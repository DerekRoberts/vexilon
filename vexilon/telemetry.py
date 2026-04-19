import os
import logging
import datetime
from typing import Optional

logger = logging.getLogger(__name__)

# Lazy pool initialization
_pool = None

async def get_pool():
    global _pool
    if _pool is not None:
        return _pool
        
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        return None
        
    try:
        import asyncpg
        _pool = await asyncpg.create_pool(db_url)
        
        # Verify schema
        async with _pool.acquire() as conn:
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS telemetry (
                    id SERIAL PRIMARY KEY,
                    timestamp TIMESTAMPTZ DEFAULT NOW(),
                    user_id TEXT,
                    persona TEXT,
                    query TEXT,
                    response_preview TEXT,
                    score INTEGER,
                    input_tokens INTEGER,
                    output_tokens INTEGER,
                    cache_creation_tokens INTEGER,
                    cache_read_tokens INTEGER,
                    latency_ms INTEGER
                );
            """)
        logger.info("[telemetry] External database connected and schema verified.")
        return _pool
    except Exception as e:
        logger.error(f"[telemetry] Database connection failed: {e}")
        return None

async def log_interaction(
    user_id: str,
    persona: str,
    query: str,
    response_preview: str,
    score: Optional[int],
    input_tokens: int,
    output_tokens: int,
    cache_creation_tokens: int,
    cache_read_tokens: int,
    latency_ms: int
):
    """
    Log an interaction to the external database.
    Falls back to structured logging if DATABASE_URL is missing.
    """
    pool = await get_pool()
    
    if not pool:
        # Fallback to structured log
        logger.info(
            f"[telemetry] interaction user={user_id} persona={persona} score={score} "
            f"tokens_in={input_tokens} tokens_out={output_tokens} "
            f"cache_new={cache_creation_tokens} cache_hit={cache_read_tokens} "
            f"latency={latency_ms}ms"
        )
        return

    try:
        async with pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO telemetry (
                    user_id, persona, query, response_preview, score, 
                    input_tokens, output_tokens, cache_creation_tokens, cache_read_tokens, latency_ms
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
            """, 
            user_id, persona, query, response_preview[:200], score, 
            input_tokens, output_tokens, cache_creation_tokens, cache_read_tokens, latency_ms
            )
    except Exception as e:
        logger.error(f"[telemetry] Failed to insert record: {e}")
