"""
Watch Overleaf .tex tree and compile changed/new files into a mirrored .pdf tree.

Usage:
  python watch_tex_to_pdf.py
  python watch_tex_to_pdf.py --once
  python watch_tex_to_pdf.py --prune
  python watch_tex_to_pdf.py --file path/to/file.tex
  python watch_tex_to_pdf.py --file path/to/file.tex --from-outdir <workshop-outDir>
"""

from __future__ import annotations

import argparse
import shutil
import string
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
TEX_ROOT = ROOT / ".tex"
PDF_ROOT = ROOT / ".pdf"

# Cached SUBST drive that maps onto Overleaf (e.g. M:\), if any.
_SHORT_ROOT: Path | None | bool = False


def overleaf_short_root() -> Path | None:
    """Return a SUBST/mapped drive root equal to Overleaf, preferring shorter paths for pdflatex."""
    global _SHORT_ROOT
    if _SHORT_ROOT is not False:
        return _SHORT_ROOT  # type: ignore[return-value]

    root = ROOT.resolve()
    best: Path | None = None
    for letter in string.ascii_uppercase:
        drive = Path(f"{letter}:/")
        try:
            if not drive.exists():
                continue
            if drive.resolve() == root:
                # Trailing slash matters: Path("M:") / ".tex" becomes "M:.tex" (invalid).
                candidate = Path(f"{letter}:/")
                if best is None or len(str(candidate)) < len(str(best)):
                    best = candidate
        except OSError:
            continue
    _SHORT_ROOT = best
    return best


def path_for_pdflatex(path: Path) -> str:
    """
    Prefer a short SUBST path under Overleaf when available.

    pdflatex still fails on long Windows paths even when Python/Explorer can open them.
    resolve() expands M:\\ back to D:\\...\\Overleaf\\..., so we rewrite under the short root.
    """
    resolved = path.resolve()
    root = ROOT.resolve()
    short_root = overleaf_short_root()
    if short_root is None:
        return str(resolved)
    try:
        rel = resolved.relative_to(root)
    except ValueError:
        return str(resolved)
    short = (short_root / rel).resolve(strict=False)
    # Keep the SUBST drive letter form (do not expand back to D:\...).
    short_display = str(short_root / rel)
    if len(short_display) < len(str(resolved)):
        return short_display
    return str(resolved)

AUX_EXTENSIONS = [
    ".aux",
    ".log",
    ".out",
    ".toc",
    ".synctex.gz",
    ".fls",
    ".fdb_latexmk",
    ".bbl",
    ".blg",
]


def pdf_path_for(tex_path: Path) -> Path:
    relative = tex_path.resolve().relative_to(TEX_ROOT.resolve())
    return PDF_ROOT / relative.with_suffix(".pdf")


def tex_path_from_arg(raw: Path) -> Path | None:
    path = Path(raw).expanduser()
    if path.suffix.lower() != ".tex":
        path = path.with_suffix(".tex")
    path = path.resolve()
    tex_root = TEX_ROOT.resolve()
    try:
        path.relative_to(tex_root)
    except ValueError:
        print(f"Skipping (not under {tex_root}): {path}")
        return None
    return path


def is_empty_tex(path: Path) -> bool:
    try:
        return path.read_text(encoding="utf-8", errors="replace").strip() == ""
    except OSError:
        return True


def prune_empty_pdf_dirs(start_dir: Path) -> None:
    pdf_root = PDF_ROOT.resolve()
    try:
        current = start_dir.resolve()
    except OSError:
        return
    while current != pdf_root:
        try:
            current.relative_to(pdf_root)
        except ValueError:
            break
        if not current.is_dir():
            break
        try:
            next(current.iterdir())
            break
        except StopIteration:
            try:
                current.rmdir()
            except OSError:
                break
            current = current.parent


def unlink_with_retry(path: Path, attempts: int = 3) -> None:
    last_exc: OSError | None = None
    for attempt in range(attempts):
        try:
            path.unlink()
            return
        except OSError as exc:
            last_exc = exc
            if attempt < attempts - 1:
                time.sleep(0.2)
    assert last_exc is not None
    raise last_exc


def remove_mirrored_pdf(tex_path: Path) -> None:
    pdf_path = pdf_path_for(tex_path)
    rel = pdf_path.resolve().relative_to(PDF_ROOT.resolve())
    if pdf_path.is_file():
        try:
            unlink_with_retry(pdf_path)
            print(f"  -> Removed: {rel}")
        except OSError as exc:
            print(f"  -> ERROR: Could not remove {pdf_path}: {exc}")
            return
    else:
        print(f"  -> No PDF to remove: {rel}")
    prune_empty_pdf_dirs(pdf_path.parent)


