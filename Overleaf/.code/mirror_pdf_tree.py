"""
Mirror a slice_pdfs.py .tex course tree into .pdf and move each Book PDF folder.

Usage:
  python .code/mirror_pdf_tree.py
"""

from __future__ import annotations

import shutil
from pathlib import Path


BOOK_PDF = "Book PDF"


def strip_quotes(raw: str) -> str:
    return raw.strip().strip('"').strip("'")


def tex_tree_to_pdf_tree(src: Path) -> Path:
    parts = list(src.resolve().parts)
    try:
        idx = parts.index(".tex")
    except ValueError:
        raise ValueError(f"Path does not contain a .tex folder: {src}")
    parts[idx] = ".pdf"
    return Path(*parts)


def create_dir_mirror(src: Path, dest: Path) -> int:
    created = 0
    dest.mkdir(parents=True, exist_ok=True)
    for path in sorted(src.rglob("*")):
        if not path.is_dir():
            continue
        rel = path.relative_to(src)
        if BOOK_PDF in rel.parts:
            continue
        target = dest / rel
        if not target.exists():
            target.mkdir(parents=True, exist_ok=True)
            created += 1
    return created


def merge_move_dir(src: Path, dest: Path) -> tuple[int, int]:
    dest.mkdir(parents=True, exist_ok=True)
    moved = 0
    overwritten = 0
    for item in list(src.iterdir()):
        target = dest / item.name
        if item.is_dir():
            nested_moved, nested_overwritten = merge_move_dir(item, target)
            moved += nested_moved
            overwritten += nested_overwritten
            try:
                item.rmdir()
            except OSError:
                pass
            continue
        if target.exists():
            target.unlink()
            overwritten += 1
        shutil.move(str(item), str(target))
        moved += 1
    return moved, overwritten


def remove_empty_dirs(path: Path) -> None:
    if not path.is_dir():
        return
    for child in list(path.iterdir()):
        if child.is_dir():
            remove_empty_dirs(child)
    try:
        next(path.iterdir())
    except StopIteration:
        try:
            path.rmdir()
        except OSError:
            pass


def find_book_pdf_dirs(src: Path) -> list[Path]:
    found = []
    for path in src.rglob(BOOK_PDF):
        if not path.is_dir():
            continue
        rel = path.relative_to(src)
        if list(rel.parts).count(BOOK_PDF) != 1:
            continue
        found.append(path)
    return sorted(found)


def mirror_tree(src: Path, dest: Path) -> None:
    dirs_created = create_dir_mirror(src, dest)
    print(f"Created {dirs_created} missing folder(s) under:\n  {dest}\n")

    book_dirs = find_book_pdf_dirs(src)
    if not book_dirs:
        print("No Book PDF folders found under the source.")
        return

    total_moved = 0
    total_overwritten = 0
    folders_moved = 0
    for book_src in book_dirs:
        book_dest = dest / book_src.relative_to(src)
        print(f"Moving: {book_src.relative_to(src)}")
        moved, overwritten = merge_move_dir(book_src, book_dest)
        remove_empty_dirs(book_src)
        total_moved += moved
        total_overwritten += overwritten
        folders_moved += 1
        print(f"  -> {moved} file(s), {overwritten} overwritten")

    print(
        f"\nDone. Book PDF folders: {folders_moved}, "
        f"files moved: {total_moved}, overwritten: {total_overwritten}"
    )


def main() -> int:
    print("--- Mirror .tex folder tree into .pdf and move Book PDF ---")
    raw = input("Enter the FULL path to the original .tex folders: ").strip()
    src = Path(strip_quotes(raw))
    if not src.is_dir():
        print(f"\nError: Not a directory: {src}")
        return 1

    try:
        dest = tex_tree_to_pdf_tree(src)
    except ValueError as exc:
        print(f"\nError: {exc}")
        return 1

    print(f"\nSource:      {src.resolve()}")
    print(f"Destination: {dest}")
    confirm = input("Create the .pdf mirror and move Book PDF folders? (y/n): ").strip().lower()
    if confirm != "y":
        print("Cancelled.")
        return 0

    mirror_tree(src.resolve(), dest)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
