"""Named automation job registry (settings, status, linked Gemini Batch IDs)."""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from .config import JOBS_PATH, PDF_ROOT, ensure_runtime_dirs, tier_label
from .reporter import SectionReport
from .ui_selector import RunSelection

console = Console()

STATUS_SUBMITTED = "submitted"
STATUS_RUNNING = "running"
STATUS_SUCCEEDED = "succeeded"
STATUS_FAILED = "failed"
STATUS_CANCELLED = "cancelled"
STATUS_PARTIAL = "partial"

ACTIVE_STATUSES = frozenset({STATUS_SUBMITTED, STATUS_RUNNING})
FAILED_LIKE_STATUSES = frozenset({STATUS_FAILED, STATUS_PARTIAL, STATUS_CANCELLED})

SECTION_PENDING = "pending"
SECTION_SUCCEEDED = "succeeded"
SECTION_SKIPPED = "skipped"
SECTION_FAILED = "failed"


def _classify_section_row(
    latex_validation: str,
    compile_status: str,
    tier_used: str = "",
    error: str = "",
) -> str:
    if tier_used == "skipped":
        return SECTION_SKIPPED
    if "Pending batch" in (error or ""):
        return SECTION_PENDING
    if latex_validation != "OK":
        return SECTION_FAILED
    if compile_status.startswith("Failed") or (error and not compile_status.startswith("Compiled")):
        return SECTION_FAILED
    if compile_status.startswith("Compiled") or compile_status == "Skipped":
        return SECTION_SUCCEEDED
    return SECTION_FAILED if error else SECTION_SUCCEEDED


def get_section_statuses(job: dict[str, Any]) -> list[dict[str, Any]]:
    """
    Return normalized per-section status dicts for a job.

    Uses persisted `section_statuses` when present, falling back to `token_diagnostics`
    + `settings.items` for historical jobs created before per-section persistence.
    """
    persisted = job.get("section_statuses")
    if isinstance(persisted, list) and persisted:
        return [dict(entry) for entry in persisted if isinstance(entry, dict)]

    settings = job.get("settings") or {}
    items = settings.get("items") or []
    diag = job.get("token_diagnostics")
    diag_sections = diag.get("sections") if isinstance(diag, dict) else []
    by_pdf_name: dict[str, dict[str, Any]] = {}
    if isinstance(diag_sections, list):
        for sec in diag_sections:
            if isinstance(sec, dict) and sec.get("pdf_name"):
                by_pdf_name[str(sec["pdf_name"])] = sec

    synthesized: list[dict[str, Any]] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        pdf_path = str(item.get("pdf_path") or "")
        pdf_name = Path(pdf_path).name if pdf_path else str(item.get("topic") or "")
        sec = by_pdf_name.get(pdf_name)
        if sec:
            latex_val = str(sec.get("latex_validation") or "")
            comp_val = str(sec.get("compile_status") or "")
            status = _classify_section_row(latex_val, comp_val)
            cost = float(sec.get("estimated_cost_usd") or 0.0)
        else:
            latex_val = ""
            comp_val = ""
            job_st = str(job.get("status") or "")
            status = SECTION_PENDING if job_st in ACTIVE_STATUSES else (
                SECTION_SUCCEEDED if job_st == STATUS_SUCCEEDED else SECTION_FAILED
            )
            cost = 0.0
        synthesized.append(
            {
                "pdf_path": pdf_path,
                "pdf_name": pdf_name,
                "topic": str(item.get("topic") or ""),
                "section_number": str(item.get("section_number") or ""),
                "target_tex_path": str(item.get("target_tex_path") or ""),
                "status": status,
                "latex_validation": latex_val,
                "compile_status": comp_val,
                "estimated_cost_usd": cost,
                "error": "",
            }
        )
    return synthesized


