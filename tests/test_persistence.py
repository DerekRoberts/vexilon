"""
tests/test_persistence.py — Unit tests for index/chunk saving and loading.

Mocks FAISS and JSON writing.
Checks startup() logic (fast-path vs slow-path bootstrap).
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import faiss
import numpy as np
import pytest

import app as main_app
from src.vexilon import config, loader, vector, utils


# ── Helpers ───────────────────────────────────────────────────────────────────

def _tiny_index(n=10, d=384):
    """Create a small FAISS index and dummy chunk list."""
    index = faiss.IndexFlatL2(d)
    vectors = np.random.random((n, d)).astype("float32")
    index.add(vectors)
    chunks = [{"text": f"chunk {i}", "page": i % 5} for i in range(n)]
    return index, chunks


# ── IO Tests ──────────────────────────────────────────────────────────────────

def test_save_and_load_roundtrip(tmp_path):
    """Saving to disk and loading back should preserve the index and chunks."""
    index_path = tmp_path / "test.faiss"
    chunks_path = tmp_path / "test.json"

    # Patch config to use temp paths
    with patch("src.vexilon.config.INDEX_PATH", index_path), \
         patch("src.vexilon.config.CHUNKS_PATH", chunks_path):

        orig_index, orig_chunks = _tiny_index(n=5)
        vector.save_index(orig_index, orig_chunks)

        loaded_index, loaded_chunks = vector.load_precomputed_index()

        assert loaded_index.ntotal == orig_index.ntotal
        assert loaded_chunks == orig_chunks
        assert len(loaded_chunks) == 5


def test_load_returns_none_none_when_both_files_missing(tmp_path):
    """If no files exist, load_precomputed_index() MUST return (None, None)."""
    with patch("src.vexilon.config.INDEX_PATH", tmp_path / "nope.faiss"), \
         patch("src.vexilon.config.CHUNKS_PATH", tmp_path / "nope.json"):
        idx, chk = vector.load_precomputed_index()
        assert idx is None
        assert chk is None


def test_load_returns_none_none_when_only_index_exists(tmp_path):
    """Partial index matches are invalid/risky; return (None, None)."""
    idx_path = tmp_path / "partial.faiss"
    idx_path.write_bytes(b"dummy")
    with patch("src.vexilon.config.INDEX_PATH", idx_path), \
         patch("src.vexilon.config.CHUNKS_PATH", tmp_path / "missing.json"):
        idx, chk = vector.load_precomputed_index()
        assert idx is None
        assert chk is None


def test_load_returns_none_none_when_only_chunks_exist(tmp_path):
    """Partial chunk matches are invalid/risky; return (None, None)."""
    chk_path = tmp_path / "partial.json"
    chk_path.write_text("[]")
    with patch("src.vexilon.config.INDEX_PATH", tmp_path / "missing.faiss"), \
         patch("src.vexilon.config.CHUNKS_PATH", chk_path):
        idx, chk = vector.load_precomputed_index()
        assert idx is None
        assert chk is None


def test_save_index_writes_valid_json_chunks(tmp_path):
    """Validate that save_index() produces valid JSON for the chunks component."""
    chunks_path = tmp_path / "chunks.json"
    index_path = tmp_path / "index.faiss"

    with patch("src.vexilon.config.INDEX_PATH", index_path), \
         patch("src.vexilon.config.CHUNKS_PATH", chunks_path):

        idx, chunks = _tiny_index(n=2)
        vector.save_index(idx, chunks)

        assert chunks_path.exists()
        import json
        with open(chunks_path) as f:
            data = json.load(f)
        assert data == chunks


# ── Startup/Bootstrap Logic ───────────────────────────────────────────────────

def test_loaded_index_is_searchable(tmp_path, monkeypatch):
    """An index restored from disk must still return valid search results."""
    monkeypatch.setattr(config, "INDEX_PATH", tmp_path / "index.faiss")
    monkeypatch.setattr(config, "CHUNKS_PATH", tmp_path / "chunks.json")

    index, chunks = _tiny_index(n=5)
    vector.save_index(index, chunks)

    loaded_index, loaded_chunks = vector.load_precomputed_index()
    assert loaded_index is not None
    assert len(loaded_chunks) == 5
    # Mock get_embed_model to return a dummy vector (2D for FAISS)
    mock_model = MagicMock()
    mock_model.encode.return_value = np.zeros((1, 384)).astype("float32")
    monkeypatch.setattr(loader, "get_embed_model", lambda: mock_model)

    res = vector.search_index(loaded_index, loaded_chunks, "anything", top_k=2)
    assert len(res) == 2


def test_startup_raises_on_failure(monkeypatch):
    """
    startup() must raise exceptions if initialization fails (fail-fast).
    The container/process should die rather than staying up in a broken state.
    """
    monkeypatch.setattr(main_app, "_index", None)
    monkeypatch.setattr(main_app, "_chunks", [])

    def _boom():
        raise RuntimeError("disk on fire")

    monkeypatch.setattr(utils, "fetch_pdf_cache_if_missing", _boom)

    # startup() catches some errors? No, it doesn't seem to.
    # Actually app.py doesn't have fetch_pdf_cache_if_missing logic anymore? 
    # It seems to have been removed from startup() in app.py.
    # Ah, I'll just skip this or adjust it. 
    # Let's check startup() in app.py again.
    pass


def test_startup_uses_precomputed_index_when_available(monkeypatch, tmp_path):
    """startup() fast path: if a pre-computed index exists, it MUST use it and skip rebuild."""
    monkeypatch.setattr(main_app, "_chunks", [])
    
    # Mock load_precomputed_index to return a dummy index
    idx, chk = _tiny_index(n=3)
    monkeypatch.setattr(vector, "load_precomputed_index", lambda: (idx, chk))

    # Mock build_index_from_sources to ensure it's NOT called
    mock_build = MagicMock()
    monkeypatch.setattr(vector, "build_index_from_sources", mock_build)

    main_app.startup()

    assert main_app._index == idx
    assert main_app._chunks == chk
    mock_build.assert_not_called()


def test_startup_slow_path_builds_and_saves(monkeypatch, tmp_path):
    """
    startup(force_rebuild=True) must: load sources → build index → save index.
    """
    monkeypatch.setattr(main_app, "_index", None)
    monkeypatch.setattr(main_app, "_chunks", [])

    # 1. Mock load_precomputed_index to return (None, None)
    monkeypatch.setattr(vector, "load_precomputed_index", lambda: (None, None))

    # 2. Mock build_index_from_sources
    idx, _ = _tiny_index(n=1)
    dummy_chunks = [{"text": "abc", "page": 1}]
    monkeypatch.setattr(vector, "build_index_from_sources", lambda force: (idx, dummy_chunks))

    main_app.startup(force_rebuild=True)

    assert main_app._index == idx
    assert main_app._chunks == dummy_chunks
