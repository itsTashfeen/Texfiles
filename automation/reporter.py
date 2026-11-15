"""Token/cost calculator, Rich terminal summary, and job-named Markdown/JSON reports."""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from rich.console import Console
from rich.table import Table

from .config import MODEL_PRICING_PER_1M, REPORTS_DIR, ensure_runtime_dirs

_FORBIDDEN_WIN_CHARS_RE = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
_RESERVED_WIN_NAMES = frozenset(
    {
        "CON",
        "PRN",
        "AUX",
        "NUL",
        *(f"COM{i}" for i in range(1, 10)),
        *(f"LPT{i}" for i in range(1, 10)),
    }
)


@dataclass
class SectionReport:
    pdf_name: str
    topic: str
    target_tex_path: str
    tier_used: str
    initial_input_tokens: int = 0
    input_tokens: int = 0
    cached_tokens: int = 0
    thinking_tokens: int = 0
    output_tokens: int = 0
    preflight_tokens: int = 0
    estimated_cost_usd: float = 0.0
    latex_validation: str = "N/A"
    compile_status: str = "N/A"
    pdf_output_path: str = ""
    elapsed_seconds: float = 0.0
    error: str = ""
    finish_reason: str = ""
    extras: dict[str, Any] = field(default_factory=dict)


def _fmt_int(n: int) -> str:
    return f"{int(n):,}"


def _short_compile_status(status: str) -> str:
    """Collapse long absolute paths / error dumps for 80-col CMD tables."""
    text = (status or "").strip()
    if not text:
        return "N/A"
    if text.startswith("Compiled ("):
        inner = text[len("Compiled (") :].rstrip(")")
        name = Path(inner).name if inner else ""
        return f"Compiled ({name})" if name else "Compiled"
    if text.startswith("Failed:"):
        detail = text[len("Failed:") :].strip()
        # Keep first meaningful fragment
        first = detail.split(";")[0].strip()
        if len(first) > 48:
            first = first[:45] + "..."
        return f"Failed: {first}" if first else "Failed"
    if len(text) > 56:
        return text[:53] + "..."
    return text


def _section_label(row: SectionReport) -> str:
    stem = Path(row.pdf_name).stem if row.pdf_name else row.topic
    return stem or row.topic or "?"


def sanitize_job_filename(job_name: str | None) -> str:
    """Convert an arbitrary job name into a safe, readable Windows filename stem."""
    if not job_name or not job_name.strip():
        return ""
    cleaned = _FORBIDDEN_WIN_CHARS_RE.sub("-", job_name.strip())
    cleaned = " ".join(cleaned.split()).rstrip(". ")
    if not cleaned:
        return ""
    if cleaned.upper() in _RESERVED_WIN_NAMES:
        cleaned = f"job-{cleaned}"
    return cleaned[:120]


def resolve_report_paths(
    job_name: str | None,
    *,
    reports_dir: Path | None = None,
    stamp: str | None = None,
) -> tuple[Path, Path, str]:
    """
    Return (md_path, json_path, stamp) named after the job.

    If `<Job Name>.md` does not exist yet, writes `<Job Name>.md` and `<Job Name>.json`.
    If it already exists, writes `<Job Name> (YYYYMMDD_HHMMSS).md` and `.json`.
    Falls back to `run_YYYYMMDD_HHMMSS` when no job name is provided.
    """
    ensure_runtime_dirs()
    base_dir = reports_dir or REPORTS_DIR
    base_dir.mkdir(parents=True, exist_ok=True)
    ts = stamp or datetime.now().strftime("%Y%m%d_%H%M%S")
    stem = sanitize_job_filename(job_name)
    if not stem:
        stem = f"run_{ts}"
        return base_dir / f"{stem}.md", base_dir / f"{stem}.json", ts

    md_candidate = base_dir / f"{stem}.md"
    json_candidate = base_dir / f"{stem}.json"
    if md_candidate.exists() or json_candidate.exists():
        stem_with_ts = f"{stem} ({ts})"
        return base_dir / f"{stem_with_ts}.md", base_dir / f"{stem_with_ts}.json", ts
    return md_candidate, json_candidate, ts