def get_failed_section_items(
    job: dict[str, Any],
    *,
    verify_disk: bool = True,
) -> list[dict[str, Any]]:
    """
    Return the subset of `job['settings']['items']` whose section failed, was truncated,
    never finished, or (when verify_disk=True) lacks a valid `.tex` + compiled `.pdf`.
    """
    from .latex_processor import validate_existing_tex_and_pdf

    settings = job.get("settings") or {}
    items = [i for i in (settings.get("items") or []) if isinstance(i, dict)]
    statuses = get_section_statuses(job)
    by_pdf_path = {str(s.get("pdf_path") or ""): s for s in statuses}
    by_pdf_name = {str(s.get("pdf_name") or ""): s for s in statuses}

    failed_items: list[dict[str, Any]] = []
    for item in items:
        pdf_path = str(item.get("pdf_path") or "")
        pdf_name = Path(pdf_path).name if pdf_path else ""
        target_tex = str(item.get("target_tex_path") or "")
        st_entry = by_pdf_path.get(pdf_path) or by_pdf_name.get(pdf_name)
        st = str((st_entry or {}).get("status") or SECTION_FAILED)

        if st not in {SECTION_SUCCEEDED, SECTION_SKIPPED}:
            failed_items.append(item)
            continue

        if verify_disk and target_tex:
            ok_disk, _, _ = validate_existing_tex_and_pdf(Path(target_tex))
            if not ok_disk:
                failed_items.append(item)
    return failed_items


def effective_job_status(job: dict[str, Any]) -> str:
    """
    Derive a display status that corrects historical mislabels.

    Jobs that were stored as succeeded while sections had TRUNCATED_LATEX or
    Failed compile statuses are surfaced as partial/failed for history filters.
    """
    stored = str(job.get("status") or "")
    if stored in ACTIVE_STATUSES:
        return stored

    persisted = job.get("section_statuses")
    if isinstance(persisted, list) and persisted:
        bad = sum(
            1
            for s in persisted
            if isinstance(s, dict)
            and str(s.get("status") or "") not in {SECTION_SUCCEEDED, SECTION_SKIPPED}
        )
        if bad == 0:
            return STATUS_SUCCEEDED if stored != STATUS_CANCELLED else STATUS_CANCELLED
        if bad >= len(persisted):
            return STATUS_FAILED if stored != STATUS_CANCELLED else STATUS_CANCELLED
        return STATUS_PARTIAL

    diag = job.get("token_diagnostics")
    sections = diag.get("sections") if isinstance(diag, dict) else None
    if not isinstance(sections, list) or not sections:
        return stored

    bad = 0
    for sec in sections:
        if not isinstance(sec, dict):
            continue
        latex = str(sec.get("latex_validation") or "")
        compile_status = str(sec.get("compile_status") or "")
        if latex in {"TRUNCATED_LATEX", "MISSING_DOCUMENTCLASS", "UNBALANCED_DOCUMENT", "LEFTOVER_FENCES"}:
            bad += 1
        elif compile_status.startswith("Failed"):
            bad += 1

    if bad == 0:
        return stored
    if bad >= len(sections):
        return STATUS_FAILED if stored != STATUS_CANCELLED else STATUS_CANCELLED
    return STATUS_PARTIAL


def filter_jobs(
    jobs: list[dict[str, Any]] | None = None,
    *,
    view: str = "current",
    model: str | None = None,
) -> list[dict[str, Any]]:
    """
    view: 'current' | 'succeeded' | 'failed' | 'all' | 'model'
    """
    jobs = jobs if jobs is not None else load_jobs()
    filtered: list[dict[str, Any]] = []
    for job in jobs:
        status = effective_job_status(job)
        settings = job.get("settings") or {}
        job_model = str(settings.get("model") or "")
        if view == "current":
            if status not in ACTIVE_STATUSES:
                continue
        elif view == "succeeded":
            if status != STATUS_SUCCEEDED:
                continue
        elif view == "failed":
            if status not in FAILED_LIKE_STATUSES:
                continue
        elif view == "all":
            pass
        elif view == "model":
            if model and job_model != model:
                continue
        else:
            pass
        if model and view != "model" and job_model != model:
            continue
        filtered.append(job)
    return filtered


