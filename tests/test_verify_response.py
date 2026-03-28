"""
tests/test_verify_response.py — Unit tests for verification bot

Tests verify the verify_response() function behavior.
"""

from contextlib import asynccontextmanager
from unittest.mock import MagicMock, patch

import anthropic
import pytest

import app as main_app
from src.vexilon import config, loader, vector, utils


def _fake_verify_response(
    model: str = "claude-haiku-4-5-20251001",
    max_tokens: int = 512,
    system: list = None,
    messages: list = None,
):
    """Create a fake async messages.create that returns a mock response."""
    fake_message = MagicMock()
    fake_message.text = "ALL_CLAIMS_VERIFIED"

    fake_response = MagicMock()
    fake_response.content = [fake_message]

    async def _create(*args, **kwargs):
        return fake_response

    return _create


@pytest.fixture
def mock_anthropic_client():
    """Create a mock Anthropic client."""
    mock_client = MagicMock()
    mock_client.messages.create = _fake_verify_response()
    return mock_client


@pytest.mark.asyncio
async def test_verify_response_disabled_when_flag_off(monkeypatch):
    """When VERIFY_ENABLED is False, verify_response returns empty string."""
    monkeypatch.setattr(config, "VERIFY_ENABLED", False)

    result = await main_app.verify_response("Some response", "Some context")
    assert result == ""


@pytest.mark.asyncio
async def test_verify_response_calls_anthropic(monkeypatch):
    """verify_response should call Anthropic API with the response and context."""
    mock_client = MagicMock()

    fake_message = MagicMock()
    fake_message.text = "ALL_CLAIMS_VERIFIED"
    fake_response = MagicMock()
    fake_response.content = [fake_message]
    mock_client.messages.create = MagicMock(return_value=fake_response)

    monkeypatch.setattr(main_app, "get_anthropic", lambda: mock_client)

    result = await main_app.verify_response("The response", "The context")

    mock_client.messages.create.assert_called_once()
    call_kwargs = mock_client.messages.create.call_args.kwargs
    assert "The response" in call_kwargs["messages"][0]["content"]
    assert "The context" in call_kwargs["messages"][0]["content"]


@pytest.mark.asyncio
async def test_verify_response_returns_verification_text(
    monkeypatch, mock_anthropic_client
):
    """verify_response returns the text from the verification model response."""
    monkeypatch.setattr(main_app, "get_anthropic", lambda: mock_anthropic_client)

    result = await main_app.verify_response("Response", "Context")

    assert result == "ALL_CLAIMS_VERIFIED"


@pytest.mark.asyncio
async def test_verify_response_handles_api_error(monkeypatch):
    """verify_response should handle API errors gracefully."""
    mock_client = MagicMock()

    async def _raising_create(*args, **kwargs):
        raise anthropic.APIStatusError(
            message="API error",
            response=MagicMock(status_code=500),
            body={"type": "error"},
        )

    mock_client.messages.create = _raising_create
    monkeypatch.setattr(main_app, "get_anthropic", lambda: mock_client)

    result = await main_app.verify_response("Response", "Context")

    assert "Verification unavailable" in result


@pytest.mark.asyncio
async def test_rag_stream_yields_context(monkeypatch):
    """rag_stream should include chunk context in the system prompt sent to Claude."""
    fake_chunks = [
        {"text": "Article 1 content.", "page": 5, "chunk_index": 0},
    ]

    # Mock condense_query to return a simple string
    async def _mock_condense(m, h): return m
    monkeypatch.setattr(main_app, "condense_query", _mock_condense)

    fake_index = MagicMock()
    monkeypatch.setattr(main_app, "_index", fake_index)
    monkeypatch.setattr(main_app, "_chunks", fake_chunks)
    monkeypatch.setattr(config, "VERIFY_ENABLED", False)

    def mock_search(*a, **kw):
        return fake_chunks

    monkeypatch.setattr(vector, "search_index", mock_search)

    captured_kwargs = {}

    @asynccontextmanager
    async def _stream_ctx(**kwargs):
        nonlocal captured_kwargs
        captured_kwargs = kwargs
        mock_stream = MagicMock()

        async def _async_gen():
            yield "Hello"

        mock_stream.text_stream = _async_gen()

        fake_usage = MagicMock(
            input_tokens=10,
            output_tokens=5,
            cache_creation_input_tokens=0,
            cache_read_input_tokens=0,
        )
        fake_message = MagicMock()
        fake_message.usage = fake_usage

        async def _get_final():
            return fake_message

        mock_stream.get_final_message = _get_final
        yield mock_stream

    mock_client = MagicMock()
    mock_client.messages.stream = _stream_ctx
    monkeypatch.setattr(main_app, "get_anthropic", lambda: mock_client)

    async for chunk in main_app.rag_review_stream("Question", []):
        pass

    # Context should be embedded in the system prompt, not yielded separately
    system_text = "".join([s.get("text", "") for s in captured_kwargs.get("system", [])])
    assert "Article 1 content" in system_text
    assert "Page: 5" in system_text
