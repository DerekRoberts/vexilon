"""
conftest.py — pytest root configuration

Adds the project root to sys.path so `import main` works from tests/
regardless of how pytest is invoked.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import pytest
import os
from unittest.mock import MagicMock, AsyncMock
from contextlib import asynccontextmanager

@pytest.fixture(autouse=True)
def mock_embedding_model(request, monkeypatch):
    """
    Mocks the embedding model and tokenizer for unit tests to prevent
    large model downloads. Integration tests are skipped.
    """
    if "integration" in str(request.path):
        return
    import main as app
    import indexing
    import sentence_transformers
    
    mock_model = MagicMock()
    
    # Mock tokenizer behavior for chunk_text
    mock_tokenizer = MagicMock()
    mock_tokenizer.is_fast = True
    
    def mock_tokenize_side_effect(text, **kwargs):
        tokens_count = (len(text) + 3) // 4 if text else 0
        return {
            "input_ids": [1] * tokens_count,
            "offset_mapping": [(i*4, min((i+1)*4, len(text))) for i in range(tokens_count)]
        }
        
    mock_tokenizer.side_effect = mock_tokenize_side_effect
    mock_model.tokenizer = mock_tokenizer
    mock_model.encode = MagicMock(return_value=[[0.1]*384])
    
    # The Nuclear Option: Patch the class itself so any instantiation returns our mock
    monkeypatch.setattr(sentence_transformers, "SentenceTransformer", lambda *args, **kwargs: mock_model)
    
    # Keep these for direct reference patching
    monkeypatch.setattr(app, "get_embed_model", lambda: mock_model)
    monkeypatch.setattr(indexing, "get_embed_model", lambda: mock_model)
    
    return mock_model

@pytest.fixture
def mock_llm_client():
    """Provides a mocked LLM client supporting OpenAI-compatible APIs (HF, Ollama)."""
    mock_client = MagicMock()
    
    # ── OpenAI / HF Style ──
    mock_chat = MagicMock()
    
    # Mock completions.create (non-streaming)
    mock_completion = MagicMock()
    mock_completion.choices = [MagicMock(message=MagicMock(content="Mocked response content"))]
    
    # Mock completions.create (streaming vs non-streaming)
    async def _mock_openai_create(*args, **kwargs):
        if kwargs.get("stream"):
            async def _gen():
                chunk = MagicMock()
                chunk.choices = [MagicMock(delta=MagicMock(content="Mocked response content."))]
                yield chunk
            return _gen()
        return mock_completion
    
    mock_chat.completions.create = AsyncMock(side_effect=_mock_openai_create)
    mock_client.chat = mock_chat
    
    return mock_client
