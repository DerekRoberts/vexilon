import pytest
import app
import gradio as gr

def test_manager_mode_in_selector(monkeypatch, mock_anthropic):
    """
    Verifies that 'Manager Mode' is available in the persona selector.
    """
    monkeypatch.setattr(app, "get_anthropic", lambda: mock_anthropic)
    monkeypatch.setattr(app, "_index", "not-none")
    
    demo = app.build_ui()
    
    # Find the persona selector
    radio = None
    for child in demo.children:
        if isinstance(child, gr.Row):
            for sub in child.children:
                if isinstance(sub, gr.Radio) and sub.elem_id == "persona_selector":
                    radio = sub
        elif isinstance(child, gr.Radio) and child.elem_id == "persona_selector":
            radio = child
            
    assert radio is not None, "Persona selector (Radio) not found in UI"
    # Gradio Radio choices can be a list of tuples (label, value)
    choice_values = [c[1] if isinstance(c, tuple) else c for c in radio.choices]
    assert "Manager Mode" in choice_values, f"'Manager Mode' not found in choices: {radio.choices}"

def test_manager_persona_prompt(monkeypatch):
    """
    Verifies that get_persona_prompt returns the correctly formatted manager prompt.
    """
    prompt = app.get_persona_prompt("Manager Mode")
    assert "Senior Strategic Management Consultant" in prompt
    assert "INADVERTENT BENEFIT WARNING" in prompt
    assert "Operational Framework" in prompt
    assert "> \"...\"" in prompt # Verbatim quote rule
