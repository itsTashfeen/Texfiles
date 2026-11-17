"""PDF <-> TeX path translation, prefix matching, and topic extraction."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from .config import (
    BOOK_PDF_FOLDER,
    CHAPTER_LEAF_FOLDERS,
    FOLDER_PREFIX_MAP,
    PDF_ROOT,
    TEX_ROOT,
    prefix_for_folder,
)

_LEADING_SECTION_RE = re.compile(r"^(\d+(?:\.\d+)*)\s*[-–:]?\s*")
_OPTIONAL_RE = re.compile(r"\s*\(Optional\)\s*$", re.IGNORECASE)
# Matches "(Homework) ", "(Book Section) ", "(Problem Set) ", or any "(Custom Folder) ".
_STEM_FOLDER_PREFIX_RE = re.compile(r"^\([^)]+\)\s+")


@dataclass(frozen=True)
class MappedItem:
    pdf_path: Path
    rel_path: Path
    topic: str
    target_tex_path: Path
    target_subfolder: str
    created_new: bool
    section_number: str = ""


def strip_stem_folder_prefix(stem: str) -> str:
    """
    Strip a leading '(Folder) ' prefix from a PDF/TeX stem.

    Compiled Book Section PDFs are often named '(Book Section) 6.3 ….pdf'.
    When regenerating into Problem Sets / Homework we want the clean stem
    '6.3 …' so targets become '(Problem Set) 6.3 ….tex', not a double prefix.
    """
    text = (stem or "").strip()
    if not text:
        return text
    # Prefer known automation prefixes first.
    known = sorted(set(FOLDER_PREFIX_MAP.values()), key=len, reverse=True)
    for prefix in known:
        if text.startswith(prefix):
            return text[len(prefix) :].lstrip(" -–:")
    # Generic "(Anything) rest" fallback for custom folders.
    return _STEM_FOLDER_PREFIX_RE.sub("", text, count=1).strip()


def clean_section_stem(pdf_filename: str | Path) -> str:
    """Return stem with optional '(Folder) ' prefix removed."""
    return strip_stem_folder_prefix(Path(pdf_filename).stem)


def extract_section_number(pdf_filename: str | Path) -> str:
    """Extract leading section number (e.g. '5.2' from '5.2 Bivariate...pdf')."""
    stem = clean_section_stem(pdf_filename)
    match = _LEADING_SECTION_RE.match(stem)
    return match.group(1) if match else ""


def derive_topic_name(pdf_filename: str | Path) -> str:
    stem = clean_section_stem(pdf_filename)
    topic = _LEADING_SECTION_RE.sub("", stem)
    topic = _OPTIONAL_RE.sub("", topic)
    return " ".join(topic.split()).strip() or stem


def extract_rel_path(pdf_path: Path) -> Path:
    """
    Return Domain/Subject/Chapter relative to PDF_ROOT.

    Strips the filename and any chapter leaf folder (Book PDF, Homework,
    Problem Sets, Book Section, …) so a PDF picked from
    `.pdf/.../Chapter 6/.../Book Section/(Book Section) 6.3.pdf`
    still maps to `.tex/.../Chapter 6/.../` — not nested under Book Section.
    """
    resolved = pdf_path.resolve()
    pdf_root = PDF_ROOT.resolve()
    try:
        relative = resolved.relative_to(pdf_root)
    except ValueError as exc:
        raise ValueError(f"PDF is not under {pdf_root}: {pdf_path}") from exc

    parts = list(relative.parts)
    if len(parts) < 2:
        raise ValueError(f"Cannot derive RelPath from: {pdf_path}")

    # Drop the filename.
    dir_parts = parts[:-1]

    # Walk from the leaf up and drop known chapter subfolders (Book PDF / Homework / …).
    while dir_parts and dir_parts[-1] in CHAPTER_LEAF_FOLDERS:
        dir_parts = dir_parts[:-1]

    if not dir_parts:
        raise ValueError(f"Book PDF / leaf folder has no chapter parents: {pdf_path}")
    return Path(*dir_parts)


def resolve_target_tex(
    pdf_path: Path,
    target_subfolder: str,
    *,
    create_dir: bool = True,
) -> tuple[Path, bool]:
    """
    Resolve the destination .tex path for a source PDF.

    Step A: existing file whose name ends with '<clean-stem>.tex'
    Step B: create '(Prefix) <clean-stem>.tex'
    """
    rel_path = extract_rel_path(pdf_path)
    target_dir = TEX_ROOT / rel_path / target_subfolder
    if create_dir:
        target_dir.mkdir(parents=True, exist_ok=True)

    stem = clean_section_stem(pdf_path)
    suffix = f"{stem}.tex"
    if target_dir.is_dir():
        matches = sorted(
            p for p in target_dir.iterdir() if p.is_file() and p.name.endswith(suffix)
        )
        if matches:
            return matches[0], False

    prefix = prefix_for_folder(target_subfolder)
    return target_dir / f"{prefix} {stem}.tex", True


def map_pdf_to_tex(pdf_path: Path, target_subfolder: str) -> MappedItem:
    pdf_path = Path(pdf_path)
    rel_path = extract_rel_path(pdf_path)
    target_tex, created_new = resolve_target_tex(pdf_path, target_subfolder)
    return MappedItem(
        pdf_path=pdf_path.resolve(),
        rel_path=rel_path,
        topic=derive_topic_name(pdf_path),
        target_tex_path=target_tex.resolve(),
        target_subfolder=target_subfolder,
        created_new=created_new,
        section_number=extract_section_number(pdf_path),
    )


def list_existing_tex_subfolders(rel_path: Path) -> list[str]:
    chapter_dir = TEX_ROOT / rel_path
    if not chapter_dir.is_dir():
        return []
    names = sorted(
        p.name
        for p in chapter_dir.iterdir()
        if p.is_dir() and p.name != BOOK_PDF_FOLDER
    )
    return names


def mirrored_pdf_for_tex(tex_path: Path) -> Path:
    relative = tex_path.resolve().relative_to(TEX_ROOT.resolve())
    return (PDF_ROOT / relative).with_suffix(".pdf")