def models_present(jobs: list[dict[str, Any]] | None = None) -> list[tuple[str, int]]:
    jobs = jobs if jobs is not None else load_jobs()
    counts: dict[str, int] = {}
    for job in jobs:
        model = str((job.get("settings") or {}).get("model") or "(unknown)")
        counts[model] = counts.get(model, 0) + 1
    return sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_jobs() -> list[dict[str, Any]]:
    ensure_runtime_dirs()
    if not JOBS_PATH.exists():
        return []
    try:
        data = json.loads(JOBS_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []
    return data if isinstance(data, list) else []


def save_jobs(jobs: list[dict[str, Any]]) -> None:
    ensure_runtime_dirs()
    JOBS_PATH.write_text(json.dumps(jobs, indent=2), encoding="utf-8")


def get_job(job_id: str) -> dict[str, Any] | None:
    for job in load_jobs():
        if job.get("id") == job_id:
            return job
    return None


def upsert_job(record: dict[str, Any]) -> None:
    jobs = load_jobs()
    jobs = [j for j in jobs if j.get("id") != record.get("id")]
    jobs.append(record)
    # Newest first for listing comfort
    jobs.sort(key=lambda j: j.get("created_at", ""), reverse=True)
    save_jobs(jobs)


def update_job(job_id: str, **fields: Any) -> dict[str, Any] | None:
    jobs = load_jobs()
    updated: dict[str, Any] | None = None
    for job in jobs:
        if job.get("id") == job_id:
            job.update(fields)
            job["updated_at"] = _now()
            updated = job
            break
    if updated is not None:
        save_jobs(jobs)
    return updated


def attach_batch_name(job_id: str, batch_job_name: str) -> None:
    job = get_job(job_id)
    if not job:
        return
    names = list(job.get("gemini_batch_names") or [])
    if batch_job_name not in names:
        names.append(batch_job_name)
    update_job(job_id, gemini_batch_names=names, status=STATUS_RUNNING)


def selection_snapshot(selection: RunSelection, items_meta: list[dict[str, Any]]) -> dict[str, Any]:
    pdf_root = PDF_ROOT.resolve()

    def rel_pdf(path: Path) -> str:
        try:
            return str(path.resolve().relative_to(pdf_root))
        except ValueError:
            return str(path)

    return {
        "pdf_files": [
            {"name": p.name, "path": str(p.resolve()), "relative": rel_pdf(p)}
            for p in selection.pdf_paths
        ],
        "prompt_files": [p.name for p in selection.prompt_paths],
        "prompt_paths": [str(p.resolve()) for p in selection.prompt_paths],
        "system_instruction": (
            selection.system_instruction_path.name
            if selection.system_instruction_path
            else None
        ),
        "system_instruction_path": (
            str(selection.system_instruction_path.resolve())
            if selection.system_instruction_path
            else None
        ),
        "target_subfolder": selection.target_subfolder,
        "model": selection.model,
        "thinking_level": selection.thinking_level,
        "execution_tier": selection.execution_tier,
        "execution_tier_label": tier_label(selection.execution_tier),
        "skip_completed": bool(getattr(selection, "skip_completed", False)),
        "media_resolution": str(getattr(selection, "media_resolution", "medium")),
        "trim_overlap_pages": bool(getattr(selection, "trim_overlap_pages", True)),
        "backup_existing_tex": bool(getattr(selection, "backup_existing_tex", True)),
        "items": items_meta,
    }


def summarize_token_diagnostics(rows: list[SectionReport]) -> dict[str, Any]:
    """Summarize per-section initial vs continuation-billed tokens for jobs.json."""
    sections = []
    total_init = 0
    total_billed = 0
    total_cached = 0
    total_think = 0
    total_out = 0
    total_cost = 0.0
    for r in rows:
        init_in = r.initial_input_tokens or r.preflight_tokens or r.input_tokens
        total_init += init_in
        total_billed += r.input_tokens
        total_cached += r.cached_tokens
        total_think += r.thinking_tokens
        total_out += r.output_tokens
        total_cost += r.estimated_cost_usd
        sections.append(
            {
                "pdf_name": r.pdf_name,
                "topic": r.topic,
                "initial_input_tokens": init_in,
                "billed_input_tokens": r.input_tokens,
                "preflight_tokens": r.preflight_tokens,
                "cached_tokens": r.cached_tokens,
                "thinking_tokens": r.thinking_tokens,
                "output_tokens": r.output_tokens,
                "estimated_cost_usd": r.estimated_cost_usd,
                "latex_validation": r.latex_validation,
                "compile_status": r.compile_status,
            }
        )
    return {
        "total_initial_input_tokens": total_init,
        "total_billed_input_tokens": total_billed,
        "total_cached_tokens": total_cached,
        "total_thinking_tokens": total_think,
        "total_output_tokens": total_out,
        "total_estimated_cost_usd": round(total_cost, 6),
        "sections": sections,
    }


def _initial_section_statuses(items_meta: list[dict[str, Any]]) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    for item in items_meta:
        pdf_path = str(item.get("pdf_path") or "")
        entries.append(
            {
                "pdf_path": pdf_path,
                "pdf_name": Path(pdf_path).name if pdf_path else "",
                "topic": str(item.get("topic") or ""),
                "section_number": str(item.get("section_number") or ""),
                "target_tex_path": str(item.get("target_tex_path") or ""),
                "status": SECTION_PENDING,
                "latex_validation": "N/A",
                "compile_status": "Pending",
                "estimated_cost_usd": 0.0,
                "error": "",
                "updated_at": _now(),
            }
        )
    return entries


def update_job_section_from_report(job_id: str, row: SectionReport, *, pdf_path: str = "") -> None:
    """Persist live completion/failure status for a single section on an active job."""
    job = get_job(job_id)
    if not job:
        return
    statuses = get_section_statuses(job)
    new_status = _classify_section_row(
        row.latex_validation,
        row.compile_status,
        tier_used=row.tier_used,
        error=row.error,
    )
    matched = False
    for entry in statuses:
        same_path = bool(pdf_path) and str(entry.get("pdf_path") or "") == pdf_path
        same_name = str(entry.get("pdf_name") or "") == row.pdf_name
        if same_path or same_name:
            entry.update(
                {
                    "status": new_status,
                    "tier_used": row.tier_used,
                    "latex_validation": row.latex_validation,
                    "compile_status": row.compile_status,
                    "estimated_cost_usd": row.estimated_cost_usd,
                    "error": row.error,
                    "updated_at": _now(),
                }
            )
            matched = True
            break
    if not matched:
        statuses.append(
            {
                "pdf_path": pdf_path,
                "pdf_name": row.pdf_name,
                "topic": row.topic,
                "section_number": "",
                "target_tex_path": row.target_tex_path,
                "status": new_status,
                "tier_used": row.tier_used,
                "latex_validation": row.latex_validation,
                "compile_status": row.compile_status,
                "estimated_cost_usd": row.estimated_cost_usd,
                "error": row.error,
                "updated_at": _now(),
            }
        )
    update_job(job_id, section_statuses=statuses)


def sync_section_statuses_from_reports(
    job_id: str,
    rows: list[SectionReport],
) -> list[dict[str, Any]]:
    """Merge a batch/subset of SectionReports into the job's persisted `section_statuses`."""
    job = get_job(job_id)
    if not job:
        return []
    for row in rows:
        update_job_section_from_report(job_id, row)
    refreshed = get_job(job_id)
    return get_section_statuses(refreshed) if refreshed else []


def create_named_job(
    name: str,
    selection: RunSelection,
    items_meta: list[dict[str, Any]],
) -> dict[str, Any]:
    record = {
        "id": str(uuid.uuid4()),
        "name": name.strip(),
        "created_at": _now(),
        "updated_at": _now(),
        "status": STATUS_SUBMITTED,
        "settings": selection_snapshot(selection, items_meta),
        "gemini_batch_names": [],
        "report_md": None,
        "report_json": None,
        "token_diagnostics": None,
        "section_statuses": _initial_section_statuses(items_meta),
        "section_count": len(items_meta),
        "error_summary": None,
    }
    upsert_job(record)
    return record


def print_job_settings(job: dict[str, Any]) -> None:
    settings = job.get("settings") or {}
    pdfs = settings.get("pdf_files") or []

    pdf_table = Table(title="Source PDFs", show_lines=True)
    pdf_table.add_column("#", justify="right", style="cyan")
    pdf_table.add_column("File name", overflow="fold")
    pdf_table.add_column("Relative path", overflow="fold")
    for i, pdf in enumerate(pdfs, start=1):
        pdf_table.add_row(str(i), pdf.get("name", ""), pdf.get("relative", pdf.get("path", "")))

    items = settings.get("items") or []
    map_table = Table(title="Target mapping", show_lines=True)
    map_table.add_column("PDF")
    map_table.add_column("Topic")
    map_table.add_column("Target .tex", overflow="fold")
    for item in items:
        map_table.add_row(
            Path(item.get("pdf_path", "")).name,
            item.get("topic", ""),
            item.get("target_tex_path", ""),
        )

    batches = job.get("gemini_batch_names") or []
    lines = [
        f"[bold]Name:[/bold] {job.get('name')}",
        f"[bold]ID:[/bold] {job.get('id')}",
        f"[bold]Status:[/bold] {job.get('status')}",
        f"[bold]Created:[/bold] {job.get('created_at')}",
        f"[bold]Updated:[/bold] {job.get('updated_at')}",
        "",
        f"[bold]Model:[/bold] {settings.get('model')}",
        f"[bold]Thinking:[/bold] {settings.get('thinking_level')}",
        f"[bold]Tier:[/bold] {settings.get('execution_tier_label') or settings.get('execution_tier')}",
        f"[bold]Target folder:[/bold] {settings.get('target_subfolder')}",
        f"[bold]Prompts:[/bold] {', '.join(settings.get('prompt_files') or []) or '(none)'}",
        f"[bold]System:[/bold] {settings.get('system_instruction') or '(None)'}",
        f"[bold]Sections:[/bold] {job.get('section_count', len(pdfs))}",
        f"[bold]Gemini Batch IDs:[/bold] {', '.join(batches) if batches else '(none)'}",
    ]
    if job.get("report_md"):
        lines.append(f"[bold]Report:[/bold] {job.get('report_md')}")
    if job.get("report_json"):
        lines.append(f"[bold]Report JSON:[/bold] {job.get('report_json')}")
    diag = job.get("token_diagnostics")
    if isinstance(diag, dict):
        lines.append(
            f"[bold]Tokens (InitIn / BilledIn / Cache / Think / Out):[/bold] "
            f"{diag.get('total_initial_input_tokens', 0):,} / "
            f"{diag.get('total_billed_input_tokens', 0):,} / "
            f"{diag.get('total_cached_tokens', 0):,} / "
            f"{diag.get('total_thinking_tokens', 0):,} / "
            f"{diag.get('total_output_tokens', 0):,} "
            f"(${diag.get('total_estimated_cost_usd', 0.0):.4f})"
        )
    if job.get("error_summary"):
        lines.append(f"[bold red]Errors:[/bold red] {job.get('error_summary')}")

    console.print(Panel("\n".join(lines), title="Job settings", border_style="cyan"))
    if pdfs:
        console.print(pdf_table)
    if items:
        console.print(map_table)
    sec_statuses = get_section_statuses(job)
    if sec_statuses and job.get("id") != "(pending)":
        sec_table = Table(title="Per-section status", show_lines=True)
        sec_table.add_column("Section", overflow="fold")
        sec_table.add_column("Status", no_wrap=True)
        sec_table.add_column("LaTeX", no_wrap=True)
        sec_table.add_column("Compile", overflow="fold")
        sec_table.add_column("Cost", justify="right", no_wrap=True)
        for sec in sec_statuses:
            st = str(sec.get("status") or "")
            style = (
                "green"
                if st == SECTION_SUCCEEDED
                else ("cyan" if st == SECTION_SKIPPED else ("yellow" if st == SECTION_PENDING else "red"))
            )
            comp_short = str(sec.get("compile_status") or "")
            if comp_short.startswith("Compiled ("):
                comp_short = "Compiled"
            elif len(comp_short) > 44:
                comp_short = comp_short[:41] + "..."
            sec_table.add_row(
                str(sec.get("pdf_name") or sec.get("topic") or ""),
                f"[{style}]{st}[/{style}]",
                str(sec.get("latex_validation") or "-"),
                comp_short or "-",
                f"${float(sec.get('estimated_cost_usd') or 0.0):.4f}",
            )
        console.print(sec_table)


def print_jobs_table(
    jobs: list[dict[str, Any]] | None = None,
    *,
    title: str | None = None,
) -> None:
    jobs = jobs if jobs is not None else load_jobs()
    table = Table(
        title=title or f"Automation jobs ({len(jobs)})",
        show_lines=True,
    )
    table.add_column("Name", overflow="fold")
    table.add_column("Status")
    table.add_column("Sections", justify="right")
    table.add_column("Model")
    table.add_column("Tier", overflow="fold")
    table.add_column("Created", overflow="fold")
    table.add_column("ID", overflow="fold")

    if not jobs:
        console.print(table)
        console.print("[dim]No jobs in this view.[/dim]")
        return

    for job in jobs:
        settings = job.get("settings") or {}
        stored = str(job.get("status", ""))
        effective = effective_job_status(job)
        status_label = stored if stored == effective else f"{stored}→{effective}"
        table.add_row(
            job.get("name", ""),
            status_label,
            str(job.get("section_count", "")),
            str(settings.get("model", "")),
            str(settings.get("execution_tier_label") or settings.get("execution_tier", "")),
            str(job.get("created_at", ""))[:19].replace("T", " "),
            str(job.get("id", ""))[:8],
        )
    console.print(table)


def ask_job_name_and_confirm(selection: RunSelection, items_meta: list[dict[str, Any]]) -> dict[str, Any] | None:
    """Prompt for a job name, show full settings, confirm submit. Returns job record or None."""
    import questionary

    default = datetime.now().strftime("job-%Y%m%d-%H%M%S")
    name = questionary.text(
        "Name this job before submit",
        default=default,
        validate=lambda s: True if s and s.strip() else "Job name required",
    ).ask()
    if not name:
        return None

    preview = {
        "id": "(pending)",
        "name": name.strip(),
        "created_at": _now(),
        "updated_at": _now(),
        "status": STATUS_SUBMITTED,
        "settings": selection_snapshot(selection, items_meta),
        "gemini_batch_names": [],
        "section_count": len(items_meta),
    }
    print_job_settings(preview)

    ok = questionary.confirm(
        f"Submit job '{name.strip()}' with these settings?",
        default=True,
    ).ask()
    if not ok:
        console.print("[yellow]Submission cancelled.[/yellow]")
        return None

    record = create_named_job(name.strip(), selection, items_meta)
    console.print(
        Panel(
            f"[bold green]Job submitted[/bold green]\n"
            f"Name: [cyan]{record['name']}[/cyan]\n"
            f"ID: {record['id']}\n"
            f"Sections: {record['section_count']}\n\n"
            f"Use [bold]Run Jobs.bat[/bold] to inspect, cancel, or review settings later.",
            title="Confirmation",
            border_style="green",
        )
    )
    return record
