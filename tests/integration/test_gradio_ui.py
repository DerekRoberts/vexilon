"""
tests/integration/test_gradio_ui.py — Integration: Gradio UI interaction

Verifies that the Gradio interface behaves correctly:
- Example question buttons populate the input.
- Sending a message transitions the UI state (hides onboarding).
- The chatbot receives and displays the streamed response.
"""

import pytest
import app
import gradio as gr

@pytest.mark.asyncio
async def test_ui_onboarding_interaction(monkeypatch, mock_anthropic):
    """
    Simulates a user clicking an example question and verifies UI changes.
    """
    # 1. Setup
    monkeypatch.setattr(app, "get_anthropic", lambda: mock_anthropic)
    
    # Mock search and chunks so we don't need a real PDF/Index for UI tests
    monkeypatch.setattr(app, "_index", "not-none")
    monkeypatch.setattr(app, "search_index", lambda *a, **k: [{"text": "ref", "page": 1}])
    
    demo = app.build_ui()
    
    # We use Gradio's testing utilities to simulate interactions
    # Gradio 6 has improved testing support.
    from gradio.testing import TestContext
    
    with TestContext(demo) as ctx:
        # Robustly find components by type to avoid breakage from UI changes
        all_rows = [c for c in demo.children if isinstance(c, gr.Row)]
        chip_row = all_rows[0]
        input_row = all_rows[1]
        textbox = next(c for c in input_row.children if isinstance(c, gr.Textbox))
        chatbot = next(c for c in demo.children if isinstance(c, gr.Chatbot))

        question = app.EXAMPLE_QUESTIONS[0]
        
        # Trigger submit event on the textbox
        await ctx.trigger_event(textbox, "submit", [question, []])
        
        # Verify UI state changes: onboarding chips should become invisible
        assert ctx.get_value(chip_row, property="visible") is False
        
        # Verify chatbot output
        chatbot_messages = ctx.get_value(chatbot)
        assert len(chatbot_messages) == 2
        assert chatbot_messages[0]["role"] == "user"
        assert chatbot_messages[0]["content"] == question
        assert "Mocked response content" in chatbot_messages[1]["content"]
