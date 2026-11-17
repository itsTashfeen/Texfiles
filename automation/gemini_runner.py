"""Isolated per-PDF Gemini runner, scope guard, retry logic, and Batch lifecycle."""

from __future__ import annotations

import hashlib
import json
import random
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from rich.console import Console

from .config import (
    API_TRIM_MIN_PAGES,
    BATCH_JOBS_PATH,
    BATCH_POLL_INTERVAL_SECONDS,
    CONTEXT_CACHE_TTL_SECONDS,
    FLEX_RETRY_BACKOFF_SECONDS,
    GEMINI4_MODELS,
    HTTP_TIMEOUT_MS,
    INLINE_PDF_MAX_BYTES,
    MAX_LATEX_CONTINUATION_TURNS,
    MAX_OUTPUT_TOKENS,
    MAX_WORKERS,
    PDF_MEDIA_RESOLUTION,
    TIER_BATCH_ONLY,
    TIER_FLEX_BATCH_FALLBACK,
    TIER_STANDARD,
    ensure_runtime_dirs,
    max_output_tokens_for_model,
)
from .latex_processor import (
    LatexProcessResult,
    process_latex_response,
    validate_existing_tex_and_pdf,
    write_tex,
)
from .path_mapper import MappedItem, extract_section_number
from .pdf_compiler_hook import CompileResult, compile_tex
from .reporter import (
    SectionReport,
    estimate_cost_usd,
    pricing_tier_for_execution,
    usage_from_response,
)

console = Console()


@dataclass
class WorkItem:
    mapped: MappedItem
    user_prompt: str


@dataclass
class GenerationOutcome:
    item: WorkItem
    success: bool
    tier_used: str
    response_text: str = ""
    usage: dict[str, int] = field(default_factory=dict)
    latex: LatexProcessResult | None = None
    compile_result: CompileResult | None = None
    error: str = ""
    elapsed_seconds: float = 0.0
    needs_batch_fallback: bool = False
    finish_reason: str = ""
    text_parts_count: int = 0
    continuation_turns: int = 0


def create_client(api_key: str):
    from google import genai
    from google.genai import types

    return genai.Client(
        api_key=api_key,
        http_options=types.HttpOptions(
            timeout=HTTP_TIMEOUT_MS,
            api_version="v1beta",
        ),
    )


def _close_client_quietly(client: Any) -> None:
    try:
        api_client = getattr(client, "_api_client", None)
        httpx_client = getattr(api_client, "_httpx_client", None)
        if httpx_client is not None and hasattr(httpx_client, "close"):
            httpx_client.close()
    except Exception:  # noqa: BLE001
        pass


CONTINUATION_HYGIENE_RULE = (
    "--- CONTINUATION & OUTPUT HYGIENE ---\n"
    "Emit the ENTIRE LaTeX document inside ONE continuous ```latex code fence ending with "
    r"\end{document}. "
    "Do NOT split the document across multiple code blocks and do NOT emit mid-document prose "
    "or commentary outside the single fence."
)


@dataclass
class JobContextCache:
    name: str
    model: str
    cached_tokens: int = 0
    ttl_seconds: int = CONTEXT_CACHE_TTL_SECONDS


def build_invariant_prompt_body(template: str) -> str:
    """Build the job-invariant prompt body shared across every section in a job."""
    base = (template or "").strip()
    if not base:
        return CONTINUATION_HYGIENE_RULE
    return f"{base}\n\n{CONTINUATION_HYGIENE_RULE}"


def create_job_context_cache(
    client,
    *,
    model: str,
    system_instruction: str | None,
    prompt_template: str,
    ttl_seconds: int = CONTEXT_CACHE_TTL_SECONDS,
    display_name: str | None = None,
) -> JobContextCache | None:
    """
    Create an explicit Gemini CachedContent object for system_instruction + shared prompt.

    Gracefully returns None (with a concise status message) when the selected model does
    not yet support explicit caching (e.g. Gemini 4 preview) or when system+prompt is
    below the API minimum token threshold.
    """
    from google.genai import types

    invariant_prompt = build_invariant_prompt_body(prompt_template)
    if not invariant_prompt.strip() and not (system_instruction and system_instruction.strip()):
        return None

    cfg_kwargs: dict[str, Any] = {
        "contents": [
            types.Content(
                role="user",
                parts=[types.Part.from_text(text=invariant_prompt)],
            )
        ],
        "ttl": f"{int(max(60, ttl_seconds))}s",
    }
    if system_instruction and system_instruction.strip():
        cfg_kwargs["system_instruction"] = system_instruction
    if display_name:
        cfg_kwargs["display_name"] = display_name[:120]

    try:
        cache = client.caches.create(
            model=model,
            config=types.CreateCachedContentConfig(**cfg_kwargs),
        )
        cache_name = str(getattr(cache, "name", "") or "")
        if not cache_name:
            return None
        usage_meta = getattr(cache, "usage_metadata", None)
        tok = int(getattr(usage_meta, "total_token_count", 0) or 0) if usage_meta else 0
        console.print(
            f"[green]Context cache active:[/green] [cyan]{cache_name}[/cyan] "
            f"({tok:,} shared system+prompt tok cached @ ~75% input discount)"
        )
        return JobContextCache(
            name=cache_name,
            model=model,
            cached_tokens=tok,
            ttl_seconds=ttl_seconds,
        )
    except Exception as exc:  # noqa: BLE001
        msg = str(exc)
        if "Explicit caching is not supported" in msg:
            console.print(
                f"[dim]Context cache: explicit caching not enabled on {model}; "
                "using prefix-aligned prompt layout.[/dim]"
            )
        elif "too small" in msg.lower() or "minimum" in msg.lower():
            console.print(
                "[dim]Context cache: system+prompt below model minimum cache size; "
                "sending inline.[/dim]"
            )
        else:
            console.print(
                f"[yellow]Context cache skipped ({msg[:120]}); continuing without cache.[/yellow]"
            )
        return None


def delete_job_context_cache(client, cache: JobContextCache | None) -> None:
    if cache is None or not cache.name:
        return
    try:
        client.caches.delete(name=cache.name)
    except Exception:  # noqa: BLE001
        pass


def build_generate_config(
    model: str,
    thinking_level: str,
    *,
    service_tier: str | None,
    system_instruction: str | None,
    cached_content: str | None = None,
    automatic_continuation: bool = True,
    max_output_tokens_override: int | None = None,
):
    from google.genai import types

    kwargs: dict[str, Any] = {
        "max_output_tokens": (
            int(max_output_tokens_override)
            if max_output_tokens_override is not None
            else max_output_tokens_for_model(model)
        ),
    }
    if automatic_continuation:
        kwargs["automatic_continuation"] = True
    if cached_content:
        # Gemini API forbids specifying system_instruction again when cached_content is set.
        kwargs["cached_content"] = cached_content
    elif system_instruction:
        kwargs["system_instruction"] = system_instruction
    if service_tier:
        kwargs["service_tier"] = service_tier

    if model in GEMINI4_MODELS:
        kwargs["thinking_config"] = types.ThinkingConfig(thinking_level=thinking_level)
    elif model == "gemini-3.1-pro-preview":
        # 3.1 Pro supports ThinkingConfig on v1beta; keep top_p for tighter LaTeX style.
        kwargs["thinking_config"] = types.ThinkingConfig(thinking_level=thinking_level)
        kwargs["top_p"] = 0.35

    return types.GenerateContentConfig(**kwargs)


