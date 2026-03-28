import os
from pathlib import Path

# Cache Directories (Hidden by default to reduce clutter)
PDF_CACHE_DIR = Path("./.pdf_cache")
HF_HOME_DIR = Path("./.hf_cache")

# Source Directories
LABOUR_LAW_DIR = Path("./data/labour_law")
TESTS_DIR = LABOUR_LAW_DIR / "tests"

# File Paths
INDEX_PATH = PDF_CACHE_DIR / "index.faiss"
CHUNKS_PATH = PDF_CACHE_DIR / "chunks.json"
MANIFEST_PATH = PDF_CACHE_DIR / "manifest.json"
REVIEW_LOG_PATH = PDF_CACHE_DIR / "review_log.csv"

# Authority Tiers
AUTHORITY_TIERS = {
    "primary": "Top-tier Authority",
    "statutory": "Statutory Authority",
    "resources": "Supplemental Resources",
    "jurisprudence": "Jurisprudence & Precedent",
}

# Public GitHub raw URL base for labour_law PDFs.
GITHUB_LABOUR_LAW_URL = (
    "https://github.com/DerekRoberts/vexilon/tree/main/data/labour_law"
)
_GITHUB_RAW_BASE = "https://raw.githubusercontent.com/DerekRoberts/vexilon/main"

# AI Model Configuration
CLAUDE_MODEL = os.getenv("CLAUDE_MODEL", "claude-haiku-4-5-20251001")
CONDENSE_MODEL = os.getenv("CONDENSE_MODEL", "claude-haiku-4-5-20251001")
EMBED_MODEL = os.getenv("EMBED_MODEL", "BAAI/bge-small-en-v1.5")
VERIFY_MODEL = os.getenv("VERIFY_MODEL", "claude-haiku-4-5-20251001")
REVIEWER_MODEL = os.getenv("REVIEWER_MODEL", "claude-haiku-4-5-20251001")

# RAG Parameters
EMBED_DIM = 384
CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", 450))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", 100))
SIMILARITY_TOP_K = int(os.getenv("SIMILARITY_TOP_K", 40))

# Memory / Context Condensation
CONDENSE_QUERY_HISTORY_TURNS = int(os.getenv("CONDENSE_QUERY_HISTORY_TURNS", 3))
CONDENSE_QUERY_CONTENT_MAX_LEN = int(os.getenv("CONDENSE_QUERY_CONTENT_MAX_LEN", 200))

# Security & Rate Limiting
MAX_INPUT_LENGTH = int(os.getenv("MAX_INPUT_LENGTH", 2000))
LOG_SUSPICIOUS_INPUTS = os.getenv("LOG_SUSPICIOUS_INPUTS", "true").lower() == "true"
RATE_LIMIT_PER_MINUTE = int(os.getenv("RATE_LIMIT_PER_MINUTE", "10"))
RATE_LIMIT_PER_HOUR = int(os.getenv("RATE_LIMIT_PER_HOUR", "100"))

# Feature Toggles
VERIFY_ENABLED = os.getenv("VERIFY_ENABLED", "true").lower() == "true"
USE_REVIEWER = os.getenv("USE_REVIEWER", "false").lower() == "true"

# Vexilon Identity
VEXILON_USERNAME = os.getenv("VEXILON_USERNAME", "admin")
VEXILON_PASSWORD = os.getenv("VEXILON_PASSWORD")