def estimate_cost_usd(
    model: str,
    pricing_tier: str,
    *,
    input_tokens: int = 0,
    cached_tokens: int = 0,
    thinking_tokens: int = 0,
    output_tokens: int = 0,
) -> float:
    """
    pricing_tier: 'standard' | 'flex' | 'batch'
    Thinking tokens are billed as output tokens.
    """
    model_rates = MODEL_PRICING_PER_1M.get(model) or MODEL_PRICING_PER_1M["gemini-4-argon"]
    rates = model_rates.get(pricing_tier) or model_rates["standard"]
    billable_input = max(0, input_tokens - cached_tokens)
    cost = (
        billable_input * rates["input"]
        + cached_tokens * rates["cached"]
        + (output_tokens + thinking_tokens) * rates["output"]
    ) / 1_000_000
    return round(cost, 6)


def pricing_tier_for_execution(tier_used: str) -> str:
    if tier_used in {"flex", "flex_batch_fallback", "batch_fallback"}:
        return "flex"
    if tier_used in {"batch", "batch_only"}:
        return "batch"
    return "standard"


def usage_from_response(response: Any, *, preflight_tokens: int = 0) -> dict[str, int]:
    meta = getattr(response, "usage_metadata", None)
    if meta is None:
        return {
            "initial_input_tokens": preflight_tokens,
            "input_tokens": 0,
            "cached_tokens": 0,
            "thinking_tokens": 0,
            "output_tokens": 0,
            "preflight_tokens": preflight_tokens,
        }
    billed_input = int(getattr(meta, "prompt_token_count", 0) or 0)
    raw_initial = getattr(meta, "initial_prompt_token_count", None)
    if raw_initial is not None and int(raw_initial) > 0:
        initial_input = int(raw_initial)
    elif preflight_tokens > 0:
        initial_input = preflight_tokens
    else:
        initial_input = billed_input

    return {
        "initial_input_tokens": initial_input,
        "input_tokens": billed_input,
        "cached_tokens": int(getattr(meta, "cached_content_token_count", 0) or 0),
        "thinking_tokens": int(getattr(meta, "thoughts_token_count", 0) or 0),
        "output_tokens": int(getattr(meta, "candidates_token_count", 0) or 0),
        "preflight_tokens": preflight_tokens,
    }


def print_summary_table(rows: list[SectionReport], *, console: Console | None = None) -> None:
    """
    Two compact tables that stay readable in 80-column Windows cmd.exe.

    Absolute .tex paths and slash-joined token blobs are never packed into one
    ellipsis column — each metric gets its own no_wrap numeric column.
    """
    console = console or Console()

    exec_table = Table(title="MathTex Gemini Run - Execution & Compile", show_lines=True)
    exec_table.add_column("Section", overflow="fold")
    exec_table.add_column("Tier", no_wrap=True)
    exec_table.add_column("Finish", no_wrap=True)
    exec_table.add_column("LaTeX", no_wrap=True)
    exec_table.add_column("Compile", overflow="fold")
    exec_table.add_column("Sec", justify="right", no_wrap=True)

    token_table = Table(title="MathTex Gemini Run - Tokens & Cost", show_lines=True)
    token_table.add_column("Section", overflow="fold")
    token_table.add_column("InitIn", justify="right", no_wrap=True)
    token_table.add_column("BilledIn", justify="right", no_wrap=True)
    token_table.add_column("Cache", justify="right", no_wrap=True)
    token_table.add_column("Think", justify="right", no_wrap=True)
    token_table.add_column("Out", justify="right", no_wrap=True)
    token_table.add_column("Cost", justify="right", no_wrap=True)

    total_init = total_billed = total_cache = total_think = total_out = 0
    total_cost = 0.0

    for row in rows:
        init_in = row.initial_input_tokens or row.preflight_tokens or row.input_tokens
        label = _section_label(row)
        finish = (row.finish_reason or "").replace("FinishReason.", "") or "-"
        exec_table.add_row(
            label,
            row.tier_used,
            finish,
            row.latex_validation,
            _short_compile_status(row.compile_status),
            f"{row.elapsed_seconds:.1f}",
        )
        token_table.add_row(
            label,
            _fmt_int(init_in),
            _fmt_int(row.input_tokens),
            _fmt_int(row.cached_tokens),
            _fmt_int(row.thinking_tokens),
            _fmt_int(row.output_tokens),
            f"${row.estimated_cost_usd:.4f}",
        )
        total_init += init_in
        total_billed += row.input_tokens
        total_cache += row.cached_tokens
        total_think += row.thinking_tokens
        total_out += row.output_tokens
        total_cost += row.estimated_cost_usd

    if rows:
        token_table.add_row(
            "[bold]TOTAL[/bold]",
            f"[bold]{_fmt_int(total_init)}[/bold]",
            f"[bold]{_fmt_int(total_billed)}[/bold]",
            f"[bold]{_fmt_int(total_cache)}[/bold]",
            f"[bold]{_fmt_int(total_think)}[/bold]",
            f"[bold]{_fmt_int(total_out)}[/bold]",
            f"[bold]${total_cost:.4f}[/bold]",
        )

    console.print(exec_table)
    console.print(token_table)
    console.print(
        "[dim]Note: InitIn = single-turn prompt+PDF input (matches AI Studio); "
        "BilledIn = cumulative input across multi-hop continuations.[/dim]"
    )
    console.print(f"[bold]Total estimated cost:[/bold] ${total_cost:.4f}")


