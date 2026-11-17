"""Hybrid mouse (Tkinter) and keyboard (Questionary) selection UI."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, TypeVar

import questionary
from questionary import Choice
from rich.console import Console
from rich.table import Table

from .config import (
    AVAILABLE_MODELS,
    DEFAULT_MODEL,
    DEFAULT_THINKING_LEVEL,
    EXECUTION_TIERS,
    MEDIA_RESOLUTIONS,
    PDF_MEDIA_RESOLUTION,
    PDF_ROOT,
    PROMPTS_DIR,
    SYSTEM_INSTRUCTIONS_DIR,
    TEX_ROOT,
    THINKING_LEVELS,
    TIER_FLEX_BATCH_FALLBACK,
)
from .latex_processor import validate_existing_tex_and_pdf
from .path_mapper import extract_rel_path, list_existing_tex_subfolders, resolve_target_tex

# Sentinel returned by pickers when the user chooses to go back one wizard step.
BACK: Any = object()
T = TypeVar("T")


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
    skip_completed: bool = False
    media_resolution: str = PDF_MEDIA_RESOLUTION
    trim_overlap_pages: bool = True
    backup_existing_tex: bool = True


def _back_choice() -> Choice:
    return Choice(title="[← Back]", value="__back__")


def _resolve_select(answer: Any, *, allow_back: bool) -> Any:
    if answer is None:
        raise SystemExit("Cancelled.")
    if allow_back and answer == "__back__":
        return BACK
    return answer


def _confirm_or_back(message: str, *, allow_back: bool) -> bool | Any:
    """Return True to continue, BACK to go back, or raise on cancel."""
    choices = [Choice("Continue", "continue")]
    if allow_back:
        choices.append(_back_choice())
    answer = questionary.select(message, choices=choices, default="continue").ask()
    resolved = _resolve_select(answer, allow_back=allow_back)
    if resolved is BACK:
        return BACK
    return True


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


def _list_pdfs_here(folder: Path, *, recursive: bool = False) -> list[Path]:
    if not folder.is_dir():
        return []
    if recursive:
        return sorted(p for p in folder.rglob("*.pdf") if p.is_file())
    return sorted(p for p in folder.glob("*.pdf") if p.is_file())


def _checkbox_select_pdfs(pdfs: list[Path], *, title: str) -> list[Path]:
    """Multi-select PDFs: Space toggle, a = all, i = invert, Enter confirm."""
    if not pdfs:
        return []

    console = Console()
    console.print(
        "[dim]Keys: Space = toggle · a = select all · i = invert · Enter = confirm[/dim]"
    )

    # Prefer short labels; disambiguate duplicates with a parent folder hint.
    name_counts: dict[str, int] = {}
    for p in pdfs:
        name_counts[p.name] = name_counts.get(p.name, 0) + 1

    choices = [Choice(title="[Select All]", value="__all__")]
    for p in pdfs:
        label = p.name
        if name_counts.get(p.name, 0) > 1:
            label = f"{p.parent.name}/{p.name}"
        choices.append(Choice(title=label, value=str(p)))

    selected = questionary.checkbox(
        title,
        choices=choices,
    ).ask()
    if not selected:
        return []
    if "__all__" in selected:
        return list(pdfs)
    return [Path(p) for p in selected if p != "__all__"]


def pick_pdfs_via_keyboard() -> list[Path]:
    """
    Browse any folder under .pdf, then multi-select PDFs with checkboxes.

    Enter Book PDF / Book Section / Homework / etc. and choose
    "[Select PDFs in this folder]" to get Space / a / i / Enter selection.
    """
    start = PDF_ROOT.resolve()
    current = start
    console = Console()

    while True:
        try:
            entries = list(current.iterdir())
        except OSError as exc:
            console.print(f"[red]Cannot read {current}: {exc}[/red]")
            if current == start:
                return []
            current = current.parent
            continue

        subdirs = sorted(
            [p for p in entries if p.is_dir()],
            key=lambda p: p.name.lower(),
        )
        pdfs_here = _list_pdfs_here(current, recursive=False)
        pdfs_tree = _list_pdfs_here(current, recursive=True) if not pdfs_here else pdfs_here

        choices: list[Choice] = []
        if current != start:
            choices.append(Choice(title=".. (up)", value="__up__"))

        # Primary action: select PDFs in the folder the user actually opened.
        if pdfs_here:
            choices.append(
                Choice(
                    title=f"[Select PDFs in this folder ({len(pdfs_here)})]",
                    value="__select_here__",
                )
            )
        elif pdfs_tree and current != start:
            choices.append(
                Choice(
                    title=f"[Select PDFs recursively under here ({len(pdfs_tree)})]",
                    value="__select_recursive__",
                )
            )

        # Prefer jumping into common chapter leaf folders when present.
        preferred = ("Book PDF", "Book Section", "Book Sections", "Homework", "Problem Sets")
        preferred_dirs = [d for d in subdirs if d.name in preferred]
        other_dirs = [d for d in subdirs if d.name not in preferred]
        for d in preferred_dirs + other_dirs:
            n_here = len(_list_pdfs_here(d, recursive=False))
            n_tree = len(_list_pdfs_here(d, recursive=True)) if n_here == 0 else n_here
            suffix = f"  ({n_here} pdf)" if n_here else (f"  ({n_tree} pdf below)" if n_tree else "")
            choices.append(Choice(title=f"{d.name}/{suffix}", value=str(d)))

        choices.append(Choice(title="[Cancel]", value="__cancel__"))

        try:
            rel_display = current.relative_to(start)
            where = f".pdf/{rel_display.as_posix()}" if str(rel_display) != "." else ".pdf/"
        except ValueError:
            where = str(current)

        answer = questionary.select(
            f"Browse for source PDFs\nCurrent: {where}",
            choices=choices,
        ).ask()

        if answer is None or answer == "__cancel__":
            return []
        if answer == "__up__":
            if current != start:
                parent = current.parent
                try:
                    parent.resolve().relative_to(start)
                    current = parent
                except ValueError:
                    current = start
            continue
        if answer == "__select_here__":
            picked = _checkbox_select_pdfs(
                pdfs_here,
                title="Select PDF(s) — Space toggle · a all · i invert · Enter confirm",
            )
            if picked:
                return picked
            console.print("[yellow]No PDFs selected — still browsing.[/yellow]")
            continue
        if answer == "__select_recursive__":
            picked = _checkbox_select_pdfs(
                pdfs_tree,
                title="Select PDF(s) — Space toggle · a all · i invert · Enter confirm",
            )
            if picked:
                return picked
            console.print("[yellow]No PDFs selected — still browsing.[/yellow]")
            continue

        # Enter subdirectory
        current = Path(answer)


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


def pick_input_mode_and_pdfs(*, allow_back: bool = False) -> list[Path] | Any:
    while True:
        choices = [
            Choice("[Mouse Dialog] Pick specific PDF file(s)", "files"),
            Choice("[Mouse Dialog] Pick entire Book PDF folder", "folder"),
            Choice("[Keyboard TUI] Browse Chapters & Checkboxes", "keyboard"),
        ]
        if allow_back:
            choices.append(_back_choice())
        mode = questionary.select(
            "How do you want to select source PDFs?",
            choices=choices,
        ).ask()
        resolved = _resolve_select(mode, allow_back=allow_back)
        if resolved is BACK:
            return BACK

        if resolved == "files":
            paths = pick_pdfs_via_file_dialog()
        elif resolved == "folder":
            paths = pick_pdfs_via_folder_dialog()
        elif resolved == "keyboard":
            paths = pick_pdfs_via_keyboard()
        else:
            paths = []

        if not paths:
            retry = questionary.select(
                "No PDFs selected.",
                choices=[
                    Choice("Try again", "retry"),
                    _back_choice() if allow_back else Choice("Cancel", "cancel"),
                ],
            ).ask()
            if retry == "__back__" or (not allow_back and retry == "cancel"):
                if allow_back:
                    return BACK
                raise SystemExit("Cancelled.")
            continue

        showcase_selected_pdfs(paths)
        confirm = _confirm_or_back(
            f"Use these {len(paths)} source PDF(s)?",
            allow_back=True,
        )
        if confirm is BACK:
            continue
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


def pick_prompts(*, allow_back: bool = False) -> tuple[list[Path], str] | Any:
    prompts = list_prompt_files()
    if not prompts:
        raise FileNotFoundError(f"No prompt .txt files in {PROMPTS_DIR}")

    while True:
        # Checkbox can't carry Back cleanly — offer an explicit gate first when backing is allowed.
        if allow_back:
            gate = questionary.select(
                "Select prompt file(s)",
                choices=[
                    Choice("Choose prompt file(s)…", "choose"),
                    _back_choice(),
                ],
            ).ask()
            resolved = _resolve_select(gate, allow_back=True)
            if resolved is BACK:
                return BACK

        selected = questionary.checkbox(
            "Select prompt file(s) (order = join order)",
            choices=[Choice(title=p.name, value=str(p)) for p in prompts],
            validate=lambda x: True if x else "Select at least one prompt",
        ).ask()
        if selected is None:
            if allow_back:
                return BACK
            raise SystemExit("No prompts selected.")
        if not selected:
            if allow_back:
                return BACK
            raise SystemExit("No prompts selected.")
        paths = [Path(p) for p in selected]
        return paths, assemble_prompt_text(paths)


def pick_system_instruction(*, allow_back: bool = False) -> tuple[Path | None, str | None] | Any:
    files = list_system_instruction_files()
    choices: list[Choice] = []
    if allow_back:
        choices.append(_back_choice())
    choices.append(Choice(title="(None)", value="__none__"))
    choices.extend(Choice(title=p.name, value=str(p)) for p in files)
    answer = questionary.select("Select system instruction", choices=choices).ask()
    resolved = _resolve_select(answer, allow_back=allow_back)
    if resolved is BACK:
        return BACK
    if resolved == "__none__":
        return None, None
    path = Path(resolved)
    return path, path.read_text(encoding="utf-8")


def pick_target_subfolder_via_keyboard(rel_path: Path, *, allow_back: bool = False) -> str | Any:
    existing = list_existing_tex_subfolders(rel_path)
    preferred = ["Homework", "Problem Sets", "Book Section", "Book Sections"]
    ordered = [n for n in preferred if n in existing]
    ordered.extend(n for n in existing if n not in ordered)

    choices: list[Choice] = []
    if allow_back:
        choices.append(_back_choice())
    choices.extend(Choice(title=n, value=n) for n in ordered)
    choices.append(Choice(title="[Create new subfolder…]", value="__new__"))
    answer = questionary.select(
        f"Target .tex subfolder under .tex/{rel_path.as_posix()}",
        choices=choices or [Choice(title="[Create new subfolder…]", value="__new__")],
    ).ask()
    resolved = _resolve_select(answer, allow_back=allow_back)
    if resolved is BACK:
        return BACK
    if resolved == "__new__":
        name = questionary.text(
            "New subfolder name (Esc / empty = Back)",
            validate=lambda s: True if (s and s.strip()) or allow_back else "Name required",
        ).ask()
        if not name or not str(name).strip():
            if allow_back:
                return BACK
            raise SystemExit("Cancelled.")
        return str(name).strip()
    return resolved


def pick_target_subfolder_via_file_dialog(rel_path: Path, *, allow_back: bool = False) -> str | Any:
    """Mouse-pick a folder under the chapter's .tex tree (or create one in the dialog)."""
    from tkinter import filedialog, messagebox

    chapter_tex = (TEX_ROOT / rel_path).resolve()
    chapter_tex.mkdir(parents=True, exist_ok=True)
    root = _tk_root()
    try:
        messagebox.showinfo(
            "Choose target .tex folder",
            "Select (or create) a subfolder under this chapter:\n\n"
            f"{chapter_tex}\n\n"
            "Examples: Homework, Problem Sets, Book Section, or a custom folder.",
            parent=root,
        )
        chosen = filedialog.askdirectory(
            parent=root,
            title="Select target .tex subfolder for this chapter",
            initialdir=str(chapter_tex),
            mustexist=False,
        )
    finally:
        root.destroy()

    if not chosen:
        if allow_back:
            return BACK
        raise SystemExit("Cancelled.")

    chosen_path = Path(chosen).resolve()
    try:
        relative = chosen_path.relative_to(chapter_tex)
    except ValueError:
        # User navigated outside the chapter — if they picked TEX_ROOT/.../Chapter/X, recover.
        try:
            relative = chosen_path.relative_to(TEX_ROOT.resolve())
        except ValueError as exc:
            raise SystemExit(
                f"Target folder must be under .tex/{rel_path.as_posix()}/\n"
                f"Got: {chosen_path}"
            ) from exc
        # relative is Domain/Subject/Chapter/Subfolder… — take the leaf under this chapter.
        chapter_parts = rel_path.parts
        rel_parts = relative.parts
        if rel_parts[: len(chapter_parts)] != chapter_parts:
            raise SystemExit(
                f"Target folder must be under .tex/{rel_path.as_posix()}/\n"
                f"Got: {chosen_path}"
            )
        relative = Path(*rel_parts[len(chapter_parts) :]) if len(rel_parts) > len(chapter_parts) else Path()

    if not relative.parts:
        # Picked the chapter root itself — ask for a new subfolder name.
        name = questionary.text(
            f"You selected the chapter root. New subfolder name under .tex/{rel_path.as_posix()}",
            validate=lambda s: True if (s and s.strip()) or allow_back else "Name required",
        ).ask()
        if not name or not str(name).strip():
            if allow_back:
                return BACK
            raise SystemExit("Cancelled.")
        return str(name).strip()

    # Prefer a single leaf name (Homework / Problem Sets / …). Nested picks use the leaf.
    return relative.parts[0]


