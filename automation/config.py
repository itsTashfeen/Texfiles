"""Paths, model pricing, prefix rules, and concurrency defaults."""

from __future__ import annotations

from pathlib import Path

MATHTEX_ROOT = Path(__file__).resolve().parent.parent
OVERLEAF_ROOT = MATHTEX_ROOT / "Overleaf"
PDF_ROOT = OVERLEAF_ROOT / ".pdf"
TEX_ROOT = OVERLEAF_ROOT / ".tex"
PROMPTS_DIR = OVERLEAF_ROOT / "Prompts"
SYSTEM_INSTRUCTIONS_DIR = OVERLEAF_ROOT / "System Instructions"
EXISTING_COMPILER_SCRIPT = OVERLEAF_ROOT / "watch_tex_to_pdf.py"

AUTOMATION_ROOT = Path(__file__).resolve().parent
STATE_DIR = AUTOMATION_ROOT / ".state"
BATCH_JOBS_PATH = STATE_DIR / "batch_jobs.json"
JOBS_PATH = STATE_DIR / "jobs.json"
REPORTS_DIR = AUTOMATION_ROOT / "reports"

BOOK_PDF_FOLDER = "Book PDF"
INLINE_PDF_MAX_BYTES = 18 * 1024 * 1024
# Default synchronous ceiling; Gemini 4 Long Decode uses MODEL_MAX_OUTPUT_TOKENS.
MAX_OUTPUT_TOKENS = 65_536
LONG_DECODE_MAX_OUTPUT_TOKENS = 1_048_576
# Batch API rejects decoding continuation / max_output_tokens above 65_536.
BATCH_MAX_OUTPUT_TOKENS = MAX_OUTPUT_TOKENS
HTTP_TIMEOUT_MS = 1_800_000  # 30 min — multi-hop Long Decode can exceed 15 min
MAX_WORKERS = 1
MAX_LATEX_CONTINUATION_TURNS = 2
PDF_MEDIA_RESOLUTION = "medium"  # "low" (280/pg) | "medium" (560/pg) | "high" (1120/pg)
MEDIA_RESOLUTIONS = ("low", "medium", "high")
CONTEXT_CACHE_TTL_SECONDS = 3600
DEFAULT_BUDGET_USD = 2.00
TOKEN_MISMATCH_RATIO = 3.0  # warn when BilledIn > ratio * InitIn
API_TRIM_MIN_PAGES = 3
FLEX_RETRY_BACKOFF_SECONDS = (15, 45, 90)
BATCH_POLL_INTERVAL_SECONDS = 30

DEFAULT_MODEL = "gemini-4-argon"
AVAILABLE_MODELS = (
    "gemini-4-argon",
    "gemini-4-carbon",
    "gemini-4-neon",
    "gemini-4-hydrogen",
    "gemini-3.1-pro-preview",
)
GEMINI4_MODELS = frozenset(
    {"gemini-4-argon", "gemini-4-carbon", "gemini-4-neon", "gemini-4-hydrogen"}
)

# Per-model output ceilings. Gemini 4 thinking+output share max_output_tokens;
# Long Decode (1_048_576) lets automatic_continuation finish past 65_536.
MODEL_MAX_OUTPUT_TOKENS: dict[str, int] = {
    "gemini-4-argon": LONG_DECODE_MAX_OUTPUT_TOKENS,
    "gemini-4-carbon": LONG_DECODE_MAX_OUTPUT_TOKENS,
    "gemini-4-neon": LONG_DECODE_MAX_OUTPUT_TOKENS,
    "gemini-4-hydrogen": LONG_DECODE_MAX_OUTPUT_TOKENS,
    "gemini-3.1-pro-preview": MAX_OUTPUT_TOKENS,
}

DEFAULT_THINKING_LEVEL = "high"
# Full AI Studio ladder. Not every model accepts every level — see MODEL_THINKING_LEVELS.
THINKING_LEVELS = ("low", "medium", "high", "xhigh")

# Supported thinking_level values per model (Gemini API / AI Studio).
MODEL_THINKING_LEVELS: dict[str, tuple[str, ...]] = {
    "gemini-4-argon": ("low", "medium", "high"),
    "gemini-4-carbon": ("low", "medium", "high"),
    "gemini-4-neon": ("low", "medium", "high", "xhigh"),
    "gemini-4-hydrogen": ("low", "medium", "high", "xhigh"),
    "gemini-3.1-pro-preview": ("low", "medium", "high"),
}

