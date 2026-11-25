"""Interactive manager for named automation jobs (list / inspect / cancel / refresh)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import questionary
from questionary import Choice
from rich.console import Console

from .config import DEFAULT_MODEL, PROMPTS_DIR, SYSTEM_INSTRUCTIONS_DIR, clamp_thinking_level
from .gemini_runner import (
    WorkItem,
    _batch_state,
    cancel_batch,
    outcome_to_report,
    process_batch_success,
    run_items,
    wait_for_batch,
)
from .job_store import (
    STATUS_CANCELLED,
    STATUS_FAILED,
    STATUS_PARTIAL,
    STATUS_RUNNING,
    STATUS_SUCCEEDED,
    effective_job_status,
    filter_jobs,
    get_failed_section_items,
    get_job,
    load_jobs,
    models_present,
    print_job_settings,
    print_jobs_table,
    summarize_token_diagnostics,
    sync_section_statuses_from_reports,
    update_job,
)
from .path_mapper import MappedItem, extract_section_number
from .reporter import SectionReport, print_summary_table, write_reports
from .ui_selector import assemble_prompt_text

console = Console()


def _refresh_remote_status(client, job: dict[str, Any]) -> dict[str, Any]:
    batch_names = job.get("gemini_batch_names") or []
    if not batch_names:
        return job

    states: list[str] = []
    for name in batch_names:
        try:
            remote = client.batches.get(name=name)
            states.append(_batch_state(remote))
        except Exception as exc:  # noqa: BLE001
            states.append(f"ERROR:{exc}")

    job["remote_batch_states"] = dict(zip(batch_names, states, strict=False))

    if any(s.startswith("ERROR:") for s in states):
        pass
    elif all(s == "JOB_STATE_CANCELLED" for s in states):
        job["status"] = STATUS_CANCELLED
    elif all(s == "JOB_STATE_SUCCEEDED" for s in states):
        if job.get("status") in {STATUS_RUNNING, "submitted", "partial"}:
            job["status"] = STATUS_SUCCEEDED
    elif any(s in {"JOB_STATE_PENDING", "JOB_STATE_RUNNING"} for s in states):
        job["status"] = STATUS_RUNNING
    elif any(s == "JOB_STATE_FAILED" for s in states):
        job["status"] = STATUS_FAILED

    update_job(job["id"], **{k: job[k] for k in ("status", "remote_batch_states") if k in job})
    return get_job(job["id"]) or job


def _refresh_active_batches(client, jobs: list[dict[str, Any]]) -> None:
    for job in jobs:
        if job.get("gemini_batch_names") and job.get("status") in {
            "submitted",
            STATUS_RUNNING,
            "partial",
        }:
            _refresh_remote_status(client, job)


def _resolve_prompt_text_from_settings(settings: dict[str, Any]) -> str:
    raw_paths = settings.get("prompt_paths") or []
    raw_names = settings.get("prompt_files") or []
    resolved: list[Path] = []
    for p_str in raw_paths:
        p = Path(p_str)
        if p.is_file():
            resolved.append(p)
        elif (PROMPTS_DIR / p.name).is_file():
            resolved.append(PROMPTS_DIR / p.name)
    if not resolved:
        for name in raw_names:
            cand = PROMPTS_DIR / str(name)
            if cand.is_file():
                resolved.append(cand)
    if not resolved:
        raise FileNotFoundError("Could not locate original prompt file(s) for this job.")
    return assemble_prompt_text(resolved)


def _resolve_system_text_from_settings(settings: dict[str, Any]) -> str | None:
    sys_path_str = settings.get("system_instruction_path")
    sys_name = settings.get("system_instruction")
    if sys_path_str:
        p = Path(sys_path_str)
        if p.is_file():
            return p.read_text(encoding="utf-8")
    if sys_name:
        cand = SYSTEM_INSTRUCTIONS_DIR / str(sys_name)
        if cand.is_file():
            return cand.read_text(encoding="utf-8")
    return None


def _work_items_from_meta(items_meta: list[dict[str, Any]], prompt_text: str, default_subfolder: str) -> list[WorkItem]:
    work_items: list[WorkItem] = []
    for meta in items_meta:
        pdf_p = Path(str(meta.get("pdf_path") or ""))
        tex_p = Path(str(meta.get("target_tex_path") or ""))
        if not pdf_p.is_file():
            console.print(f"[red]Missing source PDF on disk, skipping:[/red] {pdf_p}")
            continue
        mapped = MappedItem(
            pdf_path=pdf_p.resolve(),
            rel_path=Path("."),
            topic=str(meta.get("topic") or pdf_p.stem),
            target_tex_path=tex_p.resolve(),
            target_subfolder=tex_p.parent.name if tex_p.parent else default_subfolder,
            created_new=not tex_p.is_file(),
            section_number=str(meta.get("section_number") or extract_section_number(pdf_p)),
        )
        work_items.append(WorkItem(mapped=mapped, user_prompt=prompt_text))
    return work_items


def _merge_reports_with_previous(
    job: dict[str, Any],
    new_rows: list[SectionReport],
) -> list[SectionReport]:
    """Preserve earlier succeeded section reports while replacing retried sections."""
    by_name = {r.pdf_name: r for r in new_rows}
    diag = job.get("token_diagnostics")
    prev_sections = diag.get("sections") if isinstance(diag, dict) else []
    settings_items = (job.get("settings") or {}).get("items") or []
    ordered_names = [
        Path(str(i.get("pdf_path") or "")).name
        for i in settings_items
        if isinstance(i, dict) and i.get("pdf_path")
    ]

    prev_by_name: dict[str, SectionReport] = {}
    if isinstance(prev_sections, list):
        for sec in prev_sections:
            if not isinstance(sec, dict) or not sec.get("pdf_name"):
                continue
            pname = str(sec["pdf_name"])
            prev_by_name[pname] = SectionReport(
                pdf_name=pname,
                topic=str(sec.get("topic") or ""),
                target_tex_path="",
                tier_used="previous",
                initial_input_tokens=int(sec.get("initial_input_tokens") or 0),
                input_tokens=int(sec.get("billed_input_tokens") or 0),
                cached_tokens=int(sec.get("cached_tokens") or 0),
                thinking_tokens=int(sec.get("thinking_tokens") or 0),
                output_tokens=int(sec.get("output_tokens") or 0),
                preflight_tokens=int(sec.get("preflight_tokens") or 0),
                estimated_cost_usd=float(sec.get("estimated_cost_usd") or 0.0),
                latex_validation=str(sec.get("latex_validation") or "OK"),
                compile_status=str(sec.get("compile_status") or "Compiled"),
            )

    merged: list[SectionReport] = []
    seen: set[str] = set()
    for name in ordered_names:
        if name in by_name:
            merged.append(by_name[name])
            seen.add(name)
        elif name in prev_by_name:
            merged.append(prev_by_name[name])
            seen.add(name)
    for r in new_rows:
        if r.pdf_name not in seen:
            merged.append(r)
    return merged


def _execute_job_rerun(
    client,
    job: dict[str, Any],
    *,
    api_key: str,
    failed_only: bool,
) -> None:
    settings = job.get("settings") or {}
    all_items_meta = [i for i in (settings.get("items") or []) if isinstance(i, dict)]
    target_meta = (
        get_failed_section_items(job, verify_disk=True)
        if failed_only
        else all_items_meta
    )
    if not target_meta:
        console.print("[green]All sections on this job already succeeded and have valid .tex + PDF outputs.[/green]")
        return

    try:
        prompt_text = _resolve_prompt_text_from_settings(settings)
    except FileNotFoundError as exc:
        console.print(f"[red]{exc}[/red]")
        return
    system_text = _resolve_system_text_from_settings(settings)
    subfolder = str(settings.get("target_subfolder") or "Homework")
    work_items = _work_items_from_meta(target_meta, prompt_text, subfolder)
    if not work_items:
        console.print("[red]No runnable PDFs found for retry.[/red]")
        return

    model = str(settings.get("model") or DEFAULT_MODEL)
    thinking = clamp_thinking_level(model, str(settings.get("thinking_level") or "high"))
    tier = str(settings.get("execution_tier") or "flex_batch_fallback")

    label = (
        f"Retry {len(work_items)}/{len(all_items_meta)} failed/incomplete section(s)"
        if failed_only
        else f"Resume {len(work_items)} section(s) with Skip-if-OK"
    )
    ok = questionary.confirm(
        f"{label} for '{job.get('name')}' using {model} ({tier})?",
        default=True,
    ).ask()
    if not ok:
        return

    outcomes = run_items(
        client,
        work_items,
        api_key=api_key,
        model=model,
        thinking_level=thinking,
        execution_tier=tier,
        system_instruction=system_text,
        local_job_id=job["id"],
        skip_completed=not failed_only,
        media_resolution=str(settings.get("media_resolution") or "medium"),
        trim_overlap_pages=bool(settings.get("trim_overlap_pages", True)),
        backup_existing_tex=bool(settings.get("backup_existing_tex", True)),
    )
    new_rows = [outcome_to_report(o, model) for o in outcomes]
    print_summary_table(new_rows)
    sync_section_statuses_from_reports(job["id"], new_rows)

    merged_rows = _merge_reports_with_previous(job, new_rows)
    md, js = write_reports(
        merged_rows,
        model=model,
        tier=tier,
        job_name=job.get("name"),
        job_id=job.get("id"),
    )
    refreshed = get_job(job["id"]) or job
    remaining_failed = get_failed_section_items(refreshed, verify_disk=False)
    if not remaining_failed:
        final_status = STATUS_SUCCEEDED
        err_summary = None
    elif len(remaining_failed) < len(all_items_meta):
        final_status = STATUS_PARTIAL
        err_summary = f"{len(remaining_failed)}/{len(all_items_meta)} section(s) failed"
    else:
        final_status = STATUS_FAILED
        err_summary = f"All {len(remaining_failed)} section(s) failed"

    update_job(
        job["id"],
        status=final_status,
        report_md=str(md),
        report_json=str(js),
        token_diagnostics=summarize_token_diagnostics(merged_rows),
        error_summary=err_summary,
    )
    console.print(f"[green]Updated job '{job.get('name')}' → {final_status}[/green]")
    console.print(f"[green]Reports:[/green] {md}")


def _job_action_menu(client, job: dict[str, Any], *, api_key: str = "") -> None:
    print_job_settings(job)

    all_items = (job.get("settings") or {}).get("items") or []
    failed_items = get_failed_section_items(job, verify_disk=True)

    menu_choices: list[Choice] = []
    if api_key and failed_items:
        menu_choices.append(
            Choice(
                f"Retry failed/incomplete sections only ({len(failed_items)}/{len(all_items)})",
                "retry_failed",
            )
        )
    if api_key and all_items:
        menu_choices.append(
            Choice(
                "Resume job (Skip sections where .tex OK + PDF exists)",
                "resume_skip",
            )
        )
    menu_choices.extend(
        [
            Choice("Refresh remote status", "refresh"),
            Choice("Wait & download Gemini Batch results (if any)", "wait"),
            Choice("Cancel job (Gemini Batch + mark cancelled)", "cancel"),
            Choice("Mark cancelled locally only", "cancel_local"),
            Choice("Back to list", "back"),
        ]
    )

    action = questionary.select(
        f"Action for '{job.get('name')}'",
        choices=menu_choices,
    ).ask()

    if action == "back" or action is None:
        return
    if action == "retry_failed":
        _execute_job_rerun(client, job, api_key=api_key, failed_only=True)
        return
    if action == "resume_skip":
        _execute_job_rerun(client, job, api_key=api_key, failed_only=False)
        return
    if action == "refresh":
        job = _refresh_remote_status(client, job)
        print_job_settings(job)
        return
    if action == "cancel_local":
        update_job(job["id"], status=STATUS_CANCELLED)
        console.print(f"[yellow]Marked '{job.get('name')}' cancelled locally.[/yellow]")
        return
    if action == "cancel":
        names = job.get("gemini_batch_names") or []
        if names:
            for name in names:
                try:
                    cancel_batch(client, name, local_job_id=job["id"])
                except Exception as exc:  # noqa: BLE001
                    console.print(f"[red]Cancel failed for {name}: {exc}[/red]")
        update_job(job["id"], status=STATUS_CANCELLED)
        console.print(f"[green]Job '{job.get('name')}' cancelled.[/green]")
        return
    if action == "wait":
        names = job.get("gemini_batch_names") or []
        if not names:
            console.print("[yellow]No Gemini Batch IDs on this job.[/yellow]")
            return
        all_outcomes = []
        model = (job.get("settings") or {}).get("model", "")
        for name in names:
            remote = wait_for_batch(client, name)
            state = _batch_state(remote)
            if state != "JOB_STATE_SUCCEEDED":
                console.print(f"[red]{name} ended as {state}[/red]")
                continue
            items = (job.get("settings") or {}).get("items") or []
            outcomes = process_batch_success(client, name, items, model=model)
            all_outcomes.extend(outcomes)
        if all_outcomes:
            rows = [outcome_to_report(o, model) for o in all_outcomes]
            print_summary_table(rows)
            md, js = write_reports(
                rows,
                model=model,
                tier="batch",
                job_name=job.get("name"),
                job_id=job.get("id"),
            )
            failures = sum(1 for o in all_outcomes if not o.success)
            status = STATUS_PARTIAL if failures else STATUS_SUCCEEDED
            sync_section_statuses_from_reports(job["id"], rows)
            update_job(
                job["id"],
                status=status,
                report_md=str(md),
                report_json=str(js),
                token_diagnostics=summarize_token_diagnostics(rows),
            )
            console.print(f"[green]Reports:[/green] {md}")
            console.print(f"[green]JSON:[/green] {js}")


def _browse_job_list(
    client,
    jobs: list[dict[str, Any]],
    *,
    title: str,
    empty_message: str,
    api_key: str = "",
) -> None:
    """Subview: pick a job to inspect, or go back."""
    while True:
        print_jobs_table(jobs, title=title)
        if not jobs:
            console.print(f"[yellow]{empty_message}[/yellow]")
            questionary.press_any_key_to_continue("Press Enter to go back…").ask()
            return

        choices = [
            Choice(
                title=f"{j.get('name')}  [{effective_job_status(j)}]  "
                f"{j.get('section_count')} sections  ({str(j.get('id', ''))[:8]})",
                value=j.get("id"),
            )
            for j in jobs
        ]
        choices.append(Choice(title="[Back to Current Jobs]", value="__back__"))

        selected = questionary.select(
            "Select a job to inspect",
            choices=choices,
        ).ask()
        if selected is None or selected == "__back__":
            return

        job = get_job(selected)
        if not job:
            console.print("[red]Job not found.[/red]")
            continue
        _job_action_menu(client, job, api_key=api_key)
        # Refresh list after actions
        all_jobs = load_jobs()
        # Re-apply same filter by matching ids from original view set
        id_set = {j.get("id") for j in jobs}
        jobs = [j for j in all_jobs if j.get("id") in id_set]


def manage_jobs_cli(client, *, api_key: str = "") -> int:
    while True:
        all_jobs = load_jobs()
        _refresh_active_batches(client, all_jobs)
        all_jobs = load_jobs()

        current = filter_jobs(all_jobs, view="current")
        succeeded = filter_jobs(all_jobs, view="succeeded")
        failed = filter_jobs(all_jobs, view="failed")

        print_jobs_table(
            current,
            title=f"Current jobs ({len(current)})",
        )
        if not current:
            console.print(
                "[dim]No active jobs currently running. "
                "Use history views below, or Run Automation.bat to submit one.[/dim]"
            )

        choices: list[Choice] = [
            Choice(
                title=f"{j.get('name')}  [{effective_job_status(j)}]  "
                f"{j.get('section_count')} sections  ({str(j.get('id', ''))[:8]})",
                value=j.get("id"),
            )
            for j in current
        ]
        choices.extend(
            [
                Choice(
                    title=f"[Succeeded History ({len(succeeded)})]",
                    value="__hist_succeeded__",
                ),
                Choice(
                    title=f"[Failed History ({len(failed)})]",
                    value="__hist_failed__",
                ),
                Choice(
                    title=f"[All History ({len(all_jobs)})]",
                    value="__hist_all__",
                ),
                Choice(title="[History by Model…]", value="__hist_model__"),
                Choice(title="[Refresh list]", value="__refresh__"),
                Choice(title="[Done]", value="__done__"),
            ]
        )

        selected = questionary.select(
            "Select a current job, or open a history view",
            choices=choices,
        ).ask()

        if selected is None or selected == "__done__":
            return 0
        if selected == "__refresh__":
            continue
        if selected == "__hist_succeeded__":
            _browse_job_list(
                client,
                succeeded,
                title=f"Succeeded history ({len(succeeded)})",
                empty_message="No succeeded jobs yet.",
                api_key=api_key,
            )
            continue
        if selected == "__hist_failed__":
            _browse_job_list(
                client,
                failed,
                title=f"Failed / partial / cancelled history ({len(failed)})",
                empty_message="No failed jobs.",
                api_key=api_key,
            )
            continue
        if selected == "__hist_all__":
            _browse_job_list(
                client,
                all_jobs,
                title=f"All history ({len(all_jobs)})",
                empty_message="No jobs yet.",
                api_key=api_key,
            )
            continue
        if selected == "__hist_model__":
            present = models_present(all_jobs)
            if not present:
                console.print("[yellow]No jobs with model metadata yet.[/yellow]")
                continue
            model_choices = [
                Choice(title=f"{m} ({n})", value=m) for m, n in present
            ]
            model_choices.append(Choice(title="[Back]", value="__back__"))
            model = questionary.select(
                "Filter history by model",
                choices=model_choices,
            ).ask()
            if model is None or model == "__back__":
                continue
            by_model = filter_jobs(all_jobs, view="model", model=model)
            _browse_job_list(
                client,
                by_model,
                title=f"History by model — {model} ({len(by_model)})",
                empty_message=f"No jobs for model {model}.",
                api_key=api_key,
            )
            continue

        job = get_job(selected)
        if not job:
            console.print("[red]Job not found.[/red]")
            continue
        _job_action_menu(client, job, api_key=api_key)
