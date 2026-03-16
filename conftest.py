"""
conftest.py — pytest root configuration

Adds the project root to sys.path so `import app` works from tests/
regardless of how pytest is invoked.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import pytest
from unittest.mock import MagicMock, AsyncMock
from contextlib import asynccontextmanager

@pytest.fixture
def mock_anthropic():
    """Provides a mocked AsyncAnthropic client."""
    mock_client = MagicMock()
    
    @asynccontextmanager
    async def _mock_stream(*args, **kwargs):
        mock_stream = MagicMock()
        async def _async_gen():
            yield "Mocked response content."
        mock_stream.text_stream = _async_gen()
        
        # Mock get_final_message
        fake_message = MagicMock(usage=MagicMock(input_tokens=10, output_tokens=5, cache_creation_input_tokens=0, cache_read_input_tokens=0))
        mock_stream.get_final_message = AsyncMock(return_value=fake_message)
        
        yield mock_stream

    mock_client.messages.stream = _mock_stream
    
    # Mock messages.create for condense_query
    mock_resp = MagicMock()
    mock_resp.content = [MagicMock(text="Condensed search query")]
    mock_client.messages.create = AsyncMock(return_value=mock_resp)
    
    return mock_client
