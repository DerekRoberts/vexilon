"""
tests/test_deploy_integrity.py — Automated Deployment Readiness Checks
----------------------------------------------------------------------
Verifies that the codebase is ready for a 'Green' Hugging Face Space deploy.
Ensures metadata (README), Docker safety (Containerfile), and performance 
optimizations (app.py) are correctly synchronized.
"""
import os
import re
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent


def test_readme_metadata_sync():
    """Ensures README.md has the critical metadata for Docker HF Spaces."""
    readme_path = REPO_ROOT / "README.md"
    content = readme_path.read_text()
    
    # 1. Must be sdk: docker
    assert re.search(r"^sdk: docker", content, re.MULTILINE), \
        "README.md MUST have 'sdk: docker' for the current deployment strategy."
    
    # 2. Must have app_port: 7860 (prevents 'Still Building' status ghost)
    # Plus a warning comment to prevent drift
    assert re.search(r"^app_port: 7860.*drift", content, re.MULTILINE), \
        "README.md MUST have 'app_port: 7860' AND the sync-drift warning comment."
    
    # 3. Must NOT have Gradio-specific fields that confuse Docker mode
    assert not re.search(r"^sdk_version:", content, re.MULTILINE), \
        "README.md must NOT have 'sdk_version' — that's a Gradio SDK field, not Docker."
    assert not re.search(r"^app_file:", content, re.MULTILINE), \
        "README.md must NOT have 'app_file' — that's a Gradio SDK field, not Docker."
    
    # 4. Must have startup_duration_timeout to prevent HF from killing slow model loads
    assert re.search(r"^startup_duration_timeout: 10m", content, re.MULTILINE), \
        "README.md MUST have 'startup_duration_timeout: 10m' to prevent HF from killing the container during model loading."


def test_app_py_build_safety():
    """Ensures app.py doesn't contain global thread-pinning that hangs Docker builds."""
    app_path = REPO_ROOT / "app.py"
    content = app_path.read_text()
    
    # Check for OMP_NUM_THREADS or MKL_NUM_THREADS at top level (not inside a function)
    # This specifically checks for assignments happening outside of any def/if/with blocks
    # which is what caused our previous build-time hangs.
    
    for line in content.splitlines():
        if ("OMP_NUM_THREADS" in line or "MKL_NUM_THREADS" in line) and "=" in line:
            # If the assignment is at the start of the line (no indentation), it's global.
            # This is a basic safety check against regressions like PR #238.
            assert line.startswith(" ") or line.startswith("\t") or "os.getenv" in line or "os.environ.get" in line, \
                f"Potentially dangerous global thread pinning detected: {line.strip()}. Move this inside a function or conditioned check."


def test_containerfile_healthcheck_sync():
    """Ensures the Docker HEALTHCHECK port matches the app port."""
    containerfile_path = REPO_ROOT / "Containerfile"
    if not containerfile_path.exists():
        return # Skip if no Containerfile
        
    content = containerfile_path.read_text()
    
    # Check for the HEALTHCHECK port
    # CMD python -c "... http://localhost:7860"
    assert "localhost:7860" in content or "0.0.0.0:7860" in content, \
        "Containerfile HEALTHCHECK port must match the app port (7860)."


def test_mandatory_rules_no_stale_branch_links():
    """
    GLOBAL_MANDATORY_RULES must never contain GitHub raw URLs pointing at a
    specific feature branch (e.g. /raw/feat/NNN/ or /raw/fix/NNN/).
    Those branches eventually get deleted and the links 404.
    """
    import sys
    sys.path.insert(0, str(REPO_ROOT))
    import app  # noqa: PLC0415

    rules = app.get_mandatory_rules()

    # Catch any github.com/.../raw/<branch-name>/... pattern where branch-name
    # looks like a feature/fix/chore branch rather than 'main' or a tag.
    stale_pattern = re.compile(
        r"github\.com/[^/]+/[^/]+/raw/(?!main\b|master\b|v\d)([^/\s\"']+)/",
        re.IGNORECASE,
    )
    match = stale_pattern.search(rules)
    assert match is None, (
        f"get_mandatory_rules() contains a GitHub raw URL pointing at branch "
        f"'{match.group(1)}' which may not exist. Use Gradio's "
        f"/gradio_api/file= endpoint instead: {match.group(0)!r}"
    )


def test_mandatory_rules_uses_gradio_file_endpoint():
    """
    Grievance form links in the mandatory rules must use Gradio's
    /gradio_api/file= endpoint so they resolve at run-time from local disk,
    not from a remote URL that can go stale.
    """
    import sys
    sys.path.insert(0, str(REPO_ROOT))
    import app  # noqa: PLC0415

    rules = app.get_mandatory_rules()

    # All four forms must appear and each link must use the Gradio endpoint.
    for form_name in app._GRIEVANCE_FORM_NAMES:
        label = form_name.removesuffix(".pdf")
        assert label in rules, (
            f"Grievance form '{label}' is missing from get_mandatory_rules() output."
        )

    assert "/gradio_api/file=" in rules, (
        "get_mandatory_rules() must link forms via /gradio_api/file= so they "
        "are served from the running Gradio app, not a remote URL."
    )


