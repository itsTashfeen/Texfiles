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


@dataclass
class LatexProcessResult:
    text: str
    has_documentclass: bool
    has_end_document: bool
    truncated: bool
    written_path: Path | None = None
    codeblock_count: int = 0

    @property
    def validation_label(self) -> str:
        if self.truncated or not self.has_end_document:
            return "TRUNCATED_LATEX"
        if not self.has_documentclass:
            return "MISSING_DOCUMENTCLASS"
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
    has_end_document = r"\end{document}" in text
    truncated = has_documentclass and not has_end_document
    return LatexProcessResult(
        text=text,
        has_documentclass=has_documentclass,
        has_end_document=has_end_document,
        truncated=truncated,
        codeblock_count=codeblock_count,
    )


def write_tex(target_path: Path, raw_or_processed: str | LatexProcessResult) -> LatexProcessResult:
    if isinstance(raw_or_processed, LatexProcessResult):
        result = raw_or_processed
    else:
        result = process_latex_response(raw_or_processed)

    target_path = Path(target_path)
    target_path.parent.mkdir(parents=True, exist_ok=True)
    target_path.write_text(result.text, encoding="utf-8")
    result.written_path = target_path.resolve()
    return result
