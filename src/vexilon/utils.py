import time
import datetime
import threading
import logging
import sys
import os
import re
from pathlib import Path
from typing import TYPE_CHECKING
from src.vexilon import config

if TYPE_CHECKING:
    import platform

# ─── Rate Limiter ─────────────────────────────────────────────────────────────
_SECONDS_IN_MINUTE = 60
_SECONDS_IN_HOUR = 3600

class RateLimiter:
    """Simple in-memory rate limiter for request throttling."""
    def __init__(self, max_per_minute: int = 10, max_per_hour: int = 100):
        self.minute_limit = max_per_minute
        self.hour_limit = max_per_hour
        self.requests: dict[str, list[float]] = {}
        self._lock = threading.Lock()

    def _clean_old_requests(self, key: str) -> None:
        """Remove requests older than 1 hour."""
        now = time.time()
        hour_ago = now - _SECONDS_IN_HOUR
        if key in self.requests:
            self.requests[key] = [t for t in self.requests[key] if t > hour_ago]
            if not self.requests[key]:
                del self.requests[key]

    def is_allowed(self, user_id: str = "default") -> tuple[bool, str]:
        """Check if request is allowed."""
        with self._lock:
            self._clean_old_requests(user_id)
            now = time.time()
            minute_ago = now - _SECONDS_IN_MINUTE

            requests = self.requests.get(user_id, [])
            recent_requests = [t for t in requests if t > minute_ago]

            if len(recent_requests) >= self.minute_limit:
                return (False, f"Rate limit exceeded: {self.minute_limit} per minute.")
            if len(requests) >= self.hour_limit:
                return (False, f"Rate limit exceeded: {self.hour_limit} per hour.")

            self.requests.setdefault(user_id, []).append(now)
            return True, ""

# ─── Input Sanitization ───────────────────────────────────────────────────────
PROMPT_INJECTION_PATTERNS = [
    re.compile(r, re.IGNORECASE)
    for r in [
        r"ignore\s+.*instructions",
        r"forget\s+.*instructions",
        r"disregard\s+.*rules",
        r"you\s+are\s+now\s+.+\s+instead",
        r"new\s+(system\s+|)prompt:",
        r"#\#\#\s*(system\s+|)instructions",
        r"\[\[SYSTEM\]\]",
        r"override\s+.*instructions",
        r"disable\s+.*safety",
        r"\bjailbreak\b",
        r"developer\s+mode",
        r"sudo\s+mode",
        r"roleplay\s+as",
        r"pretend\s+(you\s+are|to\s+be)",
        r"forget\s+everything\s+above",
        r"discard\s+.*instructions",
    ]
]

def sanitize_input(user_input: str) -> tuple[str, bool]:
    """Check for prompt injection patterns and length limits."""
    if not user_input:
        return user_input, False

    injection_found = any(p.search(user_input) for p in PROMPT_INJECTION_PATTERNS)
    too_long = len(user_input) > config.MAX_INPUT_LENGTH

    if (injection_found or too_long) and config.LOG_SUSPICIOUS_INPUTS:
        reason = "injection" if injection_found else "length"
        logging.warning(f"[security] Suspicious input detected ({reason}).")

    return user_input[:config.MAX_INPUT_LENGTH], injection_found or too_long

# ─── Vexilon Info ─────────────────────────────────────────────────────────────
def log_review(query: str, raw_response: str, review_output: str, score: int) -> None:
    """Append a review record to the audit log CSV."""
    import csv
    
    log_path = config.PDF_CACHE_DIR / "review_log.csv"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    write_header = not log_path.exists()
    
    with open(log_path, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if write_header:
            writer.writerow(["timestamp", "query", "raw_response", "review_output", "score", "steward"])
        writer.writerow([
            datetime.datetime.now().isoformat(),
            query[:500],
            raw_response[:1000],
            review_output[:2000],
            score,
            config.VEXILON_USERNAME,
        ])
def get_vexilon_info():
    """Get Version, Python and OS metadata."""
    import platform
    version = os.getenv("VEXILON_VERSION", "unspecified-local")
    source = "External/CI" if os.getenv("VEXILON_VERSION") else "fallback"
    
    if version == "unspecified-local":
        try:
            with open("/app/build_version.txt", "r") as f:
                version = f.read().strip()
                source = "Local Build"
        except FileNotFoundError:
            pass

    py_ver = sys.version.split()[0]
    os_info = platform.system()
    return {"ver": version, "src": source, "py": py_ver, "os": os_info}

def print_banner(info: dict):
    """Print the startup banner."""
    print("=" * 50)
    print(f" VEXILON VERSION : {info['ver']} ({info['src']})")
    print(f" PYTHON VERSION  : {info['py']}")
    print(f" RUNTIME OS      : {info['os']}")
    print("=" * 50, flush=True)

def fetch_pdf_cache_if_missing() -> None:
    """Download pre-computed FAISS index from GitHub if it doesn't exist locally."""
    import urllib.request
    if config.INDEX_PATH.exists() and config.CHUNKS_PATH.exists():
        return

    config.PDF_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    print(f"[bootstrap] Cache missing. Fetching from {config._GITHUB_RAW_BASE}…")
    
    # Files are served from the root of the branch in raw mode
    assets = ["index.faiss", "chunks.json"]
    for asset in assets:
        dest = config.PDF_CACHE_DIR / asset
        if dest.exists():
            continue
        url = f"{config._GITHUB_RAW_BASE}/{asset}"
        try:
            print(f"[bootstrap] Downloading {asset}…")
            urllib.request.urlretrieve(url, str(dest))
        except Exception as e:
            print(f"[bootstrap] Failed to download {asset}: {e}")

def save_temp_md(content: str) -> str:
    """Save markdown content to a temporary file and return its path."""
    import tempfile
    fd, path = tempfile.mkstemp(suffix=".md")
    with os.fdopen(fd, 'w') as f:
        f.write(content)
    os.close(fd)
    return path
