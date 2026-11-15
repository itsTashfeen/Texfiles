# Changelog — MathTex Gemini Automation (Nov 14 2026 Session)

Chronological record of what shipped in this chat. Files are under `MathTex/` unless noted.

---

## Phase A — Initial automation package

**Goal:** End-to-end CLI matching `Gemini_Automation.md` / Detailed Module Specs.

**Created:**
- `requirements-automation.txt` — `google-genai>=1.10.0`, `questionary`, `rich`, `python-dotenv`
- `automation/__init__.py` (v0.1.0), `__main__.py`
- `automation/config.py` — roots, prefix map, models, pricing, `MAX_WORKERS=3`, timeout 900_000 ms
- `automation/path_mapper.py` — RelPath, topic derivation, tex target resolve
- `automation/ui_selector.py` — Tkinter + Questionary interactive selection
- `automation/gemini_runner.py` — Flex / Batch / Standard, retries, batch persist
- `automation/latex_processor.py` — fence strip, validation labels
- `automation/pdf_compiler_hook.py` — `watch_tex_to_pdf.py --file`
- `automation/reporter.py` — Rich table + `reports/run_YYYYMMDD_HHMMSS.md|.json`
- `automation/main.py` — CLI (`--dry-run`, `--batches`, non-interactive flags)
- `automation/.state/batch_jobs.json`, `automation/reports/.gitkeep`
- `Overleaf/System Instructions/.gitkeep`
- `.env.example`, `.gitignore` entries for `.env`, `.state/`, `reports/`

**Fixes during Phase A:**
- `latex_processor.py`: add missing `def` on `@property validation_label`
- `ui_selector.py`: fix typo `system related_path if False else system_path` → `system_path`
- Re-run dry-run from `MathTex/` cwd after `ModuleNotFoundError: automation`

**Verified:** Chapter 6 dry-run — `6.3 The Method of Distribution Functions.pdf` → `(Homework) 6.3 The Method of Distribution Functions.tex`, topic `The Method of Distribution Functions`.

---

## Phase B — One-click launcher + system instructions

**User ask:** One script to hit run and choose everything; system instructions added.

**Created / updated:**
- `run_automation.py` — thin launcher into `automation.main`
- `Run Automation.bat` — double-click entry on Windows
- Detection of `Overleaf/System Instructions/Latex System Instructions.txt`

---

## Phase C — API key + selected-PDF showcase

**User ask:** `GEMINI_API_KEY not set` despite setting key; showcase selected PDFs after picker.

**Fixes / features:**
- Key was only in `.env.example`; app loads `MathTex/.env`
- Copy key from `.env.example` → `.env` when misplaced; reset example to placeholder
- `_load_api_key()` auto-detection path in `main.py`
- `ui_selector.py` — Rich table after PDF selection: `#`, file name, relative path, size

**Example sizes shown:** 5.1 = 57.7 KB, 5.2 = 122.9 KB, 5.3 = 130.3 KB (Chapter 5 wizard).

---

## Phase D — Named jobs + Jobs manager

**User ask:** Confirm “Job submitted”; name job before submit; second bat/py to inspect / cancel / see full settings.

**Created / updated:**
- `automation/config.py` — `JOBS_PATH = .state/jobs.json`
- `automation/job_store.py` — `create_named_job`, `ask_job_name_and_confirm`, statuses, `print_job_settings`
- `automation/jobs_manager.py` — list / inspect / cancel / wait Batch / refresh
- `run_jobs.py`, `Run Jobs.bat`
- `main.py` — `--jobs`, named-job confirmation panel, report paths on job record
- `gemini_runner.py` — link Gemini Batch IDs to local job via `attach_batch_name`

**Statuses:** `submitted`, `running`, `succeeded`, `failed`, `cancelled`, `partial`

---

## Phase E — Isolation, scope guard, tokens, job-named reports

**User ask / plan:** Isolate per-PDF requests; fix continuation token reporting; section scope guard; name reports after job. Do **not** change `slice_pdfs.py`.

**`config.py`:**
- `MAX_WORKERS = 1` (was 3)
- `PDF_MEDIA_RESOLUTION = "medium"`

