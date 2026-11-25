"""CLI entry point and interactive workflow orchestrator."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from rich.console import Console
from rich.table import Table

from .config import MATHTEX_ROOT, MEDIA_RESOLUTIONS, PDF_MEDIA_RESOLUTION, ensure_runtime_dirs
from .gemini_runner import (
    WorkItem,
    confirm_budget_or_abort,
    create_client,
    estimate_job_preflight_costs,
    manage_batches_cli,
    outcome_to_report,
    run_items,
)
from .job_store import (
    STATUS_FAILED,
    STATUS_PARTIAL,
    STATUS_SUCCEEDED,
    ask_job_name_and_confirm,
    summarize_token_diagnostics,
    sync_section_statuses_from_reports,
    update_job,
)
from .jobs_manager import manage_jobs_cli
from .path_mapper import map_pdf_to_tex
from .reporter import print_summary_table, write_reports
from .ui_selector import RunSelection, assemble_prompt_text, run_interactive_selection

console = Console()


def _load_api_key() -> str:
    env_path = MATHTEX_ROOT / ".env"
    example_path = MATHTEX_ROOT / ".env.example"
    load_dotenv(env_path, override=True)
    key = os.getenv("GEMINI_API_KEY", "").strip()
    if key and key != "your_api_key_here":
        return key

    # Common mistake: key only written into .env.example
    if example_path.is_file():
        load_dotenv(example_path, override=True)
        example_key = os.getenv("GEMINI_API_KEY", "").strip()
        if example_key and example_key != "your_api_key_here":
            env_path.write_text(
                f"GEMINI_API_KEY={example_key}\n",
                encoding="utf-8",
            )
            example_path.write_text(
                "GEMINI_API_KEY=your_api_key_here\n",
                encoding="utf-8",
            )
            console.print(
                "[yellow]Found key in .env.example — copied it to .env "
                "(keep secrets in .env, not .env.example).[/yellow]"
            )
            return example_key

    console.print(
        f"[red]GEMINI_API_KEY not set.[/red]\n"
        f"Create [bold]{env_path}[/bold] with:\n"
        f"  GEMINI_API_KEY=your_real_key\n"
        f"(Do not put the real key only in .env.example.)"
    )
    raise SystemExit(1)


def _build_work_items(selection: RunSelection) -> list[WorkItem]:
    items: list[WorkItem] = []
    for pdf in selection.pdf_paths:
        mapped = map_pdf_to_tex(pdf, selection.target_subfolder)
        items.append(WorkItem(mapped=mapped, user_prompt=selection.prompt_text))
    return items


def _print_dry_run(items: list[WorkItem], selection: RunSelection) -> None:
    table = Table(title="Dry-run path & scope mapping", show_lines=True)
    table.add_column("Source PDF")
    table.add_column("Section")
    table.add_column("Topic")
    table.add_column("Target .tex")
    table.add_column("New?")
    for item in items:
        table.add_row(
            item.mapped.pdf_path.name,
            item.mapped.section_number or "-",
            item.mapped.topic,
            str(item.mapped.target_tex_path),
            "yes" if item.mapped.created_new else "overwrite",
        )
    console.print(table)
    console.print(f"Model: {selection.model}")
    console.print(f"Thinking: {selection.thinking_level}")
    console.print(f"Media: {selection.media_resolution}")
    console.print(f"API trim: {'yes' if selection.trim_overlap_pages else 'no'}")
    console.print(f"Skip completed: {'yes' if selection.skip_completed else 'no'}")
    console.print(f"Tier: {selection.execution_tier}")
    console.print(f"Prompts: {', '.join(p.name for p in selection.prompt_paths)}")
    if selection.system_instruction_path:
        console.print(f"System: {selection.system_instruction_path.name}")
    else:
        console.print("System: (None)")


def _items_meta(items: list[WorkItem]) -> list[dict]:
    return [
        {
            "pdf_path": str(item.mapped.pdf_path),
            "target_tex_path": str(item.mapped.target_tex_path),
            "topic": item.mapped.topic,
            "section_number": item.mapped.section_number,
        }
        for item in items
    ]


def run_pipeline(
    selection: RunSelection,
    *,
    dry_run: bool = False,
    require_named_job: bool = True,
) -> int:
    items = _build_work_items(selection)
    if dry_run:
        _print_dry_run(items, selection)
        return 0

    api_key = _load_api_key()
    client = create_client(api_key)

    if require_named_job:
        console.print("[bold]Counting tokens for pre-submit cost estimate…[/bold]")
        estimate = estimate_job_preflight_costs(
            client,
            items,
            model=selection.model,
            thinking_level=selection.thinking_level,
            execution_tier=selection.execution_tier,
            system_instruction=selection.system_instruction_text,
            media_resolution=selection.media_resolution,
            trim_overlap_pages=selection.trim_overlap_pages,
        )
        if not confirm_budget_or_abort(estimate):
            console.print("[yellow]Submission cancelled at cost gate.[/yellow]")
            return 0

    local_job_id: str | None = None
    job_name: str | None = None
    if require_named_job:
        job = ask_job_name_and_confirm(selection, _items_meta(items))
        if job is None:
            return 0
        local_job_id = job["id"]
        job_name = job["name"]

    console.print(
        f"[bold]Running {len(items)} section(s)"
        + (f" for job '{job_name}'…" if job_name else "…")
        + "[/bold]"
    )
    outcomes = run_items(
        client,
        items,
        api_key=api_key,
        model=selection.model,
        thinking_level=selection.thinking_level,
        execution_tier=selection.execution_tier,
        system_instruction=selection.system_instruction_text,
        local_job_id=local_job_id,
        skip_completed=selection.skip_completed,
        media_resolution=selection.media_resolution,
        trim_overlap_pages=selection.trim_overlap_pages,
        backup_existing_tex=selection.backup_existing_tex,
    )
    rows = [outcome_to_report(o, selection.model) for o in outcomes]
    print_summary_table(rows)
    md, js = write_reports(
        rows,
        model=selection.model,
        tier=selection.execution_tier,
        job_name=job_name,
        job_id=local_job_id,
    )
    console.print(f"[green]Reports:[/green] {md}")
    console.print(f"[green]JSON:[/green] {js}")
    failures = sum(1 for o in outcomes if not o.success)
    pending = sum(
        1
        for o in outcomes
        if (not o.success) and "Pending batch" in (o.error or "")
    )
    token_diag = summarize_token_diagnostics(rows)
    if local_job_id:
        sync_section_statuses_from_reports(local_job_id, rows)
        if pending and failures == pending:
            # Left waiting on Gemini Batch — keep running/submitted state
            update_job(
                local_job_id,
                status="running",
                report_md=str(md),
                report_json=str(js),
                token_diagnostics=token_diag,
            )
        elif failures == 0:
            update_job(
                local_job_id,
                status=STATUS_SUCCEEDED,
                report_md=str(md),
                report_json=str(js),
                token_diagnostics=token_diag,
            )
            console.print(
                f"[bold green]Job completed successfully.[/bold green] "
                f"Inspect anytime with Run Jobs.bat."
            )
        elif failures < len(outcomes):
            update_job(
                local_job_id,
                status=STATUS_PARTIAL,
                report_md=str(md),
                report_json=str(js),
                token_diagnostics=token_diag,
                error_summary=f"{failures}/{len(outcomes)} section(s) failed",
            )
        else:
            update_job(
                local_job_id,
                status=STATUS_FAILED,
                report_md=str(md),
                report_json=str(js),
                token_diagnostics=token_diag,
                error_summary=f"All {failures} section(s) failed",
            )
    return 1 if failures else 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m automation.main",
        description="MathTex Gemini automation: PDF sections → LaTeX → compiled PDFs",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Map PDFs to .tex targets and print the plan without calling Gemini.",
    )
    parser.add_argument(
        "--batches",
        action="store_true",
        help="Legacy: inspect raw Gemini Batch IDs in automation/.state/batch_jobs.json",
    )
    parser.add_argument(
        "--jobs",
        action="store_true",
        help="Manage named automation jobs (same as Run Jobs.bat).",
    )
    parser.add_argument(
        "--job-name",
        type=str,
        default=None,
        help="Non-interactive: job name (skips name prompt when --pdf is used).",
    )
    parser.add_argument(
        "--pdf",
        type=Path,
        action="append",
        default=None,
        help="Non-interactive: add a source PDF (repeatable).",
    )
    parser.add_argument(
        "--prompt",
        type=Path,
        action="append",
        default=None,
        help="Non-interactive: prompt .txt path (repeatable, join order).",
    )
    parser.add_argument(
        "--system",
        type=Path,
        default=None,
        help="Non-interactive: system instruction .txt/.md path.",
    )
    parser.add_argument(
        "--target",
        type=str,
        default="Homework",
        help="Target .tex subfolder (default: Homework).",
    )
    parser.add_argument(
        "--model",
        type=str,
        default=None,
        help="Model id (default: gemini-4-argon). Also: gemini-4-carbon, gemini-4-neon, gemini-4-hydrogen, gemini-3.1-pro-preview.",
    )
    parser.add_argument(
        "--thinking",
        type=str,
        choices=("low", "medium", "high", "xhigh"),
        default="high",
        help="Thinking level: low|medium|high|xhigh (xhigh only on neon/hydrogen; clamped per model).",
    )
    parser.add_argument(
        "--tier",
        type=str,
        choices=(
            "flex_batch_fallback",
            "flex_only",
            "batch_only",
            "standard",
        ),
        default="flex_batch_fallback",
        help="Execution tier.",
    )
    parser.add_argument(
        "--skip-existing",
        action="store_true",
        help="Skip sections whose target .tex validates OK and compiled PDF exists.",
    )
    parser.add_argument(
        "--media",
        type=str,
        choices=MEDIA_RESOLUTIONS,
        default=None,
        help="PDF media_resolution for API tokenization (low/medium/high).",
    )
    parser.add_argument(
        "--no-trim",
        action="store_true",
        help="Disable API-only overlap page trimming.",
    )
    parser.add_argument(
        "--no-backup",
        action="store_true",
        help="Do not write .tex.bak before overwrite.",
    )
    return parser


def selection_from_args(args: argparse.Namespace) -> RunSelection:
    from .config import DEFAULT_MODEL, clamp_thinking_level
    from .ui_selector import RunSelection as RS

    if not args.pdf or not args.prompt:
        raise SystemExit("--pdf and --prompt are required in non-interactive mode.")

    prompt_paths = [Path(p) for p in args.prompt]
    for p in prompt_paths:
        if not p.is_file():
            raise SystemExit(f"Prompt not found: {p}")
    prompt_text = assemble_prompt_text(prompt_paths)

    system_path = Path(args.system) if args.system else None
    system_text = system_path.read_text(encoding="utf-8") if system_path else None

    pdf_paths = [Path(p) for p in args.pdf]
    for p in pdf_paths:
        if not p.is_file():
            raise SystemExit(f"PDF not found: {p}")

    model = args.model or DEFAULT_MODEL
    return RS(
        pdf_paths=pdf_paths,
        prompt_paths=prompt_paths,
        prompt_text=prompt_text,
        system_instruction_path=system_path,
        system_instruction_text=system_text,
        target_subfolder=args.target,
        model=model,
        thinking_level=clamp_thinking_level(model, args.thinking),
        execution_tier=args.tier,
        skip_completed=bool(getattr(args, "skip_existing", False)),
        media_resolution=str(getattr(args, "media", None) or PDF_MEDIA_RESOLUTION),
        trim_overlap_pages=not bool(getattr(args, "no_trim", False)),
        backup_existing_tex=not bool(getattr(args, "no_backup", False)),
    )


def main(argv: list[str] | None = None) -> int:
    ensure_runtime_dirs()
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.jobs:
        api_key = _load_api_key()
        client = create_client(api_key)
        return manage_jobs_cli(client, api_key=api_key)

    if args.batches:
        api_key = _load_api_key()
        client = create_client(api_key)
        manage_batches_cli(client)
        return 0

    if args.pdf or args.prompt:
        selection = selection_from_args(args)
        if args.dry_run:
            return run_pipeline(selection, dry_run=True, require_named_job=False)
        # Non-interactive: still create a named job (name from flag or default).
        from .job_store import create_named_job

        items = _build_work_items(selection)
        name = args.job_name or __import__("datetime").datetime.now().strftime(
            "job-%Y%m%d-%H%M%S"
        )
        job = create_named_job(name, selection, _items_meta(items))
        console.print(
            f"[bold green]Job submitted:[/bold green] [cyan]{job['name']}[/cyan] "
            f"({job['id'][:8]}…)"
        )
        api_key = _load_api_key()
        client = create_client(api_key)
        outcomes = run_items(
            client,
            items,
            api_key=api_key,
            model=selection.model,
            thinking_level=selection.thinking_level,
            execution_tier=selection.execution_tier,
            system_instruction=selection.system_instruction_text,
            local_job_id=job["id"],
            skip_completed=selection.skip_completed,
            media_resolution=selection.media_resolution,
            trim_overlap_pages=selection.trim_overlap_pages,
            backup_existing_tex=selection.backup_existing_tex,
        )
        rows = [outcome_to_report(o, selection.model) for o in outcomes]
        print_summary_table(rows)
        md, js = write_reports(
            rows,
            model=selection.model,
            tier=selection.execution_tier,
            job_name=job["name"],
            job_id=job["id"],
        )
        failures = sum(1 for o in outcomes if not o.success)
        sync_section_statuses_from_reports(job["id"], rows)
        update_job(
            job["id"],
            status=STATUS_SUCCEEDED if failures == 0 else STATUS_PARTIAL,
            report_md=str(md),
            report_json=str(js),
            token_diagnostics=summarize_token_diagnostics(rows),
        )
        return 1 if failures else 0

    selection = run_interactive_selection()
    return run_pipeline(selection, dry_run=args.dry_run, require_named_job=not args.dry_run)


if __name__ == "__main__":
    sys.exit(main())
