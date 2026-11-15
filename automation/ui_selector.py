"""Hybrid mouse (Tkinter) and keyboard (Questionary) selection UI."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import questionary
from questionary import Choice
from rich.console import Console
from rich.table import Table

from .config import (
    AVAILABLE_MODELS,
    DEFAULT_MODEL,
    DEFAULT_THINKING_LEVEL,
    EXECUTION_TIERS,
    PDF_ROOT,
    PROMPTS_DIR,
    SYSTEM_INSTRUCTIONS_DIR,
    TEX_ROOT,
    THINKING_LEVELS,
    TIER_FLEX_BATCH_FALLBACK,
)
from .path_mapper import extract_rel_path, list_existing_tex_subfolders


@dataclass
class RunSelection:
    pdf_paths: list[Path]
    prompt_paths: list[Path]
    prompt_text: str
    system_instruction_path: Path | None
    system_instruction_text: str | None
    target_subfolder: str
    model: str
    thinking_level: str
    execution_tier: str


def _tk_root():
    import tkinter as tk

    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)
    return root


def pick_pdfs_via_file_dialog() -> list[Path]:
    from tkinter import filedialog

    root = _tk_root()
    try:
        paths = filedialog.askopenfilenames(
            parent=root,
            title="Select section PDF file(s)",
            initialdir=str(PDF_ROOT),
            filetypes=[("PDF files", "*.pdf"), ("All files", "*.*")],
        )
    finally:
        root.destroy()
    return [Path(p) for p in paths]


def pick_pdfs_via_folder_dialog() -> list[Path]:
    from tkinter import filedialog

    root = _tk_root()
    try:
        folder = filedialog.askdirectory(
            parent=root,
            title="Select Book PDF (or chapter) folder",
            initialdir=str(PDF_ROOT),
        )
    finally:
        root.destroy()
    if not folder:
        return []
    directory = Path(folder)
    return sorted(p for p in directory.rglob("*.pdf") if p.is_file())


def _browse_directory_tree(start: Path, title: str) -> Path | None:
    current = start.resolve()
    while True:
        subdirs = sorted([p for p in current.iterdir() if p.is_dir()], key=lambda p: p.name.lower())
        choices: list[Choice] = []
        if current != start.resolve() and current.parent:
            choices.append(Choice(title=".. (up)", value="__up__"))
        for d in subdirs:
            choices.append(Choice(title=d.name + "/", value=str(d)))
        choices.append(Choice(title="[Select this folder]", value="__select__"))
        choices.append(Choice(title="[Cancel]", value="__cancel__"))

        answer = questionary.select(
            f"{title}\nCurrent: {current}",
            choices=choices,
        ).ask()
        if answer is None or answer == "__cancel__":
            return None
        if answer == "__up__":
            if current.parent != current:
                current = current.parent
            continue
        if answer == "__select__":
            return current
        current = Path(answer)


def pick_pdfs_via_keyboard() -> list[Path]:
    chapter_dir = _browse_directory_tree(PDF_ROOT, "Browse to a chapter under .pdf")
    if chapter_dir is None:
        return []

    book_pdf = chapter_dir / "Book PDF"
    search_root = book_pdf if book_pdf.is_dir() else chapter_dir
    pdfs = sorted(p for p in search_root.glob("*.pdf") if p.is_file())
    if not pdfs:
        pdfs = sorted(p for p in search_root.rglob("*.pdf") if p.is_file())
    if not pdfs:
        print(f"No PDFs found under {search_root}")
        return []

    choices = [Choice(title="[Select All PDFs in Chapter]", value="__all__")]
    choices.extend(Choice(title=p.name, value=str(p)) for p in pdfs)
    selected = questionary.checkbox(
        "Select PDF sections (Space to toggle, Enter to confirm)",
        choices=choices,
    ).ask()
    if not selected:
        return []
    if "__all__" in selected:
        return pdfs
    return [Path(p) for p in selected]


def showcase_selected_pdfs(pdf_paths: list[Path]) -> None:
    """Print a clear table of the PDFs chosen as sources."""
    console = Console()
    if not pdf_paths:
        console.print("[yellow]No source PDFs selected.[/yellow]")
        return

    table = Table(title=f"Selected source PDFs ({len(pdf_paths)})", show_lines=True)
    table.add_column("#", justify="right", style="cyan")
    table.add_column("File name", overflow="fold")
    table.add_column("Relative path", overflow="fold")
    table.add_column("Size", justify="right")

    pdf_root = PDF_ROOT.resolve()
    for i, path in enumerate(pdf_paths, start=1):
        resolved = path.resolve()
        try:
            rel = str(resolved.relative_to(pdf_root))
        except ValueError:
            rel = str(resolved)
        try:
            size_bytes = resolved.stat().st_size
            if size_bytes >= 1024 * 1024:
                size = f"{size_bytes / (1024 * 1024):.2f} MB"
            else:
                size = f"{size_bytes / 1024:.1f} KB"
        except OSError:
            size = "?"
        table.add_row(str(i), path.name, rel, size)

    console.print(table)
    console.print()


def pick_input_mode_and_pdfs() -> list[Path]:
    mode = questionary.select(
        "How do you want to select source PDFs?",
        choices=[
            Choice("[Mouse Dialog] Pick specific PDF file(s)", "files"),
            Choice("[Mouse Dialog] Pick entire Book PDF folder", "folder"),
            Choice("[Keyboard TUI] Browse Chapters & Checkboxes", "keyboard"),
        ],
    ).ask()
    if mode == "files":
        paths = pick_pdfs_via_file_dialog()
    elif mode == "folder":
        paths = pick_pdfs_via_folder_dialog()
    elif mode == "keyboard":
        paths = pick_pdfs_via_keyboard()
    else:
        paths = []
    showcase_selected_pdfs(paths)
    return paths


def list_prompt_files() -> list[Path]:
    if not PROMPTS_DIR.is_dir():
        return []
    return sorted(PROMPTS_DIR.glob("*.txt"))


def list_system_instruction_files() -> list[Path]:
    if not SYSTEM_INSTRUCTIONS_DIR.is_dir():
        return []
    files: list[Path] = []
    for pattern in ("*.txt", "*.md"):
        files.extend(SYSTEM_INSTRUCTIONS_DIR.glob(pattern))
    return sorted(p for p in files if p.name != ".gitkeep")


def assemble_prompt_text(prompt_paths: list[Path]) -> str:
    chunks: list[str] = []
    for i, path in enumerate(prompt_paths):
        header = "--- PRIMARY INSTRUCTIONS ---" if i == 0 else "--- ADDITIONAL INSTRUCTIONS ---"
        body = path.read_text(encoding="utf-8")
        chunks.append(f"{header}\n# Source: {path.name}\n\n{body.strip()}")
    return "\n\n".join(chunks)


def pick_prompts() -> tuple[list[Path], str]:
    prompts = list_prompt_files()
    if not prompts:
        raise FileNotFoundError(f"No prompt .txt files in {PROMPTS_DIR}")
    selected = questionary.checkbox(
        "Select prompt file(s) (order = join order)",
        choices=[Choice(title=p.name, value=str(p)) for p in prompts],
        validate=lambda x: True if x else "Select at least one prompt",
    ).ask()
    if not selected:
        raise SystemExit("No prompts selected.")
    # Preserve selection order from checkbox; questionary returns in display order of checked items.
    paths = [Path(p) for p in selected]
    return paths, assemble_prompt_text(paths)


def pick_system_instruction() -> tuple[Path | None, str | None]:
    files = list_system_instruction_files()
    choices = [Choice(title="(None)", value="__none__")]
    choices.extend(Choice(title=p.name, value=str(p)) for p in files)
    answer = questionary.select("Select system instruction", choices=choices).ask()
    if answer is None or answer == "__none__":
        return None, None
    path = Path(answer)
    return path, path.read_text(encoding="utf-8")


def pick_target_subfolder(pdf_paths: list[Path]) -> str:
    rel_path = extract_rel_path(pdf_paths[0])
    existing = list_existing_tex_subfolders(rel_path)
    preferred = ["Homework", "Problem Sets", "Book Section", "Book Sections"]
    ordered = [n for n in preferred if n in existing]
    ordered.extend(n for n in existing if n not in ordered)

    choices = [Choice(title=n, value=n) for n in ordered]
    choices.append(Choice(title="[Create new subfolder…]", value="__new__"))
    answer = questionary.select(
        f"Target .tex subfolder under .tex/{rel_path.as_posix()}",
        choices=choices or [Choice(title="[Create new subfolder…]", value="__new__")],
    ).ask()
    if answer is None:
        raise SystemExit("Cancelled.")
    if answer == "__new__":
        name = questionary.text(
            "New subfolder name",
            validate=lambda s: True if s and s.strip() else "Name required",
        ).ask()
        if not name:
            raise SystemExit("Cancelled.")
        return name.strip()
    return answer


def pick_model() -> str:
    answer = questionary.select(
        "Model",
        choices=[
            Choice(title=f"{m}{' (default)' if m == DEFAULT_MODEL else ''}", value=m)
            for m in AVAILABLE_MODELS
        ],
        default=DEFAULT_MODEL,
    ).ask()
    return answer or DEFAULT_MODEL


def pick_thinking_level() -> str:
    answer = questionary.select(
        "Thinking level",
        choices=[
            Choice(title=f"{lvl}{' (default)' if lvl == DEFAULT_THINKING_LEVEL else ''}", value=lvl)
            for lvl in THINKING_LEVELS
        ],
        default=DEFAULT_THINKING_LEVEL,
    ).ask()
    return answer or DEFAULT_THINKING_LEVEL


def pick_execution_tier() -> str:
    answer = questionary.select(
        "Execution tier",
        choices=[Choice(title=label, value=key) for key, label in EXECUTION_TIERS],
        default=TIER_FLEX_BATCH_FALLBACK,
    ).ask()
    return answer or TIER_FLEX_BATCH_FALLBACK


def run_interactive_selection() -> RunSelection:
    if not PDF_ROOT.is_dir():
        raise FileNotFoundError(f"PDF root missing: {PDF_ROOT}")
    if not TEX_ROOT.is_dir():
        raise FileNotFoundError(f"TeX root missing: {TEX_ROOT}")

    pdf_paths = pick_input_mode_and_pdfs()
    if not pdf_paths:
        raise SystemExit("No PDFs selected.")

    prompt_paths, prompt_text = pick_prompts()
    system_path, system_text = pick_system_instruction()
    target_subfolder = pick_target_subfolder(pdf_paths)
    model = pick_model()
    thinking_level = pick_thinking_level()
    execution_tier = pick_execution_tier()

    return RunSelection(
        pdf_paths=pdf_paths,
        prompt_paths=prompt_paths,
        prompt_text=prompt_text,
        system_instruction_path=system_path,
        system_instruction_text=system_text,
        target_subfolder=target_subfolder,
        model=model,
        thinking_level=thinking_level,
        execution_tier=execution_tier,
    )
