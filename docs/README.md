# MathTex Gemini Automation — Docs Archive

Archive of **everything** from the Nov 14 2026 build session: bugs, fixes, changelogs, AI rules, architecture, plans, findings, verification numbers, and roadmap. Nothing from that chat is intentionally omitted.

**Project:** End-to-end CLI that turns `Overleaf/.pdf/.../Book PDF/*.pdf` into overwritten `Overleaf/.tex/.../<TargetSubfolder>/(Prefix) <stem>.tex`, compiles mirrored PDFs via `watch_tex_to_pdf.py`, and reports tokens / cost / compile status.

## Launch

From `MathTex/`:

| Launcher | Purpose |
|----------|---------|
| `Run Automation.bat` / `python run_automation.py` | Interactive wizard: select PDFs, prompts, system instructions, model, tier; name job; run |
| `Run Jobs.bat` / `python run_jobs.py` | Inspect / cancel / refresh named jobs; download Batch results |
| `python -m automation.main --dry-run ...` | Map PDFs → `.tex` without calling Gemini |
| `python -m automation.main --jobs` | Same as Run Jobs |
| `python -m automation.main --batches` | Legacy Gemini Batch ID manager |

Setup: `pip install -r requirements-automation.txt`, put `GEMINI_API_KEY` in `MathTex/.env` (not only `.env.example`).

## Index

| Doc | Contents |
|-----|----------|
| [CHANGELOG.md](CHANGELOG.md) | Phases A–E: what shipped and which files changed |
| [BUGS_AND_FIXES.md](BUGS_AND_FIXES.md) | Every bug: symptom → root cause → fix |
| [FINDINGS.md](FINDINGS.md) | Token inflation, PDF media rates, concurrency leakage, API versions, boundary bleed |
| [AI_RULES.md](AI_RULES.md) | Scope guard text, isolation rules, prompt assembly, do-not-touch list |
| [ARCHITECTURE.md](ARCHITECTURE.md) | Modules, path/prefix rules, tiers, state files, flow diagram |
| [ROADMAP.md](ROADMAP.md) | Done / open / out of scope |
| [VERIFICATION.md](VERIFICATION.md) | Dry-runs, preflight counts, live-run report numbers |
| [SESSION_HISTORY.md](SESSION_HISTORY.md) | Chronological user requests from the chat |
| [specs/Gemini_Automation.md](specs/Gemini_Automation.md) | Original product roadmap attachment |
| [specs/Detailed_Module_Specs.md](specs/Detailed_Module_Specs.md) | Original detailed module specs attachment |
| [plans/01-gemini-overleaf-automation.md](plans/01-gemini-overleaf-automation.md) | Initial build plan (Cursor) |
| [plans/02-isolate-jobs-token-reports.md](plans/02-isolate-jobs-token-reports.md) | Isolation / tokens / scope guard plan (Cursor) |

## Session source

- Transcript: `agent-transcripts/328ab998-b4cd-418a-9bba-504ca3488585`
- Date covered: Saturday Nov 14, 2026