**`path_mapper.py`:**
- `extract_section_number()` (e.g. `5.2`, `5.10`)
- `MappedItem.section_number`

**`gemini_runner.py`:**
- Fresh `genai.Client` per PDF / attempt; close quietly after
- `create_client(..., api_version="v1beta")`
- `_pdf_part()` with `MEDIA_RESOLUTION_MEDIUM`
- `build_section_scope_guard` / `build_scoped_prompt`
- `build_isolated_user_content` (assert exactly one PDF part)
- Preflight `_preflight_count_tokens`
- Isolation log: `[i/N] Isolated chat → … (pages, KB, sha256, media, preflight)`
- Sequential path when `MAX_WORKERS <= 1`
- `run_items(..., api_key=...)` for per-request clients

**`reporter.py`:**
- `initial_input_tokens`, `preflight_tokens` on `SectionReport`
- `usage_from_response` prefers `initial_prompt_token_count`
- Summary columns: InitIn / BilledIn / Cache / Think / Out
- `sanitize_job_filename`, `resolve_report_paths` → `<Job Name>.md|.json` (timestamp on collision)
- `write_reports(..., job_name=, job_id=)`

**`job_store.py` / `main.py` / `jobs_manager.py`:**
- `summarize_token_diagnostics`
- Persist `token_diagnostics` on jobs; show in job settings panel
- Pass job name/id into reports from interactive, non-interactive, and Batch download paths

**Verified:** Ch.5 dry-run sections `5.1`/`5.2`/`5.3`; preflight argon 4,918 / 10,533 / 11,090; `slice_pdfs.py` untouched; lints clean.
## Phase F — Long Decode, TRUNCATED_LATEX, CMD tables, Jobs views, Hydrogen (Nov 15 2026)

**User ask:** Fix push disconnect; CMD token column ellipsis; jobs list shows only current + history filters; eliminate TRUNCATED_LATEX; add gemini-4-hydrogen; ensure 3.1-pro-preview works.

**`config.py`:**
- `LONG_DECODE_MAX_OUTPUT_TOKENS = 1_048_576`
- `MODEL_MAX_OUTPUT_TOKENS` — Gemini 4 → 1M; `gemini-3.1-pro-preview` → 65_536
- `HTTP_TIMEOUT_MS = 1_800_000` (30 min)
- `MAX_LATEX_CONTINUATION_TURNS = 2`
- `AVAILABLE_MODELS` adds `gemini-4-hydrogen`
- `GEMINI4_MODELS` includes hydrogen
- Hydrogen pricing card + `max_output_tokens_for_model()`

**`latex_processor.py`:**
- `extract_latex_source()` stitches all fenced ```latex / ```tex blocks (AI Studio multi-block)
- Tracks `codeblock_count` on `LatexProcessResult`

**`gemini_runner.py`:**
- `automatic_continuation=True` + per-model Long Decode `max_output_tokens`
- `ThinkingConfig` for Gemini 4 **and** `gemini-3.1-pro-preview`
- `extract_response_text_and_meta()` joins non-thought parts + `finish_reason`
- Tail-resume fallback (up to 2 turns) when `\end{document}` missing
- `success` requires LaTeX `OK` **and** compile success (truncated runs no longer marked succeeded)
- Batch configs omit `automatic_continuation`

**`reporter.py`:**
- Two 80-col-safe tables: Execution & Compile + Tokens & Cost
- Dedicated `InitIn` / `BilledIn` / `Cache` / `Think` / `Out` / `Cost` columns (`no_wrap`)
- `finish_reason` on `SectionReport` + Markdown reports

**`job_store.py` / `jobs_manager.py`:**
- Default view = **Current** (`submitted`/`running`) only
- Menu: Succeeded History, Failed History, All History, History by Model, Refresh, Done
- `effective_job_status()` reclassifies historical TRUNCATED_LATEX as failed/partial

**Git push:** Unpushed 4.33 GB rewritten into ≤350 MB lossless chunk commits and pushed sequentially to `origin/main`.