def extract_response_text_and_meta(response: Any) -> tuple[str, dict[str, Any]]:
    """
    Join all non-thought text parts from the first candidate and capture finish metadata.

    Prefers explicit parts iteration over response.text so multi-hop / multi-part
    Long Decode merges are never dropped.
    """
    meta: dict[str, Any] = {
        "finish_reason": "",
        "text_parts_count": 0,
        "has_continuation_token": False,
    }
    if response is None:
        return "", meta

    candidates = getattr(response, "candidates", None) or []
    if not candidates:
        text = getattr(response, "text", None) or ""
        return text, meta

    candidate = candidates[0]
    finish = getattr(candidate, "finish_reason", None)
    if finish is not None:
        meta["finish_reason"] = str(getattr(finish, "name", finish) or "")
    meta["has_continuation_token"] = bool(getattr(candidate, "continuation_token", None))

    parts = getattr(getattr(candidate, "content", None), "parts", None) or []
    chunks: list[str] = []
    for part in parts:
        if isinstance(getattr(part, "thought", None), bool) and part.thought:
            continue
        part_text = getattr(part, "text", None)
        if isinstance(part_text, str) and part_text:
            chunks.append(part_text)
    meta["text_parts_count"] = len(chunks)
    if chunks:
        return "".join(chunks), meta

    # Fallback to SDK concatenator
    text = getattr(response, "text", None) or ""
    if text:
        meta["text_parts_count"] = 1
    return text, meta


def _merge_usage(base: dict[str, int], extra: dict[str, int]) -> dict[str, int]:
    merged = dict(base)
    for key in (
        "input_tokens",
        "cached_tokens",
        "thinking_tokens",
        "output_tokens",
    ):
        merged[key] = int(merged.get(key, 0) or 0) + int(extra.get(key, 0) or 0)
    # Keep the first-hop initial / preflight values.
    if not merged.get("initial_input_tokens"):
        merged["initial_input_tokens"] = int(extra.get("initial_input_tokens", 0) or 0)
    if not merged.get("preflight_tokens"):
        merged["preflight_tokens"] = int(extra.get("preflight_tokens", 0) or 0)
    return merged


def _build_tail_resume_prompt(partial_latex: str) -> str:
    anchor = partial_latex[-2000:] if len(partial_latex) > 2000 else partial_latex
    return (
        "Your previous response was truncated before finishing the LaTeX document.\n"
        "Continue the LaTeX source EXACTLY from where it left off — do not restart, "
        "do not repeat earlier sections, and do not add prose outside a single "
        "```latex code fence.\n"
        "Resume from this exact cutoff (last ~2000 characters of the incomplete file):\n"
        "----- CUTOFF ANCHOR START -----\n"
        f"{anchor}\n"
        "----- CUTOFF ANCHOR END -----\n"
        "Continue from the next character after the anchor through a complete "
        r"\end{document}."
        "\nOutput ONLY the continuation inside one ```latex code fence."
    )


def _build_compile_fix_prompt(
    latex_text: str,
    *,
    error_lines: list[str],
    validation_label: str,
) -> str:
    tail = "\n".join(latex_text.splitlines()[-150:])
    errors = "\n".join(error_lines[:8]) if error_lines else validation_label
    return (
        "The LaTeX document below is ~95% complete but failed validation/compile.\n"
        "Return a MINIMAL patch only — prefer the corrected final ~150 lines, or a short "
        "unified diff-style replacement of the broken region. Do NOT rewrite the whole file.\n"
        "Keep packages, theorem environments, and solved exercises intact.\n"
        "Output ONLY inside one ```latex code fence.\n\n"
        f"VALIDATION/COMPILE STATUS: {validation_label}\n"
        f"COMPILER / STRUCTURAL ERRORS:\n{errors}\n\n"
        "----- LAST ~150 LINES OF CURRENT .TEX -----\n"
        f"{tail}\n"
        "----- END -----\n"
        "If the document is missing \\end{document}, finish it. If braces/environments are "
        "unbalanced near the end, repair only that region."
    )


def _apply_compile_fix_patch(original: str, patch_raw: str) -> str:
    """Merge a micro-pass patch into the original LaTeX source."""
    patch = process_latex_response(patch_raw).text.strip()
    if not patch:
        return original
    # Full document replacement (still cheaper than regenerating from PDF).
    if r"\documentclass" in patch and r"\end{document}" in patch:
        return patch
    # Tail replacement: take everything before the last 150 lines of original, append patch.
    orig_lines = original.splitlines()
    if len(orig_lines) > 150 and r"\end{document}" in patch:
        head = "\n".join(orig_lines[:-150]).rstrip()
        # If patch still has begin{document}, keep only after begin.
        body = patch
        if r"\begin{document}" in body:
            body = body[body.find(r"\begin{document}") + len(r"\begin{document}") :].lstrip()
        return f"{head}\n{body}".strip()
    # Append missing end if that's all we got.
    if r"\end{document}" in patch and r"\end{document}" not in original:
        return (original.rstrip() + "\n" + patch).strip()
    return original


def _outcome_success(latex: LatexProcessResult | None, compile_result: CompileResult | None) -> bool:
    if latex is None or latex.validation_label != "OK":
        return False
    if compile_result is None:
        return True
    return bool(compile_result.success)


def _resolve_part_media_resolution(media_resolution: str | None = None):
    from google.genai import types

    level_map = {
        "low": types.PartMediaResolutionLevel.MEDIA_RESOLUTION_LOW,
        "medium": types.PartMediaResolutionLevel.MEDIA_RESOLUTION_MEDIUM,
        "high": types.PartMediaResolutionLevel.MEDIA_RESOLUTION_HIGH,
    }
    key = (media_resolution or PDF_MEDIA_RESOLUTION or "medium").strip().lower()
    return level_map.get(key, types.PartMediaResolutionLevel.MEDIA_RESOLUTION_MEDIUM)


def _pdf_page_count(pdf_path: Path) -> int | None:
    try:
        import pymupdf

        doc = pymupdf.open(pdf_path)
        try:
            return int(doc.page_count)
        finally:
            doc.close()
    except Exception:  # noqa: BLE001
        return None


def _next_section_number(section_number: str) -> str:
    parts = (section_number or "").split(".")
    if len(parts) == 2 and parts[0].isdigit() and parts[1].isdigit():
        return f"{parts[0]}.{int(parts[1]) + 1}"
    return ""


def _heading_y_fraction(page: Any, section_number: str) -> float | None:
    """Return fractional Y (0–1) of first body occurrence of a section number heading."""
    import re

    if not section_number:
        return None
    try:
        height = float(getattr(page.rect, "height", 0) or 0) or 1.0
        # Prefer titled headings like "7.3 Constrained…" / "5.3\nMarginal…" over bare nums in exercises.
        titled = re.compile(
            rf"(?m)^\s*{re.escape(section_number)}(?:\s+[A-Za-z]|\s*$)",
        )
        bare = re.compile(rf"(?m)^\s*{re.escape(section_number)}\b")
        best: float | None = None
        for block in page.get_text("blocks") or []:
            if len(block) < 5:
                continue
            text = str(block[4] or "")
            if not (titled.search(text) or bare.search(text)):
                continue
            y_frac = float(block[1]) / height
            if y_frac <= 0.06:
                continue  # running header band
            if best is None or y_frac < best:
                best = y_frac
                if titled.search(text) and y_frac <= 0.25:
                    return y_frac
        return best
    except Exception:  # noqa: BLE001
        return None


def _page_starts_with_section(page: Any, section_number: str) -> bool:
    """True when the first meaningful lines of the page are the section heading."""
    import re

    if not section_number:
        return False
    try:
        lines = [ln.strip() for ln in page.get_text("text").splitlines() if ln.strip()]
        # Skip a short run of page-number / CHAPTER running heads.
        head = lines[:6]
        joined = "\n".join(head)
        return bool(
            re.search(
                rf"(?m)^\s*{re.escape(section_number)}(?:\s+\S+|\s*$)",
                joined,
            )
        )
    except Exception:  # noqa: BLE001
        return False