def prune_orphan_pdfs() -> int:
    if not PDF_ROOT.is_dir():
        return 0
    removed = 0
    tex_root = TEX_ROOT.resolve()
    pdf_root = PDF_ROOT.resolve()
    for pdf_path in list(pdf_root.rglob("*.pdf")):
        rel = pdf_path.relative_to(pdf_root)
        tex_path = tex_root / rel.with_suffix(".tex")
        if tex_path.is_file() and not is_empty_tex(tex_path):
            continue
        try:
            unlink_with_retry(pdf_path)
            removed += 1
            print(f"  -> Pruned: {rel}")
        except OSError:
            continue
        prune_empty_pdf_dirs(pdf_path.parent)
    return removed


def mirror_from_outdir(tex_path: Path, outdir: Path) -> bool:
    pdf_path = pdf_path_for(tex_path)
    pdf_dir = pdf_path.parent
    pdf_dir.mkdir(parents=True, exist_ok=True)
    source = Path(outdir) / f"{tex_path.stem}.pdf"
    if not source.is_file():
        print(f"  -> ERROR: No PDF at {source}")
        return False
    shutil.copy2(source, pdf_path)
    print(f"  -> Mirrored: {pdf_path.resolve().relative_to(PDF_ROOT.resolve())}")
    return True


def needs_compile(tex_path: Path, pdf_path: Path) -> bool:
    if not pdf_path.exists():
        return True
    return tex_path.stat().st_mtime > pdf_path.stat().st_mtime


def cleanup_aux(pdf_dir: Path, base_name: str) -> None:
    for ext in AUX_EXTENSIONS:
        aux = pdf_dir / f"{base_name}{ext}"
        if aux.exists():
            try:
                aux.unlink()
            except OSError:
                pass


