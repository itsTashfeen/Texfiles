# Bugs and Fixes — MathTex Gemini Automation Session

Every bug found in the Nov 14 2026 chat, with symptom, root cause, fix, and files. Includes live-run failures and corrected misdiagnoses.

---

## 1. `ModuleNotFoundError: No module named 'automation'`

| | |
|--|--|
| **Symptom** | First verify / dry-run failed when run from parent directory |
| **Root cause** | Package must be imported with cwd = `MathTex/` (or `python -m automation.main` from that root) |
| **Fix** | Re-run from `MathTex/`; install `requirements-automation.txt` there |
| **Files** | N/A (invocation) |

---

## 2. SyntaxError: `@property` missing `def`

| | |
|--|--|
| **Symptom** | `latex_processor.py` / `pdf_compiler_hook.py` invalid property definitions |
| **Root cause** | Wrote `@property` then bare name without `def` (e.g. `validation_label(self) -> str:`) |
| **Fix** | `@property` + `def validation_label(self) -> str:` (and `status_label`) |
| **Files** | `automation/latex_processor.py`, `automation/pdf_compiler_hook.py` |

---

## 3. Typo in `ui_selector` system instruction path

| | |
|--|--|
| **Symptom** | Broken assignment / NameError risk |
| **Root cause** | `system_instruction_path=system related_path if False else system_path` |
| **Fix** | `system_instruction_path=system_path` |
| **Files** | `automation/ui_selector.py` |

---

## 4. `GEMINI_API_KEY not set` despite user setting the key

| | |
|--|--|
| **Symptom** | Wizard completed then: `GEMINI_API_KEY not set. Copy .env.example to .env and add your key.` |
| **Root cause** | Key written only into `.env.example`; loader used `load_dotenv(MATHTEX_ROOT / ".env")` |
| **Fix** | Copy key from `.env.example` → `.env`; reset example to placeholder; auto-detect in `_load_api_key()` |
| **Files** | `MathTex/.env`, `.env.example`, `automation/main.py` |

---

## 5. Cross-section / cross-PDF “leakage”

| | |
|--|--|
| **Symptom** | Job with 5.1 / 5.2 / 5.3 (or 6.x) produced `.tex` that referenced other sections; **5.2 PDF (only first page of 5.3) still generated all of 5.3 questions**; felt like one chat with three PDFs |
| **Root cause (composite)** | (1) Shared `genai.Client` + `ThreadPoolExecutor(max_workers=3)` while `automatic_continuation` ran parallel multi-hop loops; (2) intentional 1-page boundary overlap + textbook (Wackerly) in pretraining — adjacent section header without a hard scope boundary → model continued from memory |
| **Misdiagnosis** | Agent first blamed page bleed alone (6.1 quoting start of 6.2). User confirmed bleed is intentional; real failure was full adjacent-section generation |
| **Fix** | `MAX_WORKERS=1`; fresh `genai.Client` per PDF; explicit single-PDF `types.Content`; **STRICT SECTION SCOPE BOUNDARY** prompt header |
| **Files** | `automation/config.py`, `automation/gemini_runner.py`, `automation/path_mapper.py` |
| **Intentional non-fix** | Do **not** change `Overleaf/.code/slice_pdfs.py` (keep 1-page overlap) |

---

## 6. Inflated input tokens (44k–73k vs AI Studio ~3k–11k)

| | |
|--|--|
| **Symptom** | Reports showed In ≈ 44,910–73,696; AI Studio showed ~3.3k–8k for same-ish payload |
| **Root cause** | `google-genai` v3.3.0 `automatic_continuation=True` by default. Long LaTeX (36k–47k out) → multiple hops. SDK **sums** `prompt_token_count` across hops in `merge_pydantic_models()`; true first-turn size is `initial_prompt_token_count` |
| **Wrong report citation** | User pointed at `run_20261114_154131.md` as “first PDF of 5.x”; that run is **Chapter 6**. Chapter 5 job is `run_20261114_142314.md` (5.1 In = 45,042) |
| **Fix** | Report **InitIn** (`initial_prompt_token_count` or preflight) and **BilledIn** (`prompt_token_count`); cost from billed; preflight `count_tokens`; lock `media_resolution=MEDIUM` |
| **Files** | `automation/reporter.py`, `automation/gemini_runner.py`, `automation/config.py` |

---

## 7. Preflight `count_tokens` returned 0 / 404 on v1

| | |
|--|--|
| **Symptom** | Verification printed `preflight=0 tokens`; then explicit call failed |
| **Error quote** | `404 NOT_FOUND. {'error': {'code': 404, 'message': 'models/gemini-3.1-pro-preview is not found for API version v1, or is not supported for countTokens...'}}` |
| **Root cause** | `HttpOptions(timeout=...)` alone defaulted `api_version` to **`v1`**. `gemini-3.1-pro-preview` / full `countTokens` + media fields need **`v1beta`** |
| **Fix** | `create_client`: `HttpOptions(timeout=HTTP_TIMEOUT_MS, api_version="v1beta")` |
| **Files** | `automation/gemini_runner.py` |

---

## 8. Verification glob footgun

| | |
|--|--|
| **Symptom** | `5.[123]*.pdf` matched 6 files including `5.10`, `5.11`, `5.12` |
| **Root cause** | Character class + `*` expands incorrectly for multi-digit sections |
| **Fix** | Name exact paths (`5.1 Introduction.pdf`, etc.) in verification scripts; `extract_section_number` correctly returns `5.10` |
| **Files** | Verification only (no product bug) |

---

## 9. `ImportError: cannot import name 'outcome_to_report' from 'automation.reporter'`