def pick_target_subfolder(pdf_paths: list[Path], *, allow_back: bool = False) -> str | Any:
    rel_path = extract_rel_path(pdf_paths[0])
    while True:
        choices = [
            Choice("[Keyboard TUI] Pick / create subfolder under chapter", "keyboard"),
            Choice("[Mouse Dialog] Browse to a folder under .tex", "mouse"),
        ]
        if allow_back:
            choices.append(_back_choice())
        mode = questionary.select(
            f"How do you want to choose the target .tex folder?\n"
            f"Chapter: .tex/{rel_path.as_posix()}",
            choices=choices,
            default="keyboard",
        ).ask()
        resolved = _resolve_select(mode, allow_back=allow_back)
        if resolved is BACK:
            return BACK
        if resolved == "mouse":
            result = pick_target_subfolder_via_file_dialog(rel_path, allow_back=True)
        else:
            result = pick_target_subfolder_via_keyboard(rel_path, allow_back=True)
        if result is BACK:
            continue
        return result


def suggested_thinking_level(target_subfolder: str) -> str:
    """Homework / Problem Sets default high; Book Section copies can use low."""
    name = (target_subfolder or "").strip().lower()
    if name in {"book section", "book sections"}:
        return "low"
    return DEFAULT_THINKING_LEVEL


