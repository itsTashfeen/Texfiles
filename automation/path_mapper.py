"""PDF <-> TeX path translation, prefix matching, and topic extraction."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from .config import BOOK_PDF_FOLDER, PDF_ROOT, TEX_ROOT, prefix_for_folder

_LEADING_SECTION_RE = re.compile(r"^(\d+(?:\.\d+)*)\s*[-–:]?\s*")
_OPTIONAL_RE = re.compile(r"\s*\(Optional\)\s*$", re.IGNORECASE)


@dataclass(frozen=True)
class MappedItem:
    pdf_path: Path
    rel_path: Path
    topic: str
    target_tex_path: Path
    target_subfolder: str
    created_new: bool
    section_number: str = ""


def extract_section_number(pdf_filename: str | Path) -> str:
    """Extract leading section number (e.g. '5.2' from '5.2 Bivariate...pdf')."""
    stem = Path(pdf_filename).stem
    match = _LEADING_SECTION_RE.match(stem)
    return match.group(1) if match else ""


def derive_topic_name(pdf_filename: str | Path) -> str:
    stem = Path(pdf_filename).stem
    topic = _LEADING_SECTION_RE.sub("", stem)
    topic = _OPTIONAL_RE.sub("", topic)
    return " ".join(topic.split()).strip() or stem


def extract_rel_path(pdf_path: Path) -> Path:
    """Return Domain/Subject/Chapter relative to PDF_ROOT (parents above Book PDF)."""
    resolved = pdf_path.resolve()
    pdf_root = PDF_ROOT.resolve()
    try:
        relative = resolved.relative_to(pdf_root)
    except ValueError as exc:
        raise ValueError(f"PDF is not under {pdf_root}: {pdf_path}") from exc

    parts = list(relative.parts)
    if BOOK_PDF_FOLDER not in parts:
        # Allow PDFs selected from any folder under the chapter; strip file name only.
        if len(parts) < 2:
            raise ValueError(f"Cannot derive RelPath from: {pdf_path}")
        return Path(*parts[:-1])

    idx = parts.index(BOOK_PDF_FOLDER)
    if idx == 0:
        raise ValueError(f"Book PDF folder has no chapter parents: {pdf_path}")
    return Path(*parts[:idx])


def resolve_target_tex(
    pdf_path: Path,
    target_subfolder: str,
    *,
    create_dir: bool = True,
) -> tuple[Path, bool]:
    """
    Resolve the destination .tex path for a source PDF.

    Step A: existing file whose name ends with '<stem>.tex'
    Step B: create '(Prefix) <stem>.tex'
    """
    rel_path = extract_rel_path(pdf_path)
    target_dir = TEX_ROOT / rel_path / target_subfolder
    if create_dir:
        target_dir.mkdir(parents=True, exist_ok=True)

    stem = pdf_path.stem
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