TIER_FLEX_BATCH_FALLBACK = "flex_batch_fallback"
TIER_FLEX_ONLY = "flex_only"
TIER_BATCH_ONLY = "batch_only"
TIER_STANDARD = "standard"

EXECUTION_TIERS = (
    (TIER_FLEX_BATCH_FALLBACK, "Flex + Auto Batch Fallback (Recommended)"),
    (TIER_FLEX_ONLY, "Flex Only"),
    (TIER_BATCH_ONLY, "Batch Only"),
    (TIER_STANDARD, "Standard (Real-Time)"),
)

# Folder name -> filename prefix used when no placeholder .tex exists yet.
FOLDER_PREFIX_MAP = {
    "Homework": "(Homework)",
    "Problem Sets": "(Problem Set)",
    "Book Section": "(Book Section)",
    "Book Sections": "(Book Section)",
}

# Chapter leaf folders that sit beside each other under Domain/Subject/Chapter.
# Selecting a PDF from any of these must still resolve RelPath to the Chapter.
CHAPTER_LEAF_FOLDERS = frozenset({BOOK_PDF_FOLDER, *FOLDER_PREFIX_MAP.keys()})

# USD per 1M tokens. Flex/Batch are 50% of standard list rates.
# Update when Google publishes final Gemini 4 pricing.
MODEL_PRICING_PER_1M = {
    "gemini-4-argon": {
        "standard": {"input": 1.25, "output": 10.00, "cached": 0.31},
        "flex": {"input": 0.625, "output": 5.00, "cached": 0.155},
        "batch": {"input": 0.625, "output": 5.00, "cached": 0.155},
    },
    "gemini-4-carbon": {
        "standard": {"input": 2.50, "output": 15.00, "cached": 0.625},
        "flex": {"input": 1.25, "output": 7.50, "cached": 0.3125},
        "batch": {"input": 1.25, "output": 7.50, "cached": 0.3125},
    },
    "gemini-4-neon": {
        # List rates (Nov 2026): $3 / $15; implicit cache $0.15. Flex/Batch = 50%.
        "standard": {"input": 3.00, "output": 15.00, "cached": 0.15},
        "flex": {"input": 1.50, "output": 7.50, "cached": 0.075},
        "batch": {"input": 1.50, "output": 7.50, "cached": 0.075},
    },
    "gemini-4-hydrogen": {
        "standard": {"input": 0.50, "output": 3.00, "cached": 0.125},
        "flex": {"input": 0.25, "output": 1.50, "cached": 0.0625},
        "batch": {"input": 0.25, "output": 1.50, "cached": 0.0625},
    },
    "gemini-3.1-pro-preview": {
        "standard": {"input": 1.25, "output": 10.00, "cached": 0.31},
        "flex": {"input": 0.625, "output": 5.00, "cached": 0.155},
        "batch": {"input": 0.625, "output": 5.00, "cached": 0.155},
    },
}


def max_output_tokens_for_model(model: str) -> int:
    return MODEL_MAX_OUTPUT_TOKENS.get(model, MAX_OUTPUT_TOKENS)


def thinking_levels_for_model(model: str) -> tuple[str, ...]:
    return MODEL_THINKING_LEVELS.get(model, THINKING_LEVELS)


def clamp_thinking_level(model: str, level: str) -> str:
    """Return a thinking_level the model accepts (e.g. xhigh → high on Argon/Carbon)."""
    normalized = (level or DEFAULT_THINKING_LEVEL).strip().lower()
    aliases = {
        "extra high": "xhigh",
        "extra_high": "xhigh",
        "extrahigh": "xhigh",
        "med": "medium",
    }
    normalized = aliases.get(normalized, normalized)
    allowed = thinking_levels_for_model(model)
    if normalized in allowed:
        return normalized
    if "high" in allowed:
        return "high"
    return allowed[-1] if allowed else DEFAULT_THINKING_LEVEL


def prefix_for_folder(folder_name: str) -> str:
    if folder_name in FOLDER_PREFIX_MAP:
        return FOLDER_PREFIX_MAP[folder_name]
    return f"({folder_name})"


def tier_label(tier_key: str) -> str:
    for key, label in EXECUTION_TIERS:
        if key == tier_key:
            return label
    return tier_key


def ensure_runtime_dirs() -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    SYSTEM_INSTRUCTIONS_DIR.mkdir(parents=True, exist_ok=True)
    if not BATCH_JOBS_PATH.exists():
        BATCH_JOBS_PATH.write_text("[]\n", encoding="utf-8")
    if not JOBS_PATH.exists():
        JOBS_PATH.write_text("[]\n", encoding="utf-8")
