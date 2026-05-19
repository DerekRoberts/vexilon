import pytest
from unittest.mock import AsyncMock, patch, MagicMock
import main as app

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