| | |
|--|--|
| **Symptom** | `jobs_manager` import failure |
| **Root cause** | `outcome_to_report` lives in `gemini_runner.py`, not `reporter.py` |
| **Fix** | Import from `automation.gemini_runner` |
| **Files** | `automation/jobs_manager.py` |

---

## 10. Unbound variable `job` in `main.py`

| | |
|--|--|
| **Symptom** | Reference error on `job['name']` when named job not required |
| **Root cause** | `job` only defined inside `if require_named_job:` |
| **Fix** | `job_name: str | None = None`; set from `job["name"]` when present |
| **Files** | `automation/main.py` |

---

## 11. Live-run: Chapter 5.3 truncated LaTeX

| | |
|--|--|
| **Report** | `automation/reports/run_20261114_142314.md` |
| **Symptom** | 5.3: `TRUNCATED_LATEX`, compile failed; In 73,696; Think 17,922; Out 47,614; ~1112 s |
| **Cause** | Output hit continuation / max-output limits; `\end{document}` missing after fence strip |
| **Status** | Recorded; truncation handling still open on roadmap |

---

## 12. Live-run: Chapter 6.1 compile failed

| | |
|--|--|
| **Report** | `automation/reports/run_20261114_154131.md` (job “Stats Chapter 6.1-6.3”) |
| **Symptom** | 6.1 LaTeX validation OK-ish path but compile **Failed**; In 44,910; Out 36,975 |
| **Status** | Recorded as compile-hook / content issue for that run |

---

## 13. Live-run: Carbon `402 RESOURCE_EXHAUSTED`

| | |
|--|--|
| **Report** | `automation/reports/run_20261114_153853.md` |
| **Error quote** | `402` / `RESOURCE_EXHAUSTED` — `Your prepayment credits are depleted. Please go to AI Studio at https://ai.studio/projects...` |
| **Fix behavior** | Treat 402 / prepayment as non-retryable (`_is_retryable` returns False) |
| **Files** | `automation/gemini_runner.py` |

---

## 14. Reports named by timestamp only

| | |
|--|--|
| **Symptom** | Hard to match reports to named jobs (`run_YYYYMMDD_HHMMSS.md`) |
| **Fix** | `sanitize_job_filename` + `resolve_report_paths` → `<Job Name>.md` / `.json`; collision → `<Job Name> (YYYYMMDD_HHMMSS).*` |
| **Files** | `automation/reporter.py`, `main.py`, `jobs_manager.py` |

---

## Summary table

| # | Bug | Fixed? |
|---|-----|--------|
| 1 | Wrong cwd / ModuleNotFoundError | Yes (process) |
| 2 | `@property` missing `def` | Yes |
| 3 | ui_selector typo | Yes |
| 4 | Key only in `.env.example` | Yes |
| 5 | Cross-section leakage | Yes (isolation + scope; no slice change) |
| 6 | Inflated In tokens | Yes (InitIn/BilledIn + preflight) |
| 7 | count_tokens on api_version v1 | Yes (`v1beta`) |
| 8 | Glob 5.[123]* | Verification only |
| 9 | outcome_to_report import | Yes |
| 10 | Unbound `job` | Yes |
| 11 | 5.3 TRUNCATED_LATEX | Open / recorded |
| 12 | 6.1 compile fail | Open / recorded |
| 13 | Carbon 402 credits | Non-retry; billing |
| 14 | Timestamp-only report names | Yes |

---

## 12. TRUNCATED_LATEX = 65_536 shared thinking+output ceiling (not missing parts)

| | |
|--|--|
| **Symptom** | Large Carbon/Argon outputs stop mid-equation; `.tex` missing `\end{document}`; pdflatex `File ended while scanning use of \frac` |
| **Evidence** | Carbon Book Section 7.2: Think 44,549 + Out 20,987 = **65,536 exact**; 7.3: 34,917 + 30,619 = **65,536** |
| **Root cause** | `MAX_OUTPUT_TOKENS = 65_536` hardcoded; Gemini 4 thinking tokens count against the same cap; SDK stops with `FinishReason.MAX_TOKENS` instead of continuing |
| **Not the cause** | `response.text` already concatenates all non-thought parts across automatic_continuation hops |
| **Fix** | Gemini 4 Long Decode `max_output_tokens=1_048_576`; multi-codeblock stitcher; up to 2 tail-resume turns; mark truncated/compile-fail as not succeeded |
| **Files** | `automation/config.py`, `gemini_runner.py`, `latex_processor.py` |

---

## 13. CMD Rich table truncates InitIn/BilledIn/… with `…`

| | |
|--|--|
| **Symptom** | Token metrics show `15216/6…`; maximizing window does not help |
| **Root cause** | Windows `cmd.exe` + Rich `legacy_windows=True` often locks width ~80; one slash-joined Tokens column + absolute paths force `overflow=ellipsis` |
| **Fix** | Two tables; dedicated `no_wrap` numeric columns for InitIn, BilledIn, Cache, Think, Out, Cost; short compile labels |
| **Files** | `automation/reporter.py` |

---

## 14. Jobs manager showed cumulative history only

| | |
|--|--|
| **Symptom** | `Run Jobs.bat` listed every past job with no current/history split |
| **Fix** | Default = current only; Succeeded / Failed / All / By Model history subviews |
| **Files** | `automation/jobs_manager.py`, `job_store.py` |

---

## 15. GitHub push `The remote disconnected` / HTTP 500

| | |
|--|--|
| **Symptom** | `git push` to `Texfiles` disconnects |
| **Root cause** | `origin/main..HEAD` ≈ **4.33 GB** (Kids PDFs 4.08 GB) exceeds GitHub ~2 GB single-push pack limit; largest file 93.1 MB (under 100 MB/file) |
| **Fix** | Rewrite unpushed history into ≤350 MB lossless chunks; push each chunk sequentially |
| **Files** | Git history only (working tree unchanged) |
