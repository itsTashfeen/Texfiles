# Session History — Chronological User Requests

Transcript: `328ab998-b4cd-418a-9bba-504ca3488585` (Saturday Nov 14, 2026, UTC-5). Attachments: `Gemini_Automation.md`, `Detailed_Module_SPecs.txt`.

---

## 1. ~1:32 PM — Plan the automation

**Ask:** Plan against `MathTex/Overleaf` and `MathTex/Overleaf/.code` using the uploaded Gemini Automation roadmap and Detailed Module Specs.

**Outcome:** Cursor plan **Gemini Overleaf Automation** (`gemini_overleaf_automation_0329e277`) — new `automation/` package, Flex+Batch, compile hook, reports. Out of scope: changing slice/mirror scripts, shipping system instructions, olsync.

---

## 2. ~1:37 PM — Implement the plan

**Ask:** Implement the MathTex Gemini Automation plan as specified; do **not** edit the plan file; use existing todos; complete all.

**Outcome:** Phase A package created; dry-run Ch.6 mapping verified; property/typo fixes during build.

---

## 3. ~1:41 PM — Brief task result

**Ask:** System handoff — briefly inform user of task result.

**Outcome:** Summary of created modules and usage commands.

---

## 4. ~1:45 PM — One-click run + system instructions

**Ask:** One script to hit run and choose everything; user also added system instructions.

**Outcome:** Phase B — `Run Automation.bat` / `run_automation.py`; system instruction folder populated with `Latex System Instructions.txt`.

---

## 5. ~1:56 PM — API key + PDF showcase

**Ask:** Still seeing `GEMINI_API_KEY not set` even though key was set. After selecting source PDFs, showcase the selected files.

**Outcome:** Phase C — key recovered from `.env.example` into `.env`; auto-copy helper; Rich table of selected PDFs (name, relative path, size).

---

## 6. ~2:05 PM — Named jobs + Jobs bat

**Ask:** Happy with PDF table and “Running 3 section(s)…”. Want confirmation that job was submitted; name the job before submit; another bat/py to check current/old jobs, cancel them, and see full settings like the wizard.

**Outcome:** Phase D — `job_store.py`, `jobs_manager.py`, `Run Jobs.bat` / `run_jobs.py`, job name + confirm panel, “Job submitted” confirmation.

---

## 7. ~4:10 PM — Leakage + token shock + job-named reports

**Ask:**
- Are 3 PDFs + 1 prompt one chat or one chat per PDF? Suspected one chat — model referenced other PDFs / continued into next sections.
- Report input ~**44k** (and last ~**70k**) vs AI Studio ~**3.3k** (PDF ~1651 + prompt ~1609); asked what was missing.
- Reports `.md` / `.json` should be named after the **job**, not raw timestamps alone.
- Cited `run_20261114_154131.md` (later clarified as Ch.6, not the Ch.5 job).

**Outcome:** Investigation started; diagnosis path toward continuation hops + concurrency; plan update requested next.

---

## 8. ~4:19 PM — Correct bleed diagnosis; update plan

**Ask / clarifications:**
- PDF page bleed on 6.1 (pages include start of 6.2) is **intentional** from slicing.
- Real smoking gun: from **5.2** PDF that only contains the first page of 5.3, the `.tex` contained **all of 5.3 questions**.
- Suspect concurrency cross-talk / merged requests for leakage and token blow-up.
- Asks whether AI Studio treats PDF as extracted text vs API as media; what is the correct approach.
- **Do not** change `slice_pdfs.py` — keep one-page overlap.
- **Update the plan.**

**Outcome:** Plan revised to **Isolate Per-PDF Requests, Fix Continuation Token Reporting & Scope Guard, Name Reports by Job** (`isolate_jobs_token_reports_7f65ac8b`). Explicit out of scope: re-slicing.

---

## 9. ~4:35 PM — Implement isolation plan

**Ask:** Implement the isolation / tokens / scope / job-named reports plan; do not edit the plan file; complete all todos.

**Outcome:** Phase E — `MAX_WORKERS=1`, fresh Client, scope guard, `media_resolution=MEDIUM`, InitIn/BilledIn, preflight count_tokens, `api_version=v1beta`, job-named reports, token_diagnostics. Verified Ch.5 dry-run + preflight counts; `slice_pdfs.py` untouched.

---

## 10. ~4:47 PM — Docs archive

**Ask:** Collect all bugs, changelogs, AI rules, roadmap, and everything for this whole project from all of this chat — do not omit any finding, plan, bug, or fix — and create a `docs` folder with them as `.md`.

**Outcome:** This `MathTex/docs/` archive (README, CHANGELOG, BUGS_AND_FIXES, FINDINGS, AI_RULES, ARCHITECTURE, ROADMAP, VERIFICATION, SESSION_HISTORY, specs/, plans/).

---

## Plans referenced

1. [plans/01-gemini-overleaf-automation.md](plans/01-gemini-overleaf-automation.md)
2. [plans/02-isolate-jobs-token-reports.md](plans/02-isolate-jobs-token-reports.md)

## Specs referenced

1. [specs/Gemini_Automation.md](specs/Gemini_Automation.md)
2. [specs/Detailed_Module_Specs.md](specs/Detailed_Module_Specs.md)