def suggested_media_resolution(target_subfolder: str) -> str:
    """Text-heavy Homework drafts can use low; Book Section figures stay medium."""
    name = (target_subfolder or "").strip().lower()
    if name in {"homework", "problem sets", "problem set"}:
        return "low"
    return PDF_MEDIA_RESOLUTION or "medium"


def pick_model(*, allow_back: bool = False) -> str | Any:
    choices: list[Choice] = []
    if allow_back:
        choices.append(_back_choice())
    choices.extend(
        Choice(
            title=(
                f"{m}"
                + (" (default — quality Homework)" if m == DEFAULT_MODEL else "")
                + (" — cheapest overnight sweeps" if m == "gemini-4-hydrogen" else "")
                + (" — explicit Context Cache supported" if m == "gemini-3.1-pro-preview" else "")
            ),
            value=m,
        )
        for m in AVAILABLE_MODELS
    )
    answer = questionary.select(
        "Model",
        choices=choices,
        default=DEFAULT_MODEL,
    ).ask()
    resolved = _resolve_select(answer, allow_back=allow_back)
    if resolved is BACK:
        return BACK
    return resolved or DEFAULT_MODEL


def pick_thinking_level(target_subfolder: str = "", *, allow_back: bool = False) -> str | Any:
    suggested = suggested_thinking_level(target_subfolder)
    choices: list[Choice] = []
    if allow_back:
        choices.append(_back_choice())
    choices.extend(
        Choice(
            title=(
                f"{lvl}"
                + (" (suggested for this folder)" if lvl == suggested else "")
                + (" — lower Think $ when quality allows" if lvl == "low" else "")
            ),
            value=lvl,
        )
        for lvl in THINKING_LEVELS
    )
    answer = questionary.select(
        "Thinking level",
        choices=choices,
        default=suggested,
    ).ask()
    resolved = _resolve_select(answer, allow_back=allow_back)
    if resolved is BACK:
        return BACK
    return resolved or suggested


