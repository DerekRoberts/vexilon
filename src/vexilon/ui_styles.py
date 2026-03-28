# src/vexilon/ui_styles.py
"""UI constants: CSS, HTML banners, and example questions for the Gradio interface."""

from src.vexilon import config

# ─── Example Questions (Suggested Chips) ─────────────────────────────────────
EXAMPLE_QUESTIONS = [
    "What are the just cause requirements for discipline?",
    "What rights do stewards have in investigation meetings?",
    "What is the nexus test for off-duty conduct?",
    "Does my employer have a social media policy?",
    "What happens if I'm disciplined for off-duty behavior?",
]

# ─── HTML Banners ─────────────────────────────────────────────────────────────
# Disclaimer rendered entirely with inline styles so Gradio theme cannot override text colour.
DISCLAIMER_HTML = (
    '<div style="'
    "background-color:#fff8e1;"
    "border-left:4px solid #f59e0b;"
    "color:#7c4a00;"
    "padding:10px 14px;"
    "border-radius:4px;"
    "font-size:0.85rem;"
    "margin-bottom:12px;"
    '">'
    "This project is not affiliated with the BCGEU. AI-generated responses may contain errors."
    "</div>"
)

DIRECT_MODE_HTML = """
<div style="background-color:#e0f2fe; border-left:4px solid #0ea5e9; color:#075985; padding:10px 14px; border-radius:4px; font-size:0.85rem; margin-bottom:12px;">
    <b>⚡ Direct Advice Mode Active:</b> Responses focus on operational steps and scripts.
</div>
"""

CASE_BUILDER_HTML = """
<div style="background-color:#f0fdf4; border-left:4px solid #22c55e; color:#14532d; padding:10px 14px; border-radius:4px; font-size:0.85rem; margin-bottom:12px;">
    <b>📝 Case Builder Mode Active:</b> Responses focus on drafting formal rebuttals and grievances.
</div>
"""

# ─── Custom CSS ───────────────────────────────────────────────────────────────
CUSTOM_CSS = """
/* 1. Unified row alignment */
.compact-row {
    align-items: center !important;
    gap: 6px !important;
    flex-wrap: nowrap !important;
    overflow: visible !important;
}

/* 2. Persona Segmented Control (Pill style) */
#persona_selector.block {
    background: transparent !important;
    border: none !important;
    padding: 0 !important;
    margin: 0 !important;
    min-width: fit-content !important;
}
#persona_selector .wrap {
    display: flex !important;
    gap: 0 !important;
    flex-wrap: nowrap !important;
    padding: 0 !important;
}
#persona_selector label {
    flex: 1 !important;
    height: 32px !important;
    line-height: 32px !important;
    padding: 0 !important;
    border: 1px solid var(--border-color-primary) !important;
    font-size: 0.8rem !important;
    border-radius: 0 !important;
    background: var(--background-fill-secondary) !important;
    cursor: pointer !important;
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
}
#persona_selector label span {
    margin: 0 !important;
    padding: 0 !important;
}
#persona_selector label:not(:last-child) {
    margin-right: -1px !important;
}
#persona_selector label:first-child {
    border-top-left-radius: 8px !important;
    border-bottom-left-radius: 8px !important;
}
#persona_selector label:last-child {
    border-top-right-radius: 8px !important;
    border-bottom-right-radius: 8px !important;
}
#persona_selector input[type="radio"],
#persona_selector .radio-circle {
    display: none !important;
}
#persona_selector label.selected {
    background-color: var(--primary-500) !important;
    color: white !important;
    border-color: var(--primary-600) !important;
    z-index: 1;
}

/* 3. Reviewer Checkbox (Unified height) */
#reviewer_toggle.block {
    background: transparent !important;
    border: none !important;
    box-shadow: none !important;
    padding: 0 !important;
    margin: 0 !important;
    min-width: 90px !important;
    overflow: visible !important;
}
#reviewer_toggle label {
    height: 32px !important;
    line-height: 32px !important;
    padding: 0 10px !important;
    border: 1px solid var(--border-color-primary) !important;
    border-radius: 8px !important;
    font-size: 0.8rem !important;
    display: flex !important;
    align-items: center !important;
    white-space: nowrap !important;
    background: var(--background-fill-secondary) !important;
    cursor: pointer !important;
}
#reviewer_toggle input {
    margin: 0 6px 0 0 !important;
}

/* 4. Button normalization */
.sm-btn {
    height: 32px !important;
    min-height: 32px !important;
    padding: 0 10px !important;
    font-size: 0.8rem !important;
    min-width: 60px !important;
}
"""
