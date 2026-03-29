"""
tests/integration/test_app_flow.py — Full-flow integration test

Verifies that the app can start up, load the PDF, index it, and run a RAG query
using the real embedding model but a mocked Anthropic API.
"""

import pytest
import app
from pathlib import Path

@pytest.mark.asyncio
async def test_full_rag_flow_integration(monkeypatch, mock_anthropic, tmp_path):
    """
    Tests the system from Markdown loading to streaming response.
    Uses the real MD agreement and real embedding model.
    """
    # 1. Setup: Ensure we use the real MD and a temporary index path to avoid clobbering prod
    test_md = Path("data/labour_law/01_primary/BCGEU 19th Main Agreement.md")
    if not test_md.exists():
        pytest.skip(f"Agreement Markdown missing at {test_md}; cannot run full integration test.")

    # Redirect pdf_cache to a temp dir so save_index() doesn't fail on missing directory
    cache_dir = tmp_path / "pdf_cache"
    cache_dir.mkdir()
    monkeypatch.setattr(app, "PDF_CACHE_DIR", cache_dir)
    monkeypatch.setattr(app, "INDEX_PATH", cache_dir / "index.faiss")
    monkeypatch.setattr(app, "CHUNKS_PATH", cache_dir / "chunks.json")

    # Mock the anthropic client globally for the app
    monkeypatch.setattr(app, "get_anthropic", lambda: mock_anthropic)
    
    # 2. Startup: This builds the index in memory (slow but thorough)
    app.startup(force_rebuild=True)
    
    assert app._index is not None
    assert len(app._chunks) > 0
    
    # 3. Query: Run a real RAG query
    message = "What are the rules for overtime?"
    history = []
    
    tokens = []
    async for text_chunk, context_chunk in app.rag_stream(message, history):
        if text_chunk:
            tokens.append(text_chunk)
    
    # 4. Assertions
    full_response = "".join(tokens)
    assert "Mocked response content" in full_response
    assert app._index.ntotal > 0
    
    # Check that search actually found something
    query = "overtime rate"
    results = app.search_index(app._index, app._chunks, query, top_k=1)
    assert len(results) == 1
    assert "overtime" in results[0]["text"].lower()
