import pytest
from unittest.mock import AsyncMock, patch, MagicMock
import main as app

@pytest.mark.asyncio
async def test_rag_stream_single_query_flow(monkeypatch):
    """Verify that rag_stream successfully runs with a single query search and deduplicates context."""
    monkeypatch.setattr(app, "IS_DEV", False)
    fake_index = MagicMock()
    monkeypatch.setattr(app, "_index", fake_index)
    
    chunk1 = {"text": "Original Article 1 text.", "page": 1, "source": "DocA"}
    monkeypatch.setattr(app, "_chunks", [chunk1])

    monkeypatch.setattr(app, "condense_query", AsyncMock(return_value="condensed query"))

    search_calls = []
    def mock_search_batch(index, chunks, queries, top_ks):
        for q in queries:
            search_calls.append(q)
        return [[chunk1]]

    monkeypatch.setattr(app, "search_index_batch", mock_search_batch)

    # Mock OpenAI stream
    mock_client = MagicMock()
    
    async def _mock_openai_stream(**kwargs):
        system_prompt = kwargs.get("system", "")
        if kwargs.get("stream"):
            async def _gen():
                assert "Original Article 1 text." in system_prompt
                chunk = MagicMock()
                chunk.choices = [MagicMock(delta=MagicMock(content="Mocked response content."))]
                yield chunk
            return _gen()
        return MagicMock()

    mock_client.chat.completions.create = AsyncMock(side_effect=_mock_openai_stream)
    monkeypatch.setattr(app, "get_llm_client", lambda: mock_client)

    async for chunk, ctx in app.rag_stream("Complex question about agreement rules", [{"role": "user", "content": "hi"}]):
        pass

    assert len(search_calls) == 1
    assert "condensed query" in search_calls
