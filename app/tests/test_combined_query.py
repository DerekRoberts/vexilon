import pytest
from unittest.mock import AsyncMock, patch, MagicMock
import main as app

@pytest.mark.asyncio
async def test_condense_and_generate_perspectives_empty_history():
    """Verify that empty history returns the message itself and its list wrapper immediately."""
    message = "vacation rules"
    history = []
    
    condensed, perspectives = await app.condense_and_generate_perspectives(message, history)
    
    assert condensed == message
    assert perspectives == [message]

@pytest.mark.asyncio
async def test_condense_and_generate_perspectives_success():
    """Verify successful parsing of structured JSON from combined LLM query pass."""
    message = "What about part-time?"
    history = [{"role": "user", "content": "How many vacation days do full-time stewards get?"}]
    
    mock_client = MagicMock()
    mock_completion = MagicMock()
    mock_completion.choices = [MagicMock(message=MagicMock(content=(
        '{\n'
        '  "condensed_query": "part-time steward vacation days",\n'
        '  "perspectives": ["part-time vacation entitlement", "article 12 part-time leave", "steward vacation rights"]\n'
        '}'
    )))]
    mock_client.chat.completions.create = AsyncMock(return_value=mock_completion)
    
    with patch("main.get_llm_client", return_value=mock_client):
        condensed, perspectives = await app.condense_and_generate_perspectives(message, history)
        
    assert condensed == "part-time steward vacation days"
    assert len(perspectives) == 3
    assert "part-time vacation entitlement" in perspectives
    assert "article 12 part-time leave" in perspectives
    assert "steward vacation rights" in perspectives

@pytest.mark.asyncio
async def test_condense_and_generate_perspectives_markdown_wrapping():
    """Verify that JSON wrapped in markdown formatting is still correctly extracted and parsed."""
    message = "Any updates?"
    history = [{"role": "user", "content": "Tell me about the grievance process."}]
    
    mock_client = MagicMock()
    mock_completion = MagicMock()
    mock_completion.choices = [MagicMock(message=MagicMock(content=(
        'Here is the JSON:\n'
        '```json\n'
        '{\n'
        '  "condensed_query": "grievance process updates",\n'
        '  "perspectives": ["grievance time limits", "step 2 grievance updates", "arbitration timelines"]\n'
        '}\n'
        '```\n'
        'Hope this helps!'
    )))]
    mock_client.chat.completions.create = AsyncMock(return_value=mock_completion)
    
    with patch("main.get_llm_client", return_value=mock_client):
        condensed, perspectives = await app.condense_and_generate_perspectives(message, history)
        
    assert condensed == "grievance process updates"
    assert len(perspectives) == 3
    assert "grievance time limits" in perspectives

@pytest.mark.asyncio
async def test_condense_and_generate_perspectives_api_failure():
    """Verify fallback behavior (returning raw message) if the LLM API fails or returns garbage."""
    message = "How to file a grievance"
    history = [{"role": "user", "content": "Hello"}]
    
    mock_client = MagicMock()
    mock_client.chat.completions.create = AsyncMock(side_effect=Exception("API limit exceeded"))
    
    with patch("main.get_llm_client", return_value=mock_client):
        condensed, perspectives = await app.condense_and_generate_perspectives(message, history)
        
    assert condensed == message
    assert perspectives == [message]

def test_has_chainlit_context_outside_session():
    """Verify has_chainlit_context returns False when called from tests (no Chainlit session active)."""
    assert app.has_chainlit_context() is False

@pytest.mark.asyncio
async def test_status_step_dummy_fallback():
    """Verify status_step safely yields a dummy step object outside a Chainlit context, avoiding context exceptions."""
    async with app.status_step("Testing safe UI step fallback...") as step:
        step.output = "Setting dummy step output"
        await step.update()
        await step.remove()
        
    assert step.output == "Setting dummy step output"

@pytest.mark.asyncio
async def test_condense_and_generate_perspectives_non_dict_json():
    """Verify that if LLM returns valid JSON but it is a list rather than a dict, it raises a ValueError and falls back gracefully."""
    message = "Any updates?"
    history = [{"role": "user", "content": "Tell me about grievances."}]
    
    mock_client = MagicMock()
    mock_completion = MagicMock()
    mock_completion.choices = [MagicMock(message=MagicMock(content='["some", "random", "list"]'))]
    mock_client.chat.completions.create = AsyncMock(return_value=mock_completion)
    
    with patch("main.get_llm_client", return_value=mock_client):
        condensed, perspectives = await app.condense_and_generate_perspectives(message, history)
        
    assert condensed == message
    assert perspectives == [message]
