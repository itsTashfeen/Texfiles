# Technical Findings — MathTex Gemini Automation Session

Discoveries from debugging and verification. Exact numbers preserved from the Nov 14 2026 chat and on-disk reports.

---

## 1. Token inflation = `automatic_continuation` hop summing

In `google-genai` **v3.3.0**, `client.models.generate_content()` has **`automatic_continuation=True` by default**.

When LaTeX output is large (~**36,000–47,000** candidate tokens):
1. Backend splits work across hops (`FinishReason.CONTINUATION` + `continuation_token`).
2. Each hop re-feeds the original prompt **plus all LaTeX generated so far**.
3. Hop inputs grow roughly ~5k → ~20k → ~35k+.
4. `google.genai._extra_utils.merge_pydantic_models()` **sums** fields ending in `_count` → inflated `usage_metadata.prompt_token_count`.
5. True single-turn input is preserved as **`usage_metadata.initial_prompt_token_count`**.

**Reporting convention after fix:**
- **InitIn** = `initial_prompt_token_count` (or preflight `count_tokens`) — matches AI Studio intuition
- **BilledIn** = `prompt_token_count` — cumulative billed input across hops; used for USD cost

---

## 2. AI Studio vs API PDF tokenization (media, not plain text)

- **Both** AI Studio and the Gemini Developer API tokenize PDFs **multimodally** (page images + native text), not as stripped plain text.
- Plain-text extraction (e.g. PyMuPDF text only) would break math notation, matrices, integral limits — **rejected** as architecture.
- Keep `Part.from_bytes(..., mime_type="application/pdf")`.

**Per-page media token rates (Gemini 3 / 4):**

| Level | Tokens / page |
|-------|----------------|
| LOW | 280 |
| MEDIUM | 560 |
| HIGH | 1,120 |

Rough fixed overhead cited in session: System Instructions ~**2,380** tokens; prompt ~**1,875** tokens (order-of-magnitude; actual preflight includes scope guard).

**Config lock:** `PDF_MEDIA_RESOLUTION = "medium"` → `PartMediaResolutionLevel.MEDIA_RESOLUTION_MEDIUM` to avoid implicit HIGH escalation while keeping math OCR crisp.

User AI Studio comparison (Chapter 5-ish): PDF ~**1,651** + prompt ~**1,609** ≈ **3,300** total; API report showed ~**44k** In on first section and ~**70k** on last — explained by continuation hop summing, not “secretly uploading three PDFs in one chat.”

---

## 3. Live billed input from reports (pre-isolation accounting)

### Chapter 5 Homework — `run_20261114_142314.md`

| Section | In (billed) | Think | Out | Cost | Notes |
|---------|-------------|-------|-----|------|-------|
| 5.1 | **45,042** | 5,624 | 36,153 | $0.2370 | 876.6 s |
| 5.2 | **69,572** | 11,401 | 45,673 | $0.3289 | 1257.7 s |
| 5.3 | **73,696** | 17,922 | 47,614 | $0.3737 | TRUNCATED_LATEX; compile failed; 1112.2 s |
| **Total** | | | | **$0.9396** | |

### Chapter 6 — `run_20261114_154131.md` (job “Stats Chapter 6.1-6.3”)

| Section | In (billed) | Think | Out | Cost | Notes |
|---------|-------------|-------|-----|------|-------|
| 6.1 | **44,910** | 3,183 | 36,975 | $0.2289 | compile Failed |
| 6.2 | **45,816** | 6,343 | 38,351 | $0.2521 | Compiled |
| 6.3 | **72,130** | 8,658 | 43,695 | $0.3068 | Compiled |
| **Total** | | | | **$0.7878** | |

Note: User initially attributed `154131` to Chapter 5; that stamp is Chapter 6. Chapter 5 is `142314`.

### Carbon test — `run_20261114_153853.md`

Failed with **`402 RESOURCE_EXHAUSTED`** — prepayment credits depleted.

---

## 4. Post-fix preflight `count_tokens` (v1beta, argon + 3.1-pro)

System + scoped prompt + single PDF, Chapter 5:

| PDF | gemini-4-argon | gemini-3.1-pro-preview |
|-----|----------------|------------------------|
| 5.1 Introduction.pdf | **4,918** | **4,945** |
| 5.2 Bivariate and Multivariate Probability Distributions.pdf | **10,533** | **10,560** |
| 5.3 Marginal and Conditional Probability Distributions.pdf | **11,090** | **11,119** |

Wizard file sizes for same set: 5.1 **57.7 KB**, 5.2 **122.9 KB**, 5.3 **130.3 KB**.

---

## 5. `api_version`: v1 vs v1beta (and media_resolution)

