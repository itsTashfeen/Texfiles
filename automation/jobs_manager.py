"""Interactive manager for named automation jobs (list / inspect / cancel / refresh)."""

from __future__ import annotations

from typing import Any

import questionary
from questionary import Choice
from rich.console import Console

from .gemini_runner import (
    _batch_state,
    cancel_batch,
    outcome_to_report,
    process_batch_success,
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
    get_job,
    load_jobs,
    models_present,
    print_job_settings,
    print_jobs_table,
    summarize_token_diagnostics,
    update_job,
)
from .reporter import print_summary_table, write_reports

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


def _job_action_menu(client, job: dict[str, Any]) -> None:
    print_job_settings(job)

    action = questionary.select(
        f"Action for '{job.get('name')}'",
        choices=[
            Choice("Refresh remote status", "refresh"),
            Choice("Wait & download Gemini Batch results (if any)", "wait"),
            Choice("Cancel job (Gemini Batch + mark cancelled)", "cancel"),
            Choice("Mark cancelled locally only", "cancel_local"),
            Choice("Back to list", "back"),
        ],
    ).ask()

    if action == "back" or action is None:
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
        _job_action_menu(client, job)
        # Refresh list after actions
        all_jobs = load_jobs()
        # Re-apply same filter by matching ids from original view set
        id_set = {j.get("id") for j in jobs}
        jobs = [j for j in all_jobs if j.get("id") in id_set]


def manage_jobs_cli(client) -> int:
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
            )
            continue
        if selected == "__hist_failed__":
            _browse_job_list(
                client,
                failed,
                title=f"Failed / partial / cancelled history ({len(failed)})",
                empty_message="No failed jobs.",
            )
            continue
        if selected == "__hist_all__":
            _browse_job_list(
                client,
                all_jobs,
                title=f"All history ({len(all_jobs)})",
                empty_message="No jobs yet.",
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
            )
            continue

        job = get_job(selected)
        if not job:
            console.print("[red]Job not found.[/red]")
            continue
        _job_action_menu(client, job)