def pick_media_resolution(target_subfolder: str = "", *, allow_back: bool = False) -> str | Any:
    suggested = suggested_media_resolution(target_subfolder)
    labels = {
        "low": "low (~280 tok/page) — ~50% PDF tokens vs medium",
        "medium": "medium (~560 tok/page) — default math OCR",
        "high": "high (~1120 tok/page) — heavy figures only",
    }
    choices: list[Choice] = []
    if allow_back:
        choices.append(_back_choice())
    choices.extend(
        Choice(
            title=f"{labels.get(lvl, lvl)}"
            + (" (suggested)" if lvl == suggested else ""),
            value=lvl,
        )
        for lvl in MEDIA_RESOLUTIONS
    )
    answer = questionary.select(
        "PDF media_resolution (API tokenization)",
        choices=choices,
        default=suggested,
    ).ask()
    resolved = _resolve_select(answer, allow_back=allow_back)
    if resolved is BACK:
        return BACK
    return resolved or suggested


def pick_trim_overlap(*, allow_back: bool = False) -> bool | Any:
    choices: list[Choice] = []
    if allow_back:
        choices.append(_back_choice())
    choices.extend(
        [
            Choice(
                "Yes — drop pure overlap pages when safe (≥3 pages) (Recommended)",
                "yes",
            ),
            Choice("No — upload full sliced PDF bytes", "no"),
        ]
    )
    answer = questionary.select(
        "API-only overlap page trim (keeps on-disk sliced PDFs unchanged)",
        choices=choices,
        default="yes",
    ).ask()
    resolved = _resolve_select(answer, allow_back=allow_back)
    if resolved is BACK:
        return BACK
    return (resolved or "yes") == "yes"


