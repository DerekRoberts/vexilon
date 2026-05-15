# Tasks: Chainlit UI Overhaul

## Phase 1: Foundation & Cleanup
- [ ] **T1: Patch Decoupling**
  - Create `app/patches.py`.
  - Move all Python 3.14 compatibility patches from `app/main.py` to `app/patches.py`.
  - Import patches in `app/main.py`.
  - Verify app still starts on Python 3.14.

## Phase 2: Native UI Implementation
- [ ] **T2: Forensic Starters**
  - Update `set_starters` with high-impact forensic queries.
  - Add icons for each starter.
- [ ] **T3: Knowledge Base Sidebar**
  - Create a helper to generate Markdown links for the knowledge base.
  - Use `cl.on_chat_start` to send a `cl.Text` element displayed in the side panel.
- [ ] **T4: Action-Based Personas**
  - Create `cl.Action` buttons for personas.
  - Implement `@cl.action_callback` for persona switching.
  - Update welcome message to include these actions.

## Phase 3: PIPA & Export
- [ ] **T5: Export/Clear Actions**
  - Implement `export_history` action using `history_to_markdown`.
  - Implement `clear_session` action that resets session state and provides a fresh start.
- [ ] **T6: Final UI Polish**
  - Remove legacy `cl.ChatSettings` if the action-based persona switcher is preferred.
  - Standardize logging and error messages.

## Phase 4: Verification
- [ ] **V1: Development Smoke Test**
  - Run `podman compose up --build dev`.
  - Verify starters work.
  - Verify persona switching updates the system prompt.
  - Verify sidebar is persistent.
- [ ] **V2: Regression Test**
  - Run `pytest app/tests/test_rag_stream.py`.
