import os
import logging
import httpx
from typing import Optional

logger = logging.getLogger(__name__)

async def log_interaction(
    user_id: str,
    persona: str,
    score: Optional[int],
    input_tokens: int,
    output_tokens: int,
    cache_creation_tokens: int,
    cache_read_tokens: int,
    latency_ms: int
):
    """
    Log interaction metadata to an external HTTP endpoint (Axiom, Supabase REST, etc.)
    Silent Skip: If TELEMETRY_URL is not set, this function does nothing.
    Privacy First: No query content or response text is logged.
    """
    url = os.getenv("TELEMETRY_URL")
    if not url:
        return

    key = os.getenv("TELEMETRY_KEY")
    
    payload = {
        "steward_id": user_id,
        "persona": persona,
        "score": score,
        "tokens_in": input_tokens,
        "tokens_out": output_tokens,
        "cache_new": cache_creation_tokens,
        "cache_hit": cache_read_tokens,
        "latency_ms": latency_ms,
        "environment": os.getenv("VEXILON_ENV", "production")
    }

    headers = {}
    if key:
        # Standard bearer token or Supabase-style apikey header
        headers["Authorization"] = f"Bearer {key}"
        headers["apikey"] = key # Compatibility with Supabase PostgREST

    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(url, json=payload, headers=headers, timeout=5.0)
            if resp.status_code >= 400:
                logger.warning(f"[telemetry] Failed to log interaction: {resp.status_code} {resp.text}")
    except Exception as e:
        logger.warning(f"[telemetry] Error sending telemetry: {e}")