def compute_api_page_trim(
    pdf_path: Path,
    *,
    section_number: str = "",
    enabled: bool = True,
) -> tuple[int, int, list[str]]:
    """
    Decide which pages to keep for the API upload (0-indexed inclusive).

    On-disk sliced PDFs are never modified. Only trims when page_count >= API_TRIM_MIN_PAGES:
    - Drop last page only when it *starts* with the next-section heading (pure overlap page),
      or the next-section heading sits in the top ~12% with almost no prior body.
    - Drop first page if current-section heading is absent on page 1 but present on page 2+.
    """
    notes: list[str] = []
    if not enabled:
        return 0, max(0, (_pdf_page_count(pdf_path) or 1) - 1), notes
    try:
        import pymupdf

        doc = pymupdf.open(pdf_path)
    except Exception:  # noqa: BLE001
        return 0, max(0, (_pdf_page_count(pdf_path) or 1) - 1), notes

    try:
        page_count = int(doc.page_count)
        if page_count < API_TRIM_MIN_PAGES:
            return 0, page_count - 1, notes

        from_page = 0
        to_page = page_count - 1
        sec = section_number or extract_section_number(pdf_path)
        next_sec = _next_section_number(sec)

        if next_sec:
            last_page = doc[page_count - 1]
            starts_next = _page_starts_with_section(last_page, next_sec)
            last_y = _heading_y_fraction(last_page, next_sec)
            # Conservative: only drop when the page is essentially next-section material.
            if starts_next or (last_y is not None and last_y <= 0.12):
                to_page = page_count - 2
                why = "starts with next heading" if starts_next else f"next {next_sec} at y={last_y:.0%}"
                notes.append(f"drop last page ({why})")

        if sec and to_page - from_page + 1 >= API_TRIM_MIN_PAGES:
            first_y = _heading_y_fraction(doc[0], sec)
            second_y = _heading_y_fraction(doc[1], sec) if page_count > 1 else None
            if first_y is None and second_y is not None and not _page_starts_with_section(doc[0], sec):
                from_page = 1
                notes.append(f"drop first page (section {sec} starts on page 2)")

        if to_page < from_page:
            from_page, to_page = 0, page_count - 1
            notes = []
        return from_page, to_page, notes
    finally:
        doc.close()


def _pdf_bytes_for_api(
    pdf_path: Path,
    *,
    section_number: str = "",
    trim_overlap_pages: bool = True,
) -> tuple[bytes, int, int, list[str]]:
    """Return (pdf_bytes, kept_pages, original_pages, trim_notes)."""
    original_pages = _pdf_page_count(pdf_path) or 0
    from_page, to_page, notes = compute_api_page_trim(
        pdf_path,
        section_number=section_number,
        enabled=trim_overlap_pages,
    )
    kept = max(0, to_page - from_page + 1)
    if not notes or kept >= original_pages:
        return pdf_path.read_bytes(), original_pages or kept, original_pages, []

    try:
        import pymupdf

        src = pymupdf.open(pdf_path)
        try:
            dst = pymupdf.open()
            try:
                dst.insert_pdf(src, from_page=from_page, to_page=to_page)
                return dst.tobytes(deflate=True), kept, original_pages, notes
            finally:
                dst.close()
        finally:
            src.close()
    except Exception:  # noqa: BLE001
        return pdf_path.read_bytes(), original_pages, original_pages, []


def _pdf_part(
    client,
    pdf_path: Path,
    *,
    media_resolution: str | None = None,
    section_number: str = "",
    trim_overlap_pages: bool = True,
):
    from google.genai import types

    data, kept_pages, original_pages, notes = _pdf_bytes_for_api(
        pdf_path,
        section_number=section_number,
        trim_overlap_pages=trim_overlap_pages,
    )
    media_res = _resolve_part_media_resolution(media_resolution)
    if notes:
        console.print(
            f"[dim]API-only PDF trim for {pdf_path.name}: "
            f"{original_pages}→{kept_pages} pages ({'; '.join(notes)})[/dim]"
        )
    if len(data) <= INLINE_PDF_MAX_BYTES:
        return types.Part.from_bytes(
            data=data,
            mime_type="application/pdf",
            media_resolution=media_res,
        )
    # Large trimmed PDFs: write a temp upload then delete local temp.
    import tempfile

    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        tmp.write(data)
        tmp_path = Path(tmp.name)
    try:
        uploaded = client.files.upload(file=str(tmp_path))
        return types.Part.from_uri(
            file_uri=uploaded.uri,
            mime_type="application/pdf",
            media_resolution=media_res,
        )
    finally:
        try:
            tmp_path.unlink(missing_ok=True)
        except OSError:
            pass


def build_section_scope_guard(mapped: MappedItem) -> str:
    """
    Build a strict section boundary header so 1-page overlap slicing never triggers
    adjacent-section solving or textbook memory extrapolation.
    """
    sec_num = mapped.section_number or extract_section_number(mapped.pdf_path)
    target_label = (
        f"Section {sec_num} ({mapped.topic})"
        if sec_num
        else f"Topic '{mapped.topic}' ({mapped.pdf_path.stem})"
    )
    return (
        "--- STRICT SECTION SCOPE BOUNDARY ---\n"
        f"TARGET SECTION FOR THIS ISOLATED SESSION: {target_label}\n"
        f"SOURCE FILE: {mapped.pdf_path.name}\n"
        f'PROMPT PLACEHOLDER BINDING: Wherever the instructions reference [TOPIC NAME], substitute "{mapped.topic}".\n'
        "CRITICAL BOUNDARY RULES:\n"
        "1. This is a completely standalone, single-PDF session. Cover ONLY the theory, examples, "
        f"and exercises that belong to {target_label}.\n"
        "2. The first page and/or final page of the attached PDF intentionally includes up to 1 page "
        "of boundary overlap from the immediately preceding or following textbook section so no "
        "sentence or formula is cut off.\n"
        "3. IGNORE any exercises or text on page 1 that belong to the END of the preceding section, "
        "and STOP immediately when the next section's heading begins on the final overlap page.\n"
        "4. NEVER recall, reconstruct, or continue into exercises from earlier or later sections "
        "from your pretraining memory—solve ONLY what belongs to this target section as printed in "
        "the attached PDF.\n"
        "--- END OF SCOPE BOUNDARY ---"
    )


def build_scoped_prompt(
    template: str,
    mapped: MappedItem,
    *,
    use_cached_prompt: bool = False,
) -> str:
    guard = build_section_scope_guard(mapped)
    if use_cached_prompt:
        # System instruction + invariant prompt are already stored in CachedContent.
        return guard
    # Prefix-aligned order: invariant shared prompt first, per-section scope guard second.
    invariant = build_invariant_prompt_body(template)
    return f"{invariant}\n\n{guard}"


def build_isolated_user_content(prompt_text: str, pdf_part: Any):
    """Build a single-turn user Content object containing strictly 1 text part + 1 PDF part."""
    from google.genai import types

    user_content = types.Content(
        role="user",
        parts=[
            types.Part.from_text(text=prompt_text),
            pdf_part,
        ],
    )
    media_parts = [
        p
        for p in (user_content.parts or [])
        if getattr(p, "inline_data", None) is not None
        or getattr(p, "file_data", None) is not None
    ]
    if len(media_parts) != 1:
        raise RuntimeError(
            f"Isolation check failed: expected exactly 1 PDF part, got {len(media_parts)}"
        )
    return [user_content]


def _preflight_count_tokens(
    client,
    *,
    model: str,
    prompt_text: str,
    system_instruction: str | None,
    pdf_part: Any,
) -> int:
    """
    Compute single-turn input token count before calling generate_content.

    Note: Gemini Developer API count_tokens does not accept system_instruction in
    CountTokensConfig, so we concatenate system_instruction + prompt_text for an
    accurate single-turn token estimate matching AI Studio.
    """
    from google.genai import types

    combined_text = (
        f"{system_instruction.strip()}\n\n{prompt_text}"
        if system_instruction and system_instruction.strip()
        else prompt_text
    )
    contents = [
        types.Content(
            role="user",
            parts=[types.Part.from_text(text=combined_text), pdf_part],
        )
    ]
    try:
        res = client.models.count_tokens(model=model, contents=contents)
        return int(getattr(res, "total_tokens", 0) or 0)
    except Exception:  # noqa: BLE001
        return 0


