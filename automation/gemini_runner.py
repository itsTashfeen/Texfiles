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
    BATCH_JOBS_PATH,
    BATCH_POLL_INTERVAL_SECONDS,
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
from .latex_processor import LatexProcessResult, process_latex_response, write_tex
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


def build_generate_config(
    model: str,
    thinking_level: str,
    *,
    service_tier: str | None,
    system_instruction: str | None,
    automatic_continuation: bool = True,
):
    from google.genai import types

    kwargs: dict[str, Any] = {
        "max_output_tokens": max_output_tokens_for_model(model),
    }
    if automatic_continuation:
        kwargs["automatic_continuation"] = True
    if system_instruction:
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


def _outcome_success(latex: LatexProcessResult | None, compile_result: CompileResult | None) -> bool:
    if latex is None or latex.validation_label != "OK":
        return False
    if compile_result is None:
        return True
    return bool(compile_result.success)


def _resolve_part_media_resolution():
    from google.genai import types

    level_map = {
        "low": types.PartMediaResolutionLevel.MEDIA_RESOLUTION_LOW,
        "medium": types.PartMediaResolutionLevel.MEDIA_RESOLUTION_MEDIUM,
        "high": types.PartMediaResolutionLevel.MEDIA_RESOLUTION_HIGH,
    }
    return level_map.get(
        (PDF_MEDIA_RESOLUTION or "medium").strip().lower(),
        types.PartMediaResolutionLevel.MEDIA_RESOLUTION_MEDIUM,
    )


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


def _pdf_part(client, pdf_path: Path):
    from google.genai import types

    data = pdf_path.read_bytes()
    media_res = _resolve_part_media_resolution()
    if len(data) <= INLINE_PDF_MAX_BYTES:
        return types.Part.from_bytes(
            data=data,
            mime_type="application/pdf",
            media_resolution=media_res,
        )
    uploaded = client.files.upload(file=str(pdf_path))
    return types.Part.from_uri(
        file_uri=uploaded.uri,
        mime_type="application/pdf",
        media_resolution=media_res,
    )


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


def build_scoped_prompt(template: str, mapped: MappedItem) -> str:
    guard = build_section_scope_guard(mapped)
    body = template.replace("[TOPIC NAME]", mapped.topic)
    return f"{guard}\n\n{body}"


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

    for attempt in range(max_retries + 1):
        # Brand-new Client per request/attempt guarantees zero shared HTTP/session/continuation state.
        client = create_client(api_key)
        try:
            pdf_part = _pdf_part(client, pdf_path)
            prompt = build_scoped_prompt(item.user_prompt, item.mapped)
            contents = build_isolated_user_content(prompt, pdf_part)
            preflight_tokens = _preflight_count_tokens(
                client,
                model=model,
                prompt_text=prompt,
                system_instruction=system_instruction,
                pdf_part=pdf_part,
            )
            console.print(
                f"[cyan][{index}/{total}] Isolated chat[/cyan] → "
                f"[bold]{pdf_path.name}[/bold] "
                f"({pages_str}{size_kb:.1f} KB, sha256={sha_short}, "
                f"media={PDF_MEDIA_RESOLUTION}, preflight≈{preflight_tokens:,} tok)"
            )
            config = build_generate_config(
                model,
                thinking_level,
                service_tier=service_tier,
                system_instruction=system_instruction,
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

            console.print(
                f"[green][{index}/{total}] Completed[/green] {pdf_path.name} — "
                f"InitIn={usage.get('initial_input_tokens', 0):,}, "
                f"BilledIn={usage.get('input_tokens', 0):,}, "
                f"Think={usage.get('thinking_tokens', 0):,}, "
                f"Out={usage.get('output_tokens', 0):,}, "
                f"Finish={finish_reason or 'n/a'}"
                + (f", TailResume={continuation_turns}" if continuation_turns else "")
            )
            latex = write_tex(item.mapped.target_tex_path, latex_probe)
            compile_result = compile_tex(item.mapped.target_tex_path)
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
        pdf_part = _pdf_part(client, item.mapped.pdf_path)
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
) -> dict[str, Any]:
    inline = _build_inline_requests(
        client,
        items,
        model=model,
        thinking_level=thinking_level,
        system_instruction=system_instruction,
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
) -> list[GenerationOutcome]:
    if not items:
        return []

    if local_job_id:
        from .job_store import STATUS_RUNNING, update_job

        update_job(local_job_id, status=STATUS_RUNNING)

    if execution_tier == TIER_BATCH_ONLY:
        record = submit_batch_job(
            client,
            items,
            model=model,
            thinking_level=thinking_level,
            system_instruction=system_instruction,
            local_job_id=local_job_id,
        )
        action = prompt_batch_action(record["job_name"])
        if action == "cancel":
            cancel_batch(client, record["job_name"], local_job_id=local_job_id)
            return [
                GenerationOutcome(
                    item=item,
                    success=False,
                    tier_used="batch",
                    error="Cancelled by user",
                )
                for item in items
            ]
        if action == "wait":
            job = wait_for_batch(client, record["job_name"])
            if _batch_state(job) == "JOB_STATE_SUCCEEDED":
                return process_batch_success(
                    client,
                    record["job_name"],
                    record["items"],
                    model=model,
                )
            return [
                GenerationOutcome(
                    item=item,
                    success=False,
                    tier_used="batch",
                    error=f"Batch ended as {_batch_state(job)}",
                )
                for item in items
            ]
        console.print(
            "[yellow]Exiting; use Run Jobs.bat (or --batches) to resume.[/yellow]"
        )
        return [
            GenerationOutcome(
                item=item,
                success=False,
                tier_used="batch",
                error="Pending batch (check later with Run Jobs.bat)",
            )
            for item in items
        ]

    if execution_tier == TIER_STANDARD:
        service_tier = None
        tier_label = "standard"
    else:
        service_tier = "flex"
        tier_label = "flex"

    total = len(items)
    ordered: list[GenerationOutcome] = []

    if MAX_WORKERS <= 1:
        # Strict sequential mode: one isolated client and single-PDF call at a time.
        for idx, item in enumerate(items, start=1):
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
            )
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
                ): item
                for idx, item in enumerate(items, start=1)
            }
            for fut in as_completed(futures):
                outcomes.append(fut.result())
        by_pdf = {o.item.mapped.pdf_path: o for o in outcomes}
        ordered = [by_pdf[i.mapped.pdf_path] for i in items if i.mapped.pdf_path in by_pdf]

    if execution_tier != TIER_FLEX_BATCH_FALLBACK:
        return ordered

    fallback_items = [
        o.item
        for o in ordered
        if (not o.success) and o.needs_batch_fallback
    ]
    if not fallback_items:
        return ordered

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
    )
    action = prompt_batch_action(record["job_name"])
    if action == "cancel":
        cancel_batch(client, record["job_name"], local_job_id=local_job_id)
        return ordered
    if action == "wait":
        job = wait_for_batch(client, record["job_name"])
        if _batch_state(job) == "JOB_STATE_SUCCEEDED":
            batch_outcomes = process_batch_success(
                client,
                record["job_name"],
                record["items"],
                model=model,
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
            return merged
    else:
        console.print(
            "[yellow]Exiting; use Run Jobs.bat (or --batches) to resume.[/yellow]"
        )
    return ordered


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