def pick_execution_tier(*, allow_back: bool = False) -> str | Any:
    choices: list[Choice] = []
    if allow_back:
        choices.append(_back_choice())
    choices.extend(Choice(title=label, value=key) for key, label in EXECUTION_TIERS)
    answer = questionary.select(
        "Execution tier",
        choices=choices,
        default=TIER_FLEX_BATCH_FALLBACK,
    ).ask()
    resolved = _resolve_select(answer, allow_back=allow_back)
    if resolved is BACK:
        return BACK
    return resolved or TIER_FLEX_BATCH_FALLBACK


def pick_skip_completed(
    pdf_paths: list[Path],
    target_subfolder: str,
    *,
    allow_back: bool = False,
) -> bool | Any:
    """
    If any selected sections already have valid .tex + compiled PDF, offer to skip them.

    Returns False when there is nothing to skip (auto-advance). Returns BACK when backing up.
    """
    completed_names: list[str] = []
    for pdf in pdf_paths:
        try:
            target_tex, _ = resolve_target_tex(pdf, target_subfolder, create_dir=False)
            ok, _, _ = validate_existing_tex_and_pdf(target_tex)
            if ok:
                completed_names.append(pdf.name)
        except Exception:  # noqa: BLE001
            continue

    if not completed_names:
        return False

    choices: list[Choice] = []
    if allow_back:
        choices.append(_back_choice())
    choices.extend(
        [
            Choice(
                title=(
                    f"Skip {len(completed_names)} completed section(s) "
                    "(Recommended — saves 100% tokens on finished files)"
                ),
                value="skip",
            ),
            Choice(
                title=f"Regenerate & overwrite all {len(pdf_paths)} section(s)",
                value="overwrite",
            ),
        ]
    )
    answer = questionary.select(
        f"{len(completed_names)}/{len(pdf_paths)} selected section(s) already have a valid .tex + compiled PDF:",
        choices=choices,
        default="skip",
    ).ask()
    resolved = _resolve_select(answer, allow_back=allow_back)
    if resolved is BACK:
        return BACK
    return resolved == "skip"