def _is_retryable(exc: BaseException) -> bool:
    text = str(exc).lower()
    code = getattr(exc, "code", None) or getattr(exc, "status_code", None)
    if code in {429, 503}:
        return True
    # 402 prepayment / billing depletion is not transient; do not retry blindly.
    if code == 402 or "402" in text or "prepayment credits" in text:
        return False
    return any(
        token in text
        for token in (
            "429",
            "503",
            "resource exhausted",
            "unavailable",
            "timeout",
            "timed out",
            "capacity",
            "quota",
        )
    )


def _sleep_backoff(attempt: int) -> None:
    base = FLEX_RETRY_BACKOFF_SECONDS[min(attempt, len(FLEX_RETRY_BACKOFF_SECONDS) - 1)]
    jitter = random.uniform(0, base * 0.25)
    time.sleep(base + jitter)


def generate_one(
    api_key: str,
    item: WorkItem,
    *,
    index: int = 1,
    total: int = 1,
    model: str,
    thinking_level: str,
    service_tier: str | None,
    system_instruction: str | None,
    tier_label: str,
    context_cache: JobContextCache | None = None,
    media_resolution: str | None = None,
    trim_overlap_pages: bool = True,
    backup_existing_tex: bool = True,
    eta_seconds: float | None = None,
    max_retries: int = 3,
) -> GenerationOutcome:
    started = time.perf_counter()
    last_error = ""
    pdf_path = item.mapped.pdf_path
    pdf_bytes = pdf_path.read_bytes()
    sha_short = hashlib.sha256(pdf_bytes).hexdigest()[:10]
    pages = _pdf_page_count(pdf_path)
    pages_str = f"{pages} pages, " if pages is not None else ""
    size_kb = len(pdf_bytes) / 1024.0
    cached_name = context_cache.name if (context_cache and context_cache.name) else None
    media_label = (media_resolution or PDF_MEDIA_RESOLUTION or "medium").strip().lower()
    eta_tag = f", ETA≈{eta_seconds / 60:.1f}m" if eta_seconds and eta_seconds > 0 else ""

    for attempt in range(max_retries + 1):
        # Brand-new Client per request/attempt guarantees zero shared HTTP/session/continuation state.
        client = create_client(api_key)
        try:
            pdf_part = _pdf_part(
                client,
                pdf_path,
                media_resolution=media_label,
                section_number=item.mapped.section_number,
                trim_overlap_pages=trim_overlap_pages,
            )
            prompt = build_scoped_prompt(
                item.user_prompt,
                item.mapped,
                use_cached_prompt=bool(cached_name),
            )
            full_prompt_for_count = build_scoped_prompt(
                item.user_prompt,
                item.mapped,
                use_cached_prompt=False,
            )
            contents = build_isolated_user_content(prompt, pdf_part)
            preflight_tokens = _preflight_count_tokens(
                client,
                model=model,
                prompt_text=full_prompt_for_count,
                system_instruction=system_instruction,
                pdf_part=pdf_part,
            )
            cache_tag = f", cache={context_cache.cached_tokens:,} tok" if context_cache else ""
            console.print(
                f"[cyan][{index}/{total}] Isolated chat[/cyan] → "
                f"[bold]{pdf_path.name}[/bold] "
                f"({pages_str}{size_kb:.1f} KB, sha256={sha_short}, "
                f"media={media_label}, preflight≈{preflight_tokens:,} tok{cache_tag}{eta_tag})"
            )
            config = build_generate_config(
                model,
                thinking_level,
                service_tier=service_tier,
                system_instruction=system_instruction,
                cached_content=cached_name,
                automatic_continuation=True,
            )
            response = client.models.generate_content(
                model=model,
                contents=contents,
                config=config,
            )
            text, resp_meta = extract_response_text_and_meta(response)
            usage = usage_from_response(response, preflight_tokens=preflight_tokens)
            finish_reason = str(resp_meta.get("finish_reason") or "")
            text_parts_count = int(resp_meta.get("text_parts_count") or 0)
            continuation_turns = 0

            latex_probe = process_latex_response(text)
            # Tail-resume when Long Decode / 65k still left the document incomplete.
            while (
                latex_probe.has_documentclass
                and not latex_probe.has_end_document
                and continuation_turns < MAX_LATEX_CONTINUATION_TURNS
            ):
                continuation_turns += 1
                console.print(
                    f"[yellow][{index}/{total}] Truncated LaTeX "
                    f"(finish={finish_reason or '?'}); "
                    f"tail-resume turn {continuation_turns}/"
                    f"{MAX_LATEX_CONTINUATION_TURNS}…[/yellow]"
                )
                resume_prompt = _build_tail_resume_prompt(latex_probe.text)
                resume_contents = build_isolated_user_content(resume_prompt, pdf_part)
                resume_config = build_generate_config(
                    model,
                    thinking_level,
                    service_tier=service_tier,
                    system_instruction=system_instruction,
                    cached_content=cached_name,
                    automatic_continuation=True,
                )
                resume_response = client.models.generate_content(
                    model=model,
                    contents=resume_contents,
                    config=resume_config,
                )
                resume_text, resume_meta = extract_response_text_and_meta(resume_response)
                resume_usage = usage_from_response(resume_response, preflight_tokens=0)
                usage = _merge_usage(usage, resume_usage)
                finish_reason = str(resume_meta.get("finish_reason") or finish_reason)
                text_parts_count += int(resume_meta.get("text_parts_count") or 0)

                resume_latex = process_latex_response(resume_text)
                continuation_body = resume_latex.text
                if resume_latex.has_documentclass and r"\begin{document}" in continuation_body:
                    # Model restarted the full document — take only the body after begin.
                    begin_idx = continuation_body.find(r"\begin{document}")
                    continuation_body = continuation_body[begin_idx + len(r"\begin{document}") :].lstrip()
                text = (latex_probe.text.rstrip() + "\n" + continuation_body).strip()
                latex_probe = process_latex_response(text)

            from .config import TOKEN_MISMATCH_RATIO
            from .reporter import has_token_mismatch

            init_in = int(usage.get("initial_input_tokens", 0) or 0)
            billed_in = int(usage.get("input_tokens", 0) or 0)
            mismatch_tag = ""
            if has_token_mismatch(init_in, billed_in):
                mismatch_tag = (
                    f", TOKEN_MISMATCH BilledIn={billed_in:,}"
                    f">{TOKEN_MISMATCH_RATIO:g}×InitIn"
                )
            console.print(
                f"[green][{index}/{total}] Completed[/green] {pdf_path.name} — "
                f"InitIn={init_in:,}, "
                f"BilledIn={billed_in:,}, "
                f"Cache={usage.get('cached_tokens', 0):,}, "
                f"Think={usage.get('thinking_tokens', 0):,}, "
                f"Out={usage.get('output_tokens', 0):,}, "
                f"Finish={finish_reason or 'n/a'}"
                + (f", TailResume={continuation_turns}" if continuation_turns else "")
                + mismatch_tag
            )
            latex = write_tex(
                item.mapped.target_tex_path,
                latex_probe,
                backup_existing=backup_existing_tex,
            )
            compile_result = compile_tex(item.mapped.target_tex_path)

            # Cheap compile-fix / truncation micro-pass (one shot) instead of full regen.
            needs_fix = (
                latex.validation_label != "OK"
                or (compile_result is not None and not compile_result.success)
            )
            if needs_fix and latex.has_documentclass:
                console.print(
                    f"[yellow][{index}/{total}] Compile-fix micro-pass "
                    f"({latex.validation_label}; "
                    f"{(compile_result.status_label if compile_result else 'n/a')[:40]})…[/yellow]"
                )
                fix_prompt = _build_compile_fix_prompt(
                    latex.text,
                    error_lines=(compile_result.error_lines if compile_result else []),
                    validation_label=latex.validation_label,
                )
                fix_contents = build_isolated_user_content(fix_prompt, pdf_part)
                fix_config = build_generate_config(
                    model,
                    "low",
                    service_tier=service_tier,
                    system_instruction=system_instruction,
                    cached_content=cached_name,
                    automatic_continuation=False,
                    max_output_tokens_override=min(16_384, max_output_tokens_for_model(model)),
                )
                try:
                    fix_response = client.models.generate_content(
                        model=model,
                        contents=fix_contents,
                        config=fix_config,
                    )
                    fix_text, fix_meta = extract_response_text_and_meta(fix_response)
                    fix_usage = usage_from_response(fix_response, preflight_tokens=0)
                    usage = _merge_usage(usage, fix_usage)
                    text_parts_count += int(fix_meta.get("text_parts_count") or 0)
                    patched = _apply_compile_fix_patch(latex.text, fix_text)
                    latex_probe = process_latex_response(patched)
                    text = latex_probe.text
                    latex = write_tex(
                        item.mapped.target_tex_path,
                        latex_probe,
                        backup_existing=False,
                    )
                    compile_result = compile_tex(item.mapped.target_tex_path)
                    console.print(
                        f"[cyan][{index}/{total}] After fix-pass:[/cyan] "
                        f"LaTeX={latex.validation_label}, "
                        f"Compile={compile_result.status_label if compile_result else 'n/a'}"
                    )
                except Exception as fix_exc:  # noqa: BLE001
                    console.print(
                        f"[yellow][{index}/{total}] Compile-fix skipped: {fix_exc}[/yellow]"
                    )

            ok = _outcome_success(latex, compile_result)
            error = ""
            if not ok:
                if latex.validation_label != "OK":
                    error = f"LaTeX validation: {latex.validation_label}"
                elif compile_result and not compile_result.success:
                    error = compile_result.status_label
            return GenerationOutcome(
                item=item,
                success=ok,
                tier_used=tier_label,
                response_text=text,
                usage=usage,
                latex=latex,
                compile_result=compile_result,
                error=error,
                elapsed_seconds=time.perf_counter() - started,
                needs_batch_fallback=False,
                finish_reason=finish_reason,
                text_parts_count=text_parts_count,
                continuation_turns=continuation_turns,
            )
        except Exception as exc:  # noqa: BLE001 — surface API/runtime errors per item
            last_error = str(exc)
            if attempt < max_retries and _is_retryable(exc):
                console.print(
                    f"[yellow]Retry {attempt + 1}/{max_retries} for "
                    f"{pdf_path.name}: {exc}[/yellow]"
                )
                _sleep_backoff(attempt)
                continue
            return GenerationOutcome(
                item=item,
                success=False,
                tier_used=tier_label,
                error=last_error,
                elapsed_seconds=time.perf_counter() - started,
                needs_batch_fallback=_is_retryable(exc),
            )
        finally:
            _close_client_quietly(client)

    return GenerationOutcome(
        item=item,
        success=False,
        tier_used=tier_label,
        error=last_error or "Unknown failure",
        elapsed_seconds=time.perf_counter() - started,
        needs_batch_fallback=True,
    )