| Observation | Detail |
|-------------|--------|
| Default with `HttpOptions(timeout=900000)` only | `api_version: **v1**` |
| v1 + `gemini-3.1-pro-preview` + `countTokens` | **404** not found / not supported |
| `Part.media_resolution` | Serializes as `mediaResolution` on parts; treated as newer API surface |
| v1alpha client | Also worked for count_tokens on 3.1-pro in tests |
| **Chosen fix** | Force **`api_version="v1beta"`** in `create_client()` — argon, carbon, 3.1-pro, `serviceTier`, `thinkingConfig`, `mediaResolution`, `batches` |

Serialization check: generate_content body parts included `['mediaResolution', 'inlineData']` on both default and v1alpha paths when media_resolution set.

---

## 6. Client concurrency and “one chat vs three chats”

**Design intent:** One isolated generation per PDF (prompt + that PDF only).

**Early behavior:** Separate `generate_content` calls per item, but:
- One shared `genai.Client` (`httpx` pool)
- `ThreadPoolExecutor(max_workers=3)`
- Parallel `automatic_continuation` loops with stateful `continuation_token`

That made failures look like “one chat with three PDFs.”

**After fix:** Fresh client per PDF; sequential default (`MAX_WORKERS=1`); assert exactly one PDF part in user Content; isolation log with sha256 fingerprint.

---

## 7. Section bleed beyond intentional overlap (Wackerly)

**Intentional slicing** (`Overleaf/.code/slice_pdfs.py`): include **one page** of the next section so nothing is cut mid-sentence. **Do not change this.**

**Textbook boundary example:** Book page **235** can contain:
- Top: Exercises **5.15–5.18** (end of Section 5.2)
- Bottom: **Section 5.3** header

A 5.2 PDF that only “contains the first page of 5.3” can still trigger the model to generate **all** of 5.3 exercises from **pretraining memory** if no hard scope boundary is present.

**User confirmation:** Leakage was “well beyond” one overlap page — e.g. full 5.3 from 5.2 PDF — so concurrency/scope, not re-slicing, was the right fix.

---

## 8. Config / API constants used in session

| Constant | Value |
|----------|-------|
| `MAX_OUTPUT_TOKENS` | 65,536 |
| `HTTP_TIMEOUT_MS` | 900,000 (15 min) |
| `INLINE_PDF_MAX_BYTES` | 18 MiB (else `files.upload`) |
| Flex backoff | 15s → 45s → 90s (+ jitter) |
| Batch poll | 30s |
| Default model | `gemini-4-argon` |
| Also available | `gemini-4-carbon`, `gemini-3.1-pro-preview` |
| Gemini 4 | `ThinkingConfig(thinking_level=high\|low)` |
| 3.1-pro | `top_p=0.35` |
| Flex/Batch pricing | 50% of standard list rates in `MODEL_PRICING_PER_1M` |

---

## 9. Intentional non-changes

- **`Overleaf/.code/slice_pdfs.py`** — untouched; 1-page overlap preserved
- **`Overleaf/.code/mirror_pdf_tree.py`** — manual prep only
- System Instruction **content** — user-authored; not generated by automation
- Overleaf cloud sync (`olsync`) — out of scope
- No switch to text-only PDF extraction

---

## 12. Gemini 4 Long Decode unlocks 1,048,576 output tokens

Live `v1beta` checks (Nov 15 2026):
- `gemini-4-argon`, `gemini-4-carbon`, `gemini-4-hydrogen` accept `max_output_tokens=1_048_576`
- `gemini-3.1-pro-preview` stays at listed `out_limit=65536` (also accepts larger requests but model list reports 65536)
- Model list: argon/carbon `out_limit=32768` (list metadata), hydrogen `65536` — Long Decode still works via config for all Gemini 4 IDs tested
- PDF + Flex + System Instruction + ThinkingConfig verified for `gemini-3.1-pro-preview` and `gemini-4-hydrogen`

Thinking + candidate tokens share `max_output_tokens`. Hitting exactly 65,536 with high thinking was the Carbon Book Section truncation pattern.

---

## 13. Multi-fence AI Studio outputs

AI Studio often emits **two** ```latex fences for long docs. Single outer-fence strip left middle fences / prose in `.tex`. `extract_latex_source()` concatenates every closed (and trailing unclosed) fence in order, then trims to `\documentclass`.

---

## 14. Windows Rich width

`Console.legacy_windows=True` subtracts 1 from width; `os.get_terminal_size` for cmd often stays 80 even after maximize if the screen buffer width is not increased. Dedicated `no_wrap` columns + two tables avoid ellipsis regardless.
