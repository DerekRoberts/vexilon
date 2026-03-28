"""
tests/integration/test_app_flow.py — Full-flow integration test

Verifies that the app can start up, load the PDF, index it, and run a RAG query
using the real embedding model but a mocked Anthropic API.
"""

import pytest
import app as main_app
from src.vexilon import vector, config, loader, utils
from pathlib import Path

@pytest.mark.asyncio
async def test_full_rag_flow_integration(monkeypatch, mock_anthropic, tmp_path):
    """
    Tests the system from PDF loading to streaming response.
    Uses the real PDF and real embedding model.
    """
    # 1. Setup: Ensure we use the real PDF and a temporary index path to avoid clobbering prod
    test_pdf = Path("data/labour_law/bcgeu_19th_main_agreement.pdf")
    if not test_pdf.exists():
        pytest.skip(f"Agreement PDF missing at {test_pdf}; cannot run full integration test.")

    # Redirect pdf_cache to a temp dir so save_index() doesn't fail on missing directory
    cache_dir = tmp_path / "pdf_cache"
    cache_dir.mkdir()
    monkeypatch.setattr(config, "PDF_CACHE_DIR", cache_dir)
    monkeypatch.setattr(config, "INDEX_PATH", cache_dir / "index.faiss")
    monkeypatch.setattr(config, "CHUNKS_PATH", cache_dir / "chunks.json")

    # Mock the anthropic client globally for the app
    monkeypatch.setattr(main_app, "get_anthropic", lambda: mock_anthropic)
    
    # 2. Startup: This builds the index in memory (slow but thorough)
    # We use force_rebuild=True to ensure we test the parsing/indexing logic
    main_app.startup(force_rebuild=True)
    
    assert main_app._index is not None
    assert len(main_app._chunks) > 0
    
    # 3. Query: Run a real RAG query
    # This will:
    # - Run condense_query (mocked Claude)
    # - Run search_index (REAL FAISS + REAL Embeddings)
    # - Run rag_stream (mocked Claude)
    message = "What are the rules for overtime?"
    history = []
    
    tokens = []
    async for chunk, context_val in main_app.rag_review_stream(message, history):
        tokens.append(chunk)
    
    # 4. Assertions
    full_response = "".join(tokens)
    assert "Mocked response content" in full_response
    assert main_app._index.ntotal > 0
    
    # Check that search actually found something
    query = "overtime rate"
    results = vector.search_index(main_app._index, main_app._chunks, query, k=1)
    assert len(results) == 1
    assert "overtime" in results[0]["text"].lower()
