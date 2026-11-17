"""Fence stripping, multi-codeblock stitching, structural validation, and safe .tex overwrite."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

_FENCE_OPEN_RE = re.compile(r"^```(?:latex|tex|LaTeX)?\s*\n?", re.IGNORECASE)
_FENCE_CLOSE_RE = re.compile(r"\n?```\s*$")
_FENCED_BLOCK_RE = re.compile(
    r"```(?:latex|tex|LaTeX)?\s*\n(.*?)(?:\n```|\Z)",
    re.IGNORECASE | re.DOTALL,
)
_STANDALONE_FENCE_LINE_RE = re.compile(r"(?m)^```(?:latex|tex|LaTeX)?\s*$")
_LEFTOVER_FENCE_RE = re.compile(r"```")


@dataclass
class LatexProcessResult:
    text: str
    has_documentclass: bool
    has_end_document: bool
    truncated: bool
    written_path: Path | None = None
    codeblock_count: int = 0
    has_begin_document: bool = True
    balanced_document_env: bool = True
    has_leftover_fences: bool = False

    @property
    def validation_label(self) -> str:
        if self.truncated or not self.has_end_document:
            return "TRUNCATED_LATEX"
        if not self.has_documentclass:
            return "MISSING_DOCUMENTCLASS"
        if not self.has_begin_document or not self.balanced_document_env:
            return "UNBALANCED_DOCUMENT"
        if self.has_leftover_fences:
            return "LEFTOVER_FENCES"
        return "OK"


def extract_latex_source(raw: str) -> tuple[str, int]:
    """
    Extract and concatenate all fenced LaTeX/TeX code blocks from a model response.

    Handles AI Studio-style multi-block outputs (typically 1–2 fences for long docs).
    Falls back to single-outer-fence strip, then prose-trimmed raw text.
    Returns (latex_text, codeblock_count).
    """
    text = (raw or "").strip()
    if not text:
        return "", 0

    blocks = [m.group(1).strip() for m in _FENCED_BLOCK_RE.finditer(text) if m.group(1).strip()]
    if blocks:
        joined = "\n\n".join(blocks)
        joined = _STANDALONE_FENCE_LINE_RE.sub("", joined).strip()
        return _trim_to_document(joined), len(blocks)

    # Single outer fence (legacy path)
    if text.startswith("```"):
        text = _FENCE_OPEN_RE.sub("", text, count=1)
        text = _FENCE_CLOSE_RE.sub("", text)
        text = _STANDALONE_FENCE_LINE_RE.sub("", text).strip()
        return _trim_to_document(text), 1

    cleaned = _STANDALONE_FENCE_LINE_RE.sub("", text).strip()
    return _trim_to_document(cleaned), 0


def _trim_to_document(text: str) -> str:
    """Drop leading prose before \\documentclass when present."""
    idx = text.find(r"\documentclass")
    if idx > 0:
        return text[idx:].strip()
    return text.strip()


def strip_markdown_fences(raw: str) -> str:
    """Backward-compatible single-string fence strip (uses multi-block extractor)."""
    text, _ = extract_latex_source(raw)
    return text


def process_latex_response(raw: str) -> LatexProcessResult:
    text, codeblock_count = extract_latex_source(raw)
    has_documentclass = r"\documentclass" in text
    begin_count = text.count(r"\begin{document}")
    end_count = text.count(r"\end{document}")
    has_begin_document = begin_count >= 1
    has_end_document = end_count >= 1
    # If multiple blocks each had document wrappers, keep balanced check truthful.
    balanced_document_env = (begin_count == 1 and end_count == 1)
    if begin_count > 1 and end_count >= 1:
        # Normalize accidental duplicate \documentclass/\begin{document} from stitched blocks.
        first_begin = text.find(r"\begin{document}")
        last_end = text.rfind(r"\end{document}")
        if 0 <= first_begin < last_end:
            preamble = text[: first_begin + len(r"\begin{document}")]
            inner = text[first_begin + len(r"\begin{document}") : last_end]
            inner = re.sub(r"\\documentclass(?:\[[^\]]*\])?\{[^}]+\}", "", inner)
            inner = inner.replace(r"\begin{document}", "").replace(r"\end{document}", "")
            # Also strip duplicate preamble commands if any slipped before second begin
            text = f"{preamble}\n{inner.strip()}\n\\end{{document}}"
            begin_count = text.count(r"\begin{document}")
            end_count = text.count(r"\end{document}")
            balanced_document_env = (begin_count == 1 and end_count == 1)

    has_leftover_fences = bool(_LEFTOVER_FENCE_RE.search(text))
    truncated = has_documentclass and not has_end_document
    return LatexProcessResult(
        text=text,
        has_documentclass=has_documentclass,
        has_end_document=has_end_document,
        truncated=truncated,
        codeblock_count=codeblock_count,
        has_begin_document=has_begin_document,
        balanced_document_env=balanced_document_env,
        has_leftover_fences=has_leftover_fences,
    )


def validate_existing_tex_and_pdf(target_tex_path: Path) -> tuple[bool, Path, str]:
    """
    Check whether target_tex_path already contains valid LaTeX AND its mirrored PDF exists.

    Returns (is_valid_complete, mirrored_pdf_path, reason_or_status).
    """
    from .path_mapper import mirrored_pdf_for_tex

    tex_path = Path(target_tex_path).resolve()
    pdf_path = mirrored_pdf_for_tex(tex_path)
    if not tex_path.is_file():
        return False, pdf_path, "missing .tex"
    try:
        raw_tex = tex_path.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        return False, pdf_path, f"unreadable .tex ({exc})"

    if len(raw_tex.strip()) < 200:
        return False, pdf_path, "placeholder/empty .tex"

    probe = process_latex_response(raw_tex)
    if probe.validation_label != "OK":
        return False, pdf_path, f"LaTeX {probe.validation_label}"

    if not pdf_path.is_file() or pdf_path.stat().st_size <= 0:
        return False, pdf_path, "missing compiled .pdf"

    return True, pdf_path, f"Compiled ({pdf_path})"


def write_tex(
    target_path: Path,
    raw_or_processed: str | LatexProcessResult,
    *,
    backup_existing: bool = True,
) -> LatexProcessResult:
    if isinstance(raw_or_processed, LatexProcessResult):
        result = raw_or_processed
    else:
        result = process_latex_response(raw_or_processed)

    target_path = Path(target_path)
    target_path.parent.mkdir(parents=True, exist_ok=True)
    if backup_existing and target_path.is_file() and target_path.stat().st_size > 0:
        bak_path = target_path.with_suffix(target_path.suffix + ".bak")
        try:
            bak_path.write_bytes(target_path.read_bytes())
        except OSError:
            pass
    target_path.write_text(result.text, encoding="utf-8")
    result.written_path = target_path.resolve()
    return result