def write_reports(
    rows: list[SectionReport],
    *,
    model: str,
    tier: str,
    job_name: str | None = None,
    job_id: str | None = None,
) -> tuple[Path, Path]:
    md_path, json_path, stamp = resolve_report_paths(job_name)

    total_cost = sum(r.estimated_cost_usd for r in rows)
    title_label = job_name.strip() if job_name and job_name.strip() else f"Run {stamp}"
    lines = [
        f"# MathTex Gemini Report — {title_label}",
        "",
    ]
    if job_name:
        lines.append(f"- Job Name: `{job_name}`")
    if job_id:
        lines.append(f"- Job ID: `{job_id}`")
    lines.extend(
        [
            f"- Timestamp: `{stamp}`",
            f"- Model: `{model}`",
            f"- Execution tier: `{tier}`",
            f"- Sections: {len(rows)}",
            f"- Total estimated cost: ${total_cost:.4f}",
            "",
            "> **Token Columns:** `InitIn` is the isolated single-turn input size (System + Prompt + single PDF, matching AI Studio). `BilledIn` is cumulative `prompt_token_count` across SDK `automatic_continuation` hops when long LaTeX outputs span multiple continuation turns. `Finish` is the API `finish_reason` (`STOP`, `MAX_TOKENS`, etc.).",
            "",
            "| PDF | Topic | Target TeX | Tier | Finish | InitIn | BilledIn | Cache | Think | Out | Cost | LaTeX | Compile | Sec |",
            "|---|---|---|---|---|---:|---:|---:|---:|---:|---:|---|---|---:|",
        ]
    )
    for r in rows:
        init_in = r.initial_input_tokens or r.preflight_tokens or r.input_tokens
        finish = (r.finish_reason or "").replace("FinishReason.", "") or "-"
        lines.append(
            f"| {r.pdf_name} | {r.topic} | `{r.target_tex_path}` | {r.tier_used} | {finish} | "
            f"{init_in} | {r.input_tokens} | {r.cached_tokens} | {r.thinking_tokens} | {r.output_tokens} | "
            f"{r.estimated_cost_usd:.4f} | {r.latex_validation} | {r.compile_status} | {r.elapsed_seconds:.1f} |"
        )
        if r.error:
            lines.append(f"| | | | | | | | | | | | ERROR | {r.error} | |")

    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    payload = {
        "job_name": job_name,
        "job_id": job_id,
        "stamp": stamp,
        "model": model,
        "tier": tier,
        "total_estimated_cost_usd": total_cost,
        "sections": [asdict(r) for r in rows],
    }
    json_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return md_path, json_path