def test_ui_title_is_not_debug_string():
    """
    The UI heading must not contain worktree/branch debug markers that were
    accidentally left in during development.
    """
    app_path = REPO_ROOT / "app.py"
    content = app_path.read_text()

    forbidden = ["WORKTREE", "- ACTIVE", "feat/272", "v272-FIXED"]
    for marker in forbidden:
        assert marker not in content, (
            f"app.py contains debug/worktree string {marker!r}. "
            "Clean it up before shipping."
        )


def test_hf_cache_security_lock():
    """Ensures hf_cache ownership has not been loosened (must remain root for security)."""
    containerfile_path = REPO_ROOT / "Containerfile"
    content = containerfile_path.read_text()
    
    # Ensure there is NO --chown=1001:1001 on the hf_cache line
    # Broken version: COPY --from=builder --chown=1001:1001 /app/hf_cache /app/hf_cache
    # Safe version: COPY --from=builder /app/hf_cache /app/hf_cache
    assert "--chown=1001:1001 /app/hf_cache" not in content, \
        "Security Breach: hf_cache MUST NOT be owned by the app user. Revert the chown to root."


def test_grievance_forms_exist_and_are_surfaced():
    """
    End-to-end structural test for the most common steward use-case:
    requesting grievance forms.

    Tests the full chain up to the LLM boundary:
      1. All 4 form PDFs exist on disk (so links don't silently 404)
      2. The Gradio download sidebar HTML contains all 4 forms
      3. Each sidebar link uses /gradio_api/file= (not a GitHub URL)

    Whether the LLM *chooses* to emit those links in its response is
    non-deterministic and is covered by the integration test suite instead.
    """
    import sys
    sys.path.insert(0, str(REPO_ROOT))
    import app  # noqa: PLC0415

    forms_dir = REPO_ROOT / "data" / "labour_law" / "forms"

    # 1. Every expected PDF must physically exist.
    for name in app._GRIEVANCE_FORM_NAMES:
        path = forms_dir / name
        assert path.exists(), (
            f"Grievance form PDF missing: {path}. "
            "A steward asking for forms would receive a broken link."
        )

    # 2. The sidebar HTML must list all 4 forms.
    html = app.build_pdf_download_links()
    assert html, "build_pdf_download_links() returned empty — no forms will appear in the UI."

    for name in app._GRIEVANCE_FORM_NAMES:
        label = name.removesuffix(".pdf")
        assert label in html, (
            f"'{label}' is missing from the download sidebar HTML. "
            "Stewards won't see this form in the Knowledge Base panel."
        )

    # 3. Every link in the sidebar must point to the Gradio endpoint, not GitHub.
    assert "/gradio_api/file=" in html, (
        "Sidebar links must use /gradio_api/file= so they resolve from the "
        "running app, not a remote URL that can go stale."
    )
    assert "github.com" not in html, (
        "Sidebar links must not point to github.com — use /gradio_api/file= instead."
    )


def test_ui_reviewer_label_not_hidden_on_mobile():
    """
    Ensures that style.css doesn't contain rules that explicitly hide the
    'Reviewer' label text on mobile (which was a previous bug).
    """
    css_path = REPO_ROOT / "style.css"
    content = css_path.read_text()

    # Look for the rule that explicitly hides the text span within the label
    # Example: #reviewer_toggle label span { display: none !important; }
    pattern = re.compile(r"#reviewer_toggle.*label\s*span\s*{[^}]*display:\s*none", re.MULTILINE | re.IGNORECASE)
    assert not pattern.search(content), (
        "style.css contains a rule that hides the 'Reviewer' label text on mobile. "
        "Remove any 'display: none' inside '#reviewer_toggle label span {}'."
    )


def test_ui_enter_key_handler_present():
    """
    The 'Enter to submit' behavior is a frequent regression point in Gradio 6.
    Ensures that the JavaScript keydown listener with 'Capture Phase' (true)
    is present in app.py.
    """
    app_path = REPO_ROOT / "app.py"
    content = app_path.read_text()

    # Look for the combination of Enter-check, preventDefault, and capture-phase 'true'
    assert "e.key === 'Enter'" in content, "The 'Enter' key listener appears to be missing from app.py."
    assert "e.preventDefault()" in content, "The Enter key handler is missing e.preventDefault() to block newlines."
    assert "}, true);" in content, (
        "The keydown listener is missing the 'true' (Capture Phase) argument. "
        "Without this, Gradio's internal handlers will swallow the 'Enter' key "
        "event and insert a newline instead of submitting."
    )


