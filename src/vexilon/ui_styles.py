# src/vexilon/ui_styles.py

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
#persona_selector label.selected {
    background-color: var(--primary-500) !important;
    color: white !important;
    border-color: var(--primary-600) !important;
    z-index: 1;
}

/* 3. Reviewer Checkbox */
#reviewer_toggle.block {
    background: transparent !important;
    border: none !important;
    padding: 0 !important;
    margin: 0 !important;
    min-width: 90px !important;
}

/* 4. Button normalization */
.sm-btn {
    height: 32px !important;
    min-height: 32px !important;
    padding: 0 10px !important;
    font-size: 0.8rem !important;
}
"""

DISCLAIMER_HTML = """
<div style="background-color:#fff8e1; border-left:4px solid #f59e0b; color:#7c4a00; padding:10px 14px; border-radius:4px; font-size:0.85rem; margin-bottom:12px;">
    This project is not affiliated with the BCGEU. AI-generated responses may contain errors.
</div>
"""