def run_pdflatex(tex_path: Path, outdir: Path, capture: bool) -> tuple[int, bytes]:
    # Run from the .tex directory and pass only the basename. Full absolute paths
    # under deep chapter trees exceed pdflatex's Windows path limit even with SUBST.
    tex_path = Path(tex_path).resolve()
    outdir = Path(outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    out_arg = str(outdir)
    cmd = [
        "pdflatex",
        "-synctex=1",
        "-interaction=nonstopmode",
        "-file-line-error",
        f"-output-directory={out_arg}",
        tex_path.name,
    ]
    print(f"  -> pdflatex cwd: {tex_path.parent}", flush=True)
    print(f"  -> pdflatex file: {tex_path.name}", flush=True)
    result = subprocess.run(cmd, cwd=str(tex_path.parent), capture_output=capture)
    stdout = result.stdout or b"" if capture else b""
    return result.returncode, stdout


def compile_to_outdir(tex_path: Path, outdir: Path) -> bool:
    outdir = Path(outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    pdf_path = outdir / f"{tex_path.stem}.pdf"
    print(f"Processing: {tex_path.resolve().relative_to(TEX_ROOT.resolve())}", flush=True)
    try:
        for pass_num in range(1, 3):
            print(f"  -> Pass {pass_num}/2...", flush=True)
            code, _ = run_pdflatex(tex_path, outdir, capture=False)
            if code != 0 and not pdf_path.exists():
                print(f"  -> ERROR: Failed to compile {tex_path.name}", flush=True)
                return False
        if pdf_path.exists():
            return True
        print(f"  -> ERROR: No PDF produced for {tex_path.name}", flush=True)
        return False
    except FileNotFoundError:
        print("CRITICAL ERROR: 'pdflatex' command not found. Install a LaTeX distribution.")
        return False


def compile_tex(tex_path: Path) -> bool:
    pdf_path = pdf_path_for(tex_path)
    pdf_dir = pdf_path.parent
    pdf_dir.mkdir(parents=True, exist_ok=True)
    base_name = tex_path.stem

    print(f"Processing: {tex_path.resolve().relative_to(TEX_ROOT.resolve())}")
    last_stdout = b""
    try:
        for pass_num in range(1, 3):
            print(f"  -> Pass {pass_num}/2...")
            code, last_stdout = run_pdflatex(tex_path, pdf_dir, capture=True)
            # pdflatex often exits non-zero on warnings even when a PDF was written.
            if code != 0 and not pdf_path.exists():
                print(f"  -> ERROR: Failed to compile {tex_path.name}")
                print("=" * 20 + " LaTeX Error Log " + "=" * 20)
                print(last_stdout.decode(errors="ignore")[-1000:])
                print("=" * 57)
                return False

        if pdf_path.exists():
            print(f"  -> Created: {pdf_path.resolve().relative_to(PDF_ROOT.resolve())}")
            return True

        print(f"  -> ERROR: No PDF produced for {tex_path.name}")
        print("=" * 20 + " LaTeX Error Log " + "=" * 20)
        print(last_stdout.decode(errors="ignore")[-1000:])
        print("=" * 57)
        return False
    except FileNotFoundError:
        print("CRITICAL ERROR: 'pdflatex' command not found. Install a LaTeX distribution.")
        return False
    finally:
        cleanup_aux(pdf_dir, base_name)


def scan_and_compile(force: bool = False) -> tuple[int, int]:
    processed = 0
    skipped = 0
    if not TEX_ROOT.is_dir():
        print(f"Error: tex root not found: {TEX_ROOT}")
        return 0, 0

    for tex_path in TEX_ROOT.rglob("*.tex"):
        if is_empty_tex(tex_path):
            skipped += 1
            continue
        pdf_path = pdf_path_for(tex_path)
        if not force and not needs_compile(tex_path, pdf_path):
            skipped += 1
            continue
        if compile_tex(tex_path):
            processed += 1
        else:
            # Still count as processed attempt; leave for retry later.
            processed += 1
    return processed, skipped


def snapshot_mtimes() -> dict[str, float]:
    state: dict[str, float] = {}
    if not TEX_ROOT.is_dir():
        return state
    for tex_path in TEX_ROOT.rglob("*.tex"):
        try:
            state[str(tex_path)] = tex_path.stat().st_mtime
        except OSError:
            continue
    return state


def watch(poll_seconds: float = 2.0) -> None:
    print(f"Watching: {TEX_ROOT}")
    print(f"PDF out:  {PDF_ROOT}")
    print("Press Ctrl+C to stop.\n")

    PDF_ROOT.mkdir(parents=True, exist_ok=True)
    known = snapshot_mtimes()

    # Compile anything missing/outdated once at startup.
    processed, skipped = scan_and_compile()
    pruned = prune_orphan_pdfs()
    print(
        f"Startup compile: {processed} compiled/attempted, {skipped} up-to-date, "
        f"{pruned} pruned.\n"
    )
    known = snapshot_mtimes()

    try:
        while True:
            time.sleep(poll_seconds)
            current = snapshot_mtimes()
            for path in known:
                if path not in current:
                    remove_mirrored_pdf(Path(path))
            for path, mtime in current.items():
                if path not in known or mtime > known[path]:
                    tex_path = Path(path)
                    if is_empty_tex(tex_path):
                        remove_mirrored_pdf(tex_path)
                    else:
                        compile_tex(tex_path)
            known = current
    except KeyboardInterrupt:
        print("\nStopped watching.")


def handle_single_file(tex_arg: Path, from_outdir: Path | None) -> int:
    tex_path = tex_path_from_arg(tex_arg)
    if tex_path is None:
        # Outside Overleaf/.tex: still compile into OUTDIR for the PDF viewer.
        if from_outdir is None:
            return 0
        path = Path(tex_arg).expanduser()
        if path.suffix.lower() != ".tex":
            path = path.with_suffix(".tex")
        path = path.resolve()
        if not path.is_file() or is_empty_tex(path):
            return 0
        return 0 if compile_to_outdir(path, from_outdir) else 1
    if not tex_path.is_file() or is_empty_tex(tex_path):
        remove_mirrored_pdf(tex_path)
        return 0
    if from_outdir is not None:
        if not compile_to_outdir(tex_path, from_outdir):
            return 1
        return 0 if mirror_from_outdir(tex_path, from_outdir) else 1
    return 0 if compile_tex(tex_path) else 1


def main() -> int:
    parser = argparse.ArgumentParser(description="Watch .tex files and compile mirrored PDFs.")
    parser.add_argument(
        "--once",
        action="store_true",
        help="Compile outdated/missing PDFs once, prune orphans, then exit.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="With --once, recompile all .tex files even if PDFs look up-to-date.",
    )
    parser.add_argument(
        "--poll",
        type=float,
        default=2.0,
        help="Polling interval in seconds (default: 2).",
    )
    parser.add_argument(
        "--file",
        type=Path,
        metavar="TEX",
        help="Compile or mirror a single .tex file, then exit.",
    )
    parser.add_argument(
        "--from-outdir",
        type=Path,
        metavar="DIR",
        help="With --file, compile into DIR then copy DIR/<stem>.pdf into the mirrored .pdf tree.",
    )
    parser.add_argument(
        "--prune",
        action="store_true",
        help="Delete mirrored PDFs whose .tex is missing or empty, then exit.",
    )
    args = parser.parse_args()

    if args.from_outdir is not None and args.file is None:
        parser.error("--from-outdir requires --file")

    if args.file is not None:
        return handle_single_file(args.file, args.from_outdir)

    if args.prune:
        pruned = prune_orphan_pdfs()
        print(f"\nDone. Pruned: {pruned}")
        return 0

    if args.once:
        processed, skipped = scan_and_compile(force=args.force)
        pruned = prune_orphan_pdfs()
        print(f"\nDone. Compiled/attempted: {processed}, skipped: {skipped}, pruned: {pruned}")
        return 0

    watch(poll_seconds=args.poll)
    return 0


if __name__ == "__main__":
    sys.exit(main())
