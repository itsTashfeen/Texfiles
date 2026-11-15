4. Detailed Module Specifications
Phase 1: Dependencies & Environment Setup
Python Libraries (requirements.txt):

google-genai>=1.10.0 (official SDK supporting service_tier="flex", inline PDF Part.from_bytes, and client.batches)

questionary (keyboard arrow-key navigation & Spacebar multi-select checkboxes)

rich (live progress bars, status spinners, and formatted summary tables)

python-dotenv (loads GEMINI_API_KEY from .env)

tkinter (built into standard Windows Python for native mouse file/folder dialogs)

Phase 2: Hybrid Mouse & Keyboard Selection (ui_selector.py)
Input Mode Prompt:

[Mouse Dialog] Pick specific PDF file(s) -> opens Windows filedialog.askopenfilenames rooted at Overleaf\.pdf (supports Ctrl+Click / Shift+Click multi-select).

[Mouse Dialog] Pick entire Book PDF folder -> opens Windows filedialog.askdirectory rooted at Overleaf\.pdf, automatically queueing all .pdf files in that directory.

[Keyboard TUI] Browse Chapters & Checkboxes -> hierarchical folder picker followed by multi-select checkbox list with [Select All PDFs in Chapter] at the top.

Prompt Selection (Multi-Select):

Lists all .txt files in Overleaf\Prompts\.

Allows selecting 1 or multiple prompts (e.g., Math - Topics - Proof and Probability.txt + Strategic Problem Selection Prompt.txt).

When multiple prompts are chosen, joins them in selection order under clear task headers (--- PRIMARY INSTRUCTIONS ---, --- ADDITIONAL INSTRUCTIONS ---).

System Instruction Selection:

Lists all .txt/.md files in Overleaf\System Instructions\ (plus a None option).

Target Subfolder Selection:

Auto-detects existing subfolders under Overleaf\.tex\<RelPath>\ (e.g., Homework, Problem Sets, Book Section) + option to create a new subfolder.

Model & Tier Configuration:

Models: gemini-4-argon (default), gemini-4-carbon, gemini-3.1-pro-preview.

Thinking Level: high (default for proof/abstract math) or low (faster/cheaper for routine calculus).

Execution Tier:

Flex + Auto Batch Fallback (Recommended)

Flex Only

Batch Only

Standard (Real-Time)

Phase 3: Gemini API Engine (gemini_runner.py)
PDF Payload Handling:

Since chapter section PDFs are typically 60 KB – 2 MB (well under the 20 MB inline payload limit), attach each PDF directly via types.Part.from_bytes(data=pdf_bytes, mime_type="application/pdf") to eliminate File API upload/deletion round-trips. Automatically fall back to client.files.upload() if a file exceeds 18 MB.

Generation Config:

Set max_output_tokens=65536 so thinking tokens never truncate \end{document}.

Set thinking_config=types.ThinkingConfig(thinking_level=selected_level) for Gemini 4 models (or top_p=0.35 when gemini-3.1-pro-preview is selected).

Set client HTTP timeout to 900000 ms (15 minutes) to accommodate Flex queue latency.

Flex Execution + Automatic Batch Fallback:

Execute selected PDFs concurrently via asyncio / ThreadPoolExecutor (max_workers=3).

Retry transient 429 / 503 errors up to 3 times with jittered exponential backoff (15s -> 45s -> 90s).

Fallback Trigger: If any PDF still fails due to 503 capacity exhaustion, 429 quota, or timeout—and mode is Flex + Auto Batch Fallback—collect all uncompleted items into a single inline client.batches.create(model=..., src=inlined_requests) call.

Batch Lifecycle, Persistence & Cancellation (--batches):

Save every created Batch job to automation/.state/batch_jobs.json with {job_name, created_at, model, items: [{pdf_path, target_tex_path, topic}]}.

Prompt user immediately after Batch submission:

[W] Wait & poll live (polls every 30s; auto-writes .tex and compiles PDFs upon JOB_STATE_SUCCEEDED).

[C] Cancel batch now (calls client.batches.cancel(name=job_name)).

[E] Exit & check later (re-running python main.py --batches lets you inspect status, cancel any JOB_STATE_PENDING / JOB_STATE_RUNNING job, or download completed results).

Phase 4: LaTeX Cleaning & Safe Write (latex_processor.py)
Extract raw LaTeX from response.text:

Remove leading/trailing Markdown code fences (```latex, ```tex, ```).

Verify presence of \documentclass and \end{document}. If \end{document} is missing due to token cap, flag TRUNCATED_LATEX in the report before writing.

Overwrite the target .tex file using UTF-8 encoding (encoding="utf-8").

Phase 5: Auto-Compilation Hook (pdf_compiler_hook.py)
Invoke your existing .tex -> .pdf compiler script via subprocess.run(...) passing the updated .tex file paths (or target directory).

Verify that the corresponding .pdf file exists in Overleaf\.pdf\<RelPath>\<TargetSubfolder>\ and has size > 0 bytes.

Capture stdout/stderr or LaTeX .log error lines (! LaTeX Error:, ! Undefined control sequence) if compilation fails so you can immediately spot any syntax hiccup.

Phase 6: Cost & Final Execution Report (reporter.py)
Extract response.usage_metadata (prompt_token_count, thoughts_token_count, candidates_token_count, cached_content_token_count) for every section and compute exact USD cost:

Summary Table (Terminal + run_YYYYMMDD_HHMMSS.md):

Section PDF Name & Derived Topic

Target .tex Path

Tier Used (flex, batch_fallback, batch, standard)

Tokens (Input / Cached / Thinking / Output)

Estimated Cost ($USD)

LaTeX Validation (OK / Truncated)

PDF Compilation Status (Compiled / Failed + .pdf output path)

Elapsed Time (s)

5. Verification & Rollout Checklist
Create System Instructions Folder: Create Overleaf\System Instructions\ and save your AI Studio system instruction text file(s) inside it.

Configure .env & Compiler Path: Add GEMINI_API_KEY=... and set EXISTING_COMPILER_SCRIPT path in automation/config.py.

Dry-Run Test (--dry-run): Run on Chapter 6 - Functions of Random Variables\Book PDF targeting Homework to verify that 6.3 The Method of Distribution Functions.pdf maps to (Homework) 6.3 The Method of Distribution Functions.tex and extracts [TOPIC NAME] = The Method of Distribution Functions.

Single-Section Live Run: Run 1 PDF (6.1 Introduction.pdf) on Flex tier to confirm end-to-end .tex overwrite, PDF compilation, and cost reporting.

Batch Cancel Smoke Test: Submit a 1-file Batch Only job and immediately test the Cancel action while JOB_STATE_PENDING to confirm zero-cost cancellation.