def outcome_to_report(outcome: GenerationOutcome, model: str) -> SectionReport:
    usage = outcome.usage
    tier = outcome.tier_used
    billed_in = usage.get("input_tokens", 0)
    init_in = usage.get("initial_input_tokens", 0) or usage.get("preflight_tokens", 0) or billed_in
    cost = estimate_cost_usd(
        model,
        pricing_tier_for_execution(tier),
        input_tokens=billed_in,
        cached_tokens=usage.get("cached_tokens", 0),
        thinking_tokens=usage.get("thinking_tokens", 0),
        output_tokens=usage.get("output_tokens", 0),
    )
    latex_label = outcome.latex.validation_label if outcome.latex else "N/A"
    if outcome.compile_result:
        compile_status = outcome.compile_result.status_label
        pdf_out = str(outcome.compile_result.pdf_path)
    else:
        compile_status = "Skipped"
        pdf_out = ""
    extras: dict[str, Any] = {}
    if outcome.text_parts_count:
        extras["text_parts_count"] = outcome.text_parts_count
    if outcome.continuation_turns:
        extras["continuation_turns"] = outcome.continuation_turns
    if outcome.latex is not None and outcome.latex.codeblock_count:
        extras["codeblock_count"] = outcome.latex.codeblock_count
    return SectionReport(
        pdf_name=outcome.item.mapped.pdf_path.name,
        topic=outcome.item.mapped.topic,
        target_tex_path=str(outcome.item.mapped.target_tex_path),
        tier_used=tier,
        initial_input_tokens=init_in,
        input_tokens=billed_in,
        cached_tokens=usage.get("cached_tokens", 0),
        thinking_tokens=usage.get("thinking_tokens", 0),
        output_tokens=usage.get("output_tokens", 0),
        preflight_tokens=usage.get("preflight_tokens", 0),
        estimated_cost_usd=cost,
        latex_validation=latex_label,
        compile_status=compile_status,
        pdf_output_path=pdf_out,
        elapsed_seconds=outcome.elapsed_seconds,
        error=outcome.error,
        finish_reason=outcome.finish_reason,
        extras=extras,
    )