def run_interactive_selection() -> RunSelection:
    """
    Step-by-step wizard with [← Back] on every step after source PDFs.

    Steps: source → prompts → system → target → skip? → model → thinking → media → trim → tier
    """
    if not PDF_ROOT.is_dir():
        raise FileNotFoundError(f"PDF root missing: {PDF_ROOT}")
    if not TEX_ROOT.is_dir():
        raise FileNotFoundError(f"TeX root missing: {TEX_ROOT}")

    # Wizard state
    pdf_paths: list[Path] = []
    prompt_paths: list[Path] = []
    prompt_text = ""
    system_path: Path | None = None
    system_text: str | None = None
    target_subfolder = ""
    skip_completed = False
    skip_prompt_shown = False
    model = DEFAULT_MODEL
    thinking_level = DEFAULT_THINKING_LEVEL
    media_resolution = PDF_MEDIA_RESOLUTION
    trim_overlap_pages = True
    execution_tier = TIER_FLEX_BATCH_FALLBACK

    STEP_SOURCE = 0
    STEP_PROMPTS = 1
    STEP_SYSTEM = 2
    STEP_TARGET = 3
    STEP_SKIP = 4
    STEP_MODEL = 5
    STEP_THINKING = 6
    STEP_MEDIA = 7
    STEP_TRIM = 8
    STEP_TIER = 9

    step = STEP_SOURCE
    while True:
        if step == STEP_SOURCE:
            result = pick_input_mode_and_pdfs(allow_back=False)
            if result is BACK or not result:
                raise SystemExit("Cancelled.")
            pdf_paths = result
            step = STEP_PROMPTS
            continue

        if step == STEP_PROMPTS:
            result = pick_prompts(allow_back=True)
            if result is BACK:
                step = STEP_SOURCE
                continue
            prompt_paths, prompt_text = result
            step = STEP_SYSTEM
            continue

        if step == STEP_SYSTEM:
            result = pick_system_instruction(allow_back=True)
            if result is BACK:
                step = STEP_PROMPTS
                continue
            system_path, system_text = result
            step = STEP_TARGET
            continue

        if step == STEP_TARGET:
            result = pick_target_subfolder(pdf_paths, allow_back=True)
            if result is BACK:
                step = STEP_SYSTEM
                continue
            target_subfolder = result
            step = STEP_SKIP
            continue

        if step == STEP_SKIP:
            result = pick_skip_completed(pdf_paths, target_subfolder, allow_back=True)
            if result is BACK:
                step = STEP_TARGET
                continue
            skip_completed = bool(result)
            # Detect whether a real prompt was shown (completed files exist).
            skip_prompt_shown = False
            for pdf in pdf_paths:
                try:
                    target_tex, _ = resolve_target_tex(pdf, target_subfolder, create_dir=False)
                    ok, _, _ = validate_existing_tex_and_pdf(target_tex)
                    if ok:
                        skip_prompt_shown = True
                        break
                except Exception:  # noqa: BLE001
                    continue
            step = STEP_MODEL
            continue

        if step == STEP_MODEL:
            result = pick_model(allow_back=True)
            if result is BACK:
                step = STEP_SKIP if skip_prompt_shown else STEP_TARGET
                continue
            model = result
            step = STEP_THINKING
            continue

        if step == STEP_THINKING:
            result = pick_thinking_level(target_subfolder, allow_back=True)
            if result is BACK:
                step = STEP_MODEL
                continue
            thinking_level = result
            step = STEP_MEDIA
            continue

        if step == STEP_MEDIA:
            result = pick_media_resolution(target_subfolder, allow_back=True)
            if result is BACK:
                step = STEP_THINKING
                continue
            media_resolution = result
            step = STEP_TRIM
            continue

        if step == STEP_TRIM:
            result = pick_trim_overlap(allow_back=True)
            if result is BACK:
                step = STEP_MEDIA
                continue
            trim_overlap_pages = bool(result)
            step = STEP_TIER
            continue

        if step == STEP_TIER:
            result = pick_execution_tier(allow_back=True)
            if result is BACK:
                step = STEP_TRIM
                continue
            execution_tier = result
            break

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
        skip_completed=skip_completed,
        media_resolution=media_resolution,
        trim_overlap_pages=trim_overlap_pages,
        backup_existing_tex=True,
    )