def _load_batch_jobs() -> list[dict[str, Any]]:
    ensure_runtime_dirs()
    if not BATCH_JOBS_PATH.exists():
        return []
    try:
        data = json.loads(BATCH_JOBS_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []
    return data if isinstance(data, list) else []


def _save_batch_jobs(jobs: list[dict[str, Any]]) -> None:
    ensure_runtime_dirs()
    BATCH_JOBS_PATH.write_text(json.dumps(jobs, indent=2), encoding="utf-8")


def _persist_batch_job(job_record: dict[str, Any]) -> None:
    jobs = _load_batch_jobs()
    jobs = [j for j in jobs if j.get("job_name") != job_record.get("job_name")]
    jobs.append(job_record)
    _save_batch_jobs(jobs)


def _build_inline_requests(
    client,
    items: list[WorkItem],
    *,
    model: str,
    thinking_level: str,
    system_instruction: str | None,
    media_resolution: str | None = None,
    trim_overlap_pages: bool = True,
) -> list[dict[str, Any]]:
    requests: list[dict[str, Any]] = []
    # Batch inline requests: omit automatic_continuation (SDK-side only for sync).
    config = build_generate_config(
        model,
        thinking_level,
        service_tier=None,
        system_instruction=system_instruction,
        automatic_continuation=False,
    )
    config_dict: dict[str, Any]
    if hasattr(config, "model_dump"):
        config_dict = config.model_dump(exclude_none=True)
    elif hasattr(config, "to_json_dict"):
        config_dict = config.to_json_dict()
    else:
        config_dict = {"max_output_tokens": max_output_tokens_for_model(model)}
    config_dict.pop("automatic_continuation", None)

    total = len(items)
    for idx, item in enumerate(items, start=1):
        pdf_part = _pdf_part(
            client,
            item.mapped.pdf_path,
            media_resolution=media_resolution,
            section_number=item.mapped.section_number,
            trim_overlap_pages=trim_overlap_pages,
        )
        prompt = build_scoped_prompt(item.user_prompt, item.mapped)
        preflight_tokens = _preflight_count_tokens(
            client,
            model=model,
            prompt_text=prompt,
            system_instruction=system_instruction,
            pdf_part=pdf_part,
        )
        console.print(
            f"[cyan][Batch {idx}/{total}] Prepared isolated item[/cyan] → "
            f"[bold]{item.mapped.pdf_path.name}[/bold] (preflight≈{preflight_tokens:,} tok)"
        )
        part_payload: Any
        if hasattr(pdf_part, "model_dump"):
            part_payload = pdf_part.model_dump(exclude_none=True)
        else:
            part_payload = pdf_part
        requests.append(
            {
                "contents": [
                    {
                        "role": "user",
                        "parts": [
                            {"text": prompt},
                            part_payload,
                        ],
                    }
                ],
                "config": config_dict,
                "metadata": {
                    "pdf_path": str(item.mapped.pdf_path),
                    "target_tex_path": str(item.mapped.target_tex_path),
                    "topic": item.mapped.topic,
                    "section_number": item.mapped.section_number,
                    "preflight_tokens": str(preflight_tokens),
                },
            }
        )
    return requests


def submit_batch_job(
    client,
    items: list[WorkItem],
    *,
    model: str,
    thinking_level: str,
    system_instruction: str | None,
    local_job_id: str | None = None,
    media_resolution: str | None = None,
    trim_overlap_pages: bool = True,
) -> dict[str, Any]:
    inline = _build_inline_requests(
        client,
        items,
        model=model,
        thinking_level=thinking_level,
        system_instruction=system_instruction,
        media_resolution=media_resolution,
        trim_overlap_pages=trim_overlap_pages,
    )
    batch_job = client.batches.create(model=model, src=inline)
    job_name = getattr(batch_job, "name", None) or str(batch_job)
    record = {
        "job_name": job_name,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "model": model,
        "thinking_level": thinking_level,
        "local_job_id": local_job_id,
        "items": [
            {
                "pdf_path": str(i.mapped.pdf_path),
                "target_tex_path": str(i.mapped.target_tex_path),
                "topic": i.mapped.topic,
                "section_number": i.mapped.section_number,
                "preflight_tokens": int(
                    (inline[idx].get("metadata") or {}).get("preflight_tokens", 0) or 0
                ),
            }
            for idx, i in enumerate(items)
        ],
        "state": getattr(batch_job, "state", None) or "JOB_STATE_PENDING",
    }
    _persist_batch_job(record)
    if local_job_id:
        from .job_store import attach_batch_name

        attach_batch_name(local_job_id, job_name)
        console.print(
            f"[green]Gemini Batch linked to local job[/green] "
            f"({local_job_id[:8]}…): [cyan]{job_name}[/cyan]"
        )
    return record


def _batch_state(job: Any) -> str:
    state = getattr(job, "state", None)
    if state is None:
        return "UNKNOWN"
    return str(getattr(state, "name", state))


def process_batch_success(
    client,
    job_name: str,
    items_meta: list[dict[str, Any]],
    *,
    model: str,
    post_write: Callable[[GenerationOutcome], None] | None = None,
) -> list[GenerationOutcome]:
    job = client.batches.get(name=job_name)
    state = _batch_state(job)
    if state != "JOB_STATE_SUCCEEDED":
        raise RuntimeError(f"Batch {job_name} not succeeded (state={state})")

    outcomes: list[GenerationOutcome] = []
    dest = getattr(job, "dest", None)
    inlined = getattr(dest, "inlined_responses", None) if dest is not None else None
    if not inlined:
        inlined = getattr(job, "inlined_responses", None) or []

    for idx, meta in enumerate(items_meta):
        pdf_p = Path(meta["pdf_path"])
        mapped = MappedItem(
            pdf_path=pdf_p,
            rel_path=Path("."),
            topic=meta["topic"],
            target_tex_path=Path(meta["target_tex_path"]),
            target_subfolder=Path(meta["target_tex_path"]).parent.name,
            created_new=False,
            section_number=meta.get("section_number") or extract_section_number(pdf_p),
        )
        preflight_tok = int(meta.get("preflight_tokens", 0) or 0)
        item = WorkItem(mapped=mapped, user_prompt="")
        started = time.perf_counter()
        try:
            entry = inlined[idx] if idx < len(inlined) else None
            response = getattr(entry, "response", entry) if entry is not None else None
            text = ""
            usage: dict[str, int] = {}
            finish_reason = ""
            text_parts_count = 0
            if response is not None:
                text, resp_meta = extract_response_text_and_meta(response)
                if not text and hasattr(response, "candidates"):
                    text = str(response)
                usage = usage_from_response(response, preflight_tokens=preflight_tok)
                finish_reason = str(resp_meta.get("finish_reason") or "")
                text_parts_count = int(resp_meta.get("text_parts_count") or 0)
            if not text and entry is not None and hasattr(entry, "error") and entry.error:
                raise RuntimeError(str(entry.error))
            latex = write_tex(mapped.target_tex_path, text)
            compile_result = compile_tex(mapped.target_tex_path)
            ok = _outcome_success(latex, compile_result)
            error = ""
            if not ok:
                if latex.validation_label != "OK":
                    error = f"LaTeX validation: {latex.validation_label}"
                elif compile_result and not compile_result.success:
                    error = compile_result.status_label
            outcome = GenerationOutcome(
                item=item,
                success=ok,
                tier_used="batch",
                response_text=text,
                usage=usage,
                latex=latex,
                compile_result=compile_result,
                error=error,
                elapsed_seconds=time.perf_counter() - started,
                finish_reason=finish_reason,
                text_parts_count=text_parts_count,
            )
        except Exception as exc:  # noqa: BLE001
            outcome = GenerationOutcome(
                item=item,
                success=False,
                tier_used="batch",
                error=str(exc),
                elapsed_seconds=time.perf_counter() - started,
            )
        if post_write:
            post_write(outcome)
        outcomes.append(outcome)
    return outcomes


def prompt_batch_action(job_name: str) -> str:
    import questionary
    from questionary import Choice

    answer = questionary.select(
        f"Batch submitted: {job_name}",
        choices=[
            Choice("[W] Wait & poll live", "wait"),
            Choice("[C] Cancel batch now", "cancel"),
            Choice("[E] Exit & check later (--batches)", "exit"),
        ],
    ).ask()
    return answer or "exit"


def wait_for_batch(client, job_name: str) -> Any:
    while True:
        job = client.batches.get(name=job_name)
        state = _batch_state(job)
        console.print(f"[cyan]Batch {job_name}: {state}[/cyan]")
        if state in {
            "JOB_STATE_SUCCEEDED",
            "JOB_STATE_FAILED",
            "JOB_STATE_CANCELLED",
            "JOB_STATE_EXPIRED",
        }:
            return job
        time.sleep(BATCH_POLL_INTERVAL_SECONDS)


def cancel_batch(client, job_name: str, *, local_job_id: str | None = None) -> None:
    client.batches.cancel(name=job_name)
    jobs = _load_batch_jobs()
    for job in jobs:
        if job.get("job_name") == job_name:
            job["state"] = "JOB_STATE_CANCELLED"
            if local_job_id is None:
                local_job_id = job.get("local_job_id")
    _save_batch_jobs(jobs)
    if local_job_id:
        from .job_store import STATUS_CANCELLED, update_job

        update_job(local_job_id, status=STATUS_CANCELLED)
    console.print(f"[green]Cancelled {job_name}[/green]")


def estimate_job_preflight_costs(
    client,
    items: list[WorkItem],
    *,
    model: str,
    thinking_level: str,
    execution_tier: str,
    system_instruction: str | None,
    media_resolution: str | None = None,
    trim_overlap_pages: bool = True,
) -> dict[str, Any]:
    """
    Count tokens once per section and project min/likely/max USD before submit.
    """
    from rich.table import Table

    from .reporter import project_section_cost_band

    rows: list[dict[str, Any]] = []
    total_init = 0
    min_usd = likely_usd = max_usd = 0.0
    table = Table(title="Pre-submit cost estimate", show_lines=True)
    table.add_column("#", justify="right", style="cyan")
    table.add_column("Section", overflow="fold")
    table.add_column("InitIn", justify="right", no_wrap=True)
    table.add_column("Min $", justify="right", no_wrap=True)
    table.add_column("Likely $", justify="right", no_wrap=True)
    table.add_column("Max $", justify="right", no_wrap=True)

    for idx, item in enumerate(items, start=1):
        pdf_part = _pdf_part(
            client,
            item.mapped.pdf_path,
            media_resolution=media_resolution,
            section_number=item.mapped.section_number,
            trim_overlap_pages=trim_overlap_pages,
        )
        prompt = build_scoped_prompt(item.user_prompt, item.mapped, use_cached_prompt=False)
        init_in = _preflight_count_tokens(
            client,
            model=model,
            prompt_text=prompt,
            system_instruction=system_instruction,
            pdf_part=pdf_part,
        )
        band = project_section_cost_band(
            model,
            execution_tier,
            init_in_tokens=init_in,
            thinking_level=thinking_level,
        )
        total_init += init_in
        min_usd += band["min_usd"]
        likely_usd += band["likely_usd"]
        max_usd += band["max_usd"]
        rows.append(
            {
                "pdf_name": item.mapped.pdf_path.name,
                "init_in": init_in,
                **band,
            }
        )
        table.add_row(
            str(idx),
            item.mapped.pdf_path.stem,
            f"{init_in:,}",
            f"${band['min_usd']:.4f}",
            f"${band['likely_usd']:.4f}",
            f"${band['max_usd']:.4f}",
        )

    table.add_row(
        "",
        "[bold]TOTAL[/bold]",
        f"[bold]{total_init:,}[/bold]",
        f"[bold]${min_usd:.4f}[/bold]",
        f"[bold]${likely_usd:.4f}[/bold]",
        f"[bold]${max_usd:.4f}[/bold]",
    )
    console.print(table)
    console.print(
        "[dim]Bands assume Flex/Batch continuation inflation and typical Homework Out/Think "
        "multiples of InitIn. Actual $ varies with Long Decode hops.[/dim]"
    )
    return {
        "sections": rows,
        "total_init_in": total_init,
        "min_usd": round(min_usd, 4),
        "likely_usd": round(likely_usd, 4),
        "max_usd": round(max_usd, 4),
    }


def confirm_budget_or_abort(
    estimate: dict[str, Any],
    *,
    default_budget_usd: float | None = None,
) -> bool:
    """Show budget gate; return False if user aborts."""
    import questionary

    from .config import DEFAULT_BUDGET_USD

    budget_default = default_budget_usd if default_budget_usd is not None else DEFAULT_BUDGET_USD
    likely = float(estimate.get("likely_usd") or 0.0)
    max_usd = float(estimate.get("max_usd") or 0.0)
    console.print(
        f"[bold]Projected job cost:[/bold] "
        f"min ${estimate.get('min_usd', 0):.4f} · "
        f"likely ${likely:.4f} · "
        f"max ${max_usd:.4f}"
    )
    budget_raw = questionary.text(
        "Max budget USD for this job (abort if likely estimate exceeds it)",
        default=f"{budget_default:.2f}",
        validate=lambda s: True
        if s and s.strip().replace(".", "", 1).isdigit()
        else "Enter a number like 2.00",
    ).ask()
    if budget_raw is None:
        return False
    try:
        budget = float(budget_raw.strip())
    except ValueError:
        return False

    if likely > budget:
        console.print(
            f"[red]Likely estimate ${likely:.4f} exceeds budget ${budget:.2f}.[/red]"
        )
        override = questionary.confirm(
            "Submit anyway? (not recommended)",
            default=False,
        ).ask()
        return bool(override)

    if max_usd > budget:
        console.print(
            f"[yellow]Max-band ${max_usd:.4f} is above budget ${budget:.2f}, "
            f"but likely ${likely:.4f} is within budget.[/yellow]"
        )
        return bool(
            questionary.confirm("Continue with these settings?", default=True).ask()
        )

    return bool(
        questionary.confirm(
            f"Budget OK (${budget:.2f}). Proceed to name & submit this job?",
            default=True,
        ).ask()
    )


def _build_skipped_outcome(item: WorkItem, pdf_out: Path) -> GenerationOutcome:
    raw_tex = ""
    try:
        raw_tex = item.mapped.target_tex_path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        pass
    latex_res = process_latex_response(raw_tex)
    latex_res.written_path = item.mapped.target_tex_path.resolve()
    comp = CompileResult(
        tex_path=item.mapped.target_tex_path.resolve(),
        pdf_path=pdf_out.resolve(),
        success=True,
        returncode=0,
        stdout="Skipped (existing valid .tex + .pdf)",
        stderr="",
        error_lines=[],
    )
    return GenerationOutcome(
        item=item,
        success=True,
        tier_used="skipped",
        response_text=raw_tex,
        usage={
            "initial_input_tokens": 0,
            "input_tokens": 0,
            "cached_tokens": 0,
            "thinking_tokens": 0,
            "output_tokens": 0,
            "preflight_tokens": 0,
        },
        latex=latex_res,
        compile_result=comp,
        error="",
        elapsed_seconds=0.0,
        needs_batch_fallback=False,
        finish_reason="SKIPPED",
        text_parts_count=0,
        continuation_turns=0,
    )


def _persist_section_outcome(local_job_id: str | None, outcome: GenerationOutcome, model: str) -> None:
    if not local_job_id:
        return
    try:
        from .job_store import update_job_section_from_report

        row = outcome_to_report(outcome, model)
        update_job_section_from_report(
            local_job_id,
            row,
            pdf_path=str(outcome.item.mapped.pdf_path),
        )
    except Exception:  # noqa: BLE001
        pass


def run_items(
    client,
    items: list[WorkItem],
    *,
    api_key: str,
    model: str,
    thinking_level: str,
    execution_tier: str,
    system_instruction: str | None,
    local_job_id: str | None = None,
    skip_completed: bool = False,
    media_resolution: str | None = None,
    trim_overlap_pages: bool = True,
    backup_existing_tex: bool = True,
) -> list[GenerationOutcome]:
    if not items:
        return []

    if local_job_id:
        from .job_store import STATUS_RUNNING, update_job

        update_job(local_job_id, status=STATUS_RUNNING)

    skipped_by_pdf: dict[Path, GenerationOutcome] = {}
    active_items: list[WorkItem] = []
    if skip_completed:
        total_all = len(items)
        for idx, item in enumerate(items, start=1):
            ok_existing, existing_pdf, _ = validate_existing_tex_and_pdf(
                item.mapped.target_tex_path
            )
            if ok_existing:
                console.print(
                    f"[cyan][{idx}/{total_all}] Skipped (already OK + PDF exists)[/cyan] → "
                    f"[bold]{item.mapped.pdf_path.name}[/bold]"
                )
                skipped_outcome = _build_skipped_outcome(item, existing_pdf)
                skipped_by_pdf[item.mapped.pdf_path] = skipped_outcome
                _persist_section_outcome(local_job_id, skipped_outcome, model)
            else:
                active_items.append(item)
        if not active_items:
            return [skipped_by_pdf[i.mapped.pdf_path] for i in items]
    else:
        active_items = list(items)

    def _merge_with_skipped(active_outcomes: list[GenerationOutcome]) -> list[GenerationOutcome]:
        if not skipped_by_pdf:
            return active_outcomes
        by_pdf = dict(skipped_by_pdf)
        for o in active_outcomes:
            by_pdf[o.item.mapped.pdf_path] = o
        return [by_pdf[i.mapped.pdf_path] for i in items if i.mapped.pdf_path in by_pdf]

    if execution_tier == TIER_BATCH_ONLY:
        record = submit_batch_job(
            client,
            active_items,
            model=model,
            thinking_level=thinking_level,
            system_instruction=system_instruction,
            local_job_id=local_job_id,
            media_resolution=media_resolution,
            trim_overlap_pages=trim_overlap_pages,
        )
        action = prompt_batch_action(record["job_name"])
        if action == "cancel":
            cancel_batch(client, record["job_name"], local_job_id=local_job_id)
            return _merge_with_skipped(
                [
                    GenerationOutcome(
                        item=item,
                        success=False,
                        tier_used="batch",
                        error="Cancelled by user",
                    )
                    for item in active_items
                ]
            )
        if action == "wait":
            job = wait_for_batch(client, record["job_name"])
            if _batch_state(job) == "JOB_STATE_SUCCEEDED":
                batch_outcomes = process_batch_success(
                    client,
                    record["job_name"],
                    record["items"],
                    model=model,
                    post_write=lambda o: _persist_section_outcome(local_job_id, o, model),
                )
                return _merge_with_skipped(batch_outcomes)
            return _merge_with_skipped(
                [
                    GenerationOutcome(
                        item=item,
                        success=False,
                        tier_used="batch",
                        error=f"Batch ended as {_batch_state(job)}",
                    )
                    for item in active_items
                ]
            )
        console.print(
            "[yellow]Exiting; use Run Jobs.bat (or --batches) to resume.[/yellow]"
        )
        return _merge_with_skipped(
            [
                GenerationOutcome(
                    item=item,
                    success=False,
                    tier_used="batch",
                    error="Pending batch (check later with Run Jobs.bat)",
                )
                for item in active_items
            ]
        )

    if execution_tier == TIER_STANDARD:
        service_tier = None
        tier_label = "standard"
    else:
        service_tier = "flex"
        tier_label = "flex"

    total = len(active_items)
    ordered: list[GenerationOutcome] = []

    shared_prompt = active_items[0].user_prompt if active_items else ""
    can_share_cache = bool(shared_prompt) and all(
        i.user_prompt == shared_prompt for i in active_items
    )
    context_cache: JobContextCache | None = None
    if can_share_cache:
        context_cache = create_job_context_cache(
            client,
            model=model,
            system_instruction=system_instruction,
            prompt_template=shared_prompt,
            display_name=f"mathtex-{local_job_id[:8]}" if local_job_id else "mathtex-job",
        )

    elapsed_samples: list[float] = []
    try:
        if MAX_WORKERS <= 1:
            # Strict sequential mode: one isolated client and single-PDF call at a time.
            for idx, item in enumerate(active_items, start=1):
                remaining = total - idx + 1
                avg = (sum(elapsed_samples) / len(elapsed_samples)) if elapsed_samples else None
                eta = (avg * remaining) if avg else None
                if idx > 1 and avg:
                    console.print(
                        f"[dim]Progress {idx - 1}/{total} done · "
                        f"avg {avg / 60:.1f}m/section · ETA for rest ≈{(avg * (total - idx + 1)) / 60:.1f}m[/dim]"
                    )
                outcome = generate_one(
                    api_key,
                    item,
                    index=idx,
                    total=total,
                    model=model,
                    thinking_level=thinking_level,
                    service_tier=service_tier,
                    system_instruction=system_instruction,
                    tier_label=tier_label,
                    context_cache=context_cache,
                    media_resolution=media_resolution,
                    trim_overlap_pages=trim_overlap_pages,
                    backup_existing_tex=backup_existing_tex,
                    eta_seconds=eta,
                )
                if outcome.elapsed_seconds > 0:
                    elapsed_samples.append(outcome.elapsed_seconds)
                _persist_section_outcome(local_job_id, outcome, model)
                ordered.append(outcome)
        else:
            outcomes: list[GenerationOutcome] = []
            with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
                futures = {
                    pool.submit(
                        generate_one,
                        api_key,
                        item,
                        index=idx,
                        total=total,
                        model=model,
                        thinking_level=thinking_level,
                        service_tier=service_tier,
                        system_instruction=system_instruction,
                        tier_label=tier_label,
                        context_cache=context_cache,
                        media_resolution=media_resolution,
                        trim_overlap_pages=trim_overlap_pages,
                        backup_existing_tex=backup_existing_tex,
                    ): item
                    for idx, item in enumerate(active_items, start=1)
                }
                for fut in as_completed(futures):
                    out = fut.result()
                    _persist_section_outcome(local_job_id, out, model)
                    outcomes.append(out)
            by_pdf = {o.item.mapped.pdf_path: o for o in outcomes}
            ordered = [by_pdf[i.mapped.pdf_path] for i in active_items if i.mapped.pdf_path in by_pdf]
    finally:
        delete_job_context_cache(client, context_cache)

    if execution_tier != TIER_FLEX_BATCH_FALLBACK:
        return _merge_with_skipped(ordered)

    fallback_items = [
        o.item
        for o in ordered
        if (not o.success) and o.needs_batch_fallback
    ]
    if not fallback_items:
        return _merge_with_skipped(ordered)

    console.print(
        f"[yellow]Flex exhausted for {len(fallback_items)} item(s); "
        "submitting Batch fallback…[/yellow]"
    )
    record = submit_batch_job(
        client,
        fallback_items,
        model=model,
        thinking_level=thinking_level,
        system_instruction=system_instruction,
        local_job_id=local_job_id,
        media_resolution=media_resolution,
        trim_overlap_pages=trim_overlap_pages,
    )
    action = prompt_batch_action(record["job_name"])
    if action == "cancel":
        cancel_batch(client, record["job_name"], local_job_id=local_job_id)
        return _merge_with_skipped(ordered)
    if action == "wait":
        job = wait_for_batch(client, record["job_name"])
        if _batch_state(job) == "JOB_STATE_SUCCEEDED":
            batch_outcomes = process_batch_success(
                client,
                record["job_name"],
                record["items"],
                model=model,
                post_write=lambda o: _persist_section_outcome(local_job_id, o, model),
            )
            batch_by_pdf = {o.item.mapped.pdf_path: o for o in batch_outcomes}
            merged: list[GenerationOutcome] = []
            for o in ordered:
                if o.item.mapped.pdf_path in batch_by_pdf:
                    bo = batch_by_pdf[o.item.mapped.pdf_path]
                    bo.tier_used = "batch_fallback"
                    merged.append(bo)
                else:
                    merged.append(o)
            return _merge_with_skipped(merged)
    else:
        console.print(
            "[yellow]Exiting; use Run Jobs.bat (or --batches) to resume.[/yellow]"
        )
    return _merge_with_skipped(ordered)


def manage_batches_cli(client) -> None:
    import questionary
    from questionary import Choice

    jobs = _load_batch_jobs()
    if not jobs:
        console.print("No saved batch jobs in .state/batch_jobs.json")
        return

    refreshed: list[dict[str, Any]] = []
    for record in jobs:
        name = record.get("job_name")
        try:
            job = client.batches.get(name=name)
            record["state"] = _batch_state(job)
        except Exception as exc:  # noqa: BLE001
            record["state"] = f"ERROR: {exc}"
        refreshed.append(record)
    _save_batch_jobs(refreshed)

    choices = [
        Choice(
            title=f"{r.get('job_name')} [{r.get('state')}] — {len(r.get('items', []))} item(s)",
            value=r.get("job_name"),
        )
        for r in refreshed
    ]
    choices.append(Choice(title="[Done]", value="__done__"))
    selected = questionary.select("Select a batch job", choices=choices).ask()
    if not selected or selected == "__done__":
        return

    record = next(r for r in refreshed if r.get("job_name") == selected)
    action = questionary.select(
        f"Action for {selected}",
        choices=[
            Choice("Refresh status", "status"),
            Choice("Wait & download if succeeded", "wait"),
            Choice("Cancel (if pending/running)", "cancel"),
            Choice("Back", "back"),
        ],
    ).ask()
    if action == "status":
        job = client.batches.get(name=selected)
        console.print(f"State: {_batch_state(job)}")
    elif action == "cancel":
        cancel_batch(client, selected)
    elif action == "wait":
        job = wait_for_batch(client, selected)
        if _batch_state(job) == "JOB_STATE_SUCCEEDED":
            outcomes = process_batch_success(
                client,
                selected,
                record.get("items", []),
                model=record.get("model", ""),
            )
            from .job_store import get_job
            from .reporter import print_summary_table, write_reports

            local_id = record.get("local_job_id")
            local_job = get_job(local_id) if local_id else None
            jname = local_job.get("name") if local_job else None
            rows = [outcome_to_report(o, record.get("model", "")) for o in outcomes]
            print_summary_table(rows)
            md, js = write_reports(
                rows,
                model=record.get("model", ""),
                tier="batch",
                job_name=jname,
                job_id=local_id,
            )
            console.print(f"Wrote {md} and {js}")
        else:
            console.print(f"Ended as {_batch_state(job)}")
