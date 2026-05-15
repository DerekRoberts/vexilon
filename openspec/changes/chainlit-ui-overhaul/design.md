# Design: Chainlit UI Overhaul

## Architecture Overview
The UI will be restructured to leverage Chainlit's native sidebar and action system. This reduces reliance on the "Gear" menu for core functionality and brings forensic tools to the forefront.

## UI Components

### 1. Forensic Sidebar (Knowledge Base)
- **Implementation**: `cl.Text(name="Knowledge Base", content=markdown_links, display="side")`.
- **Content**: A dynamically generated list of links to the PDF documents in `app/data/labour_law`.
- **Behavior**: Persistent in the side panel, allowing stewards to quickly reference the source material.

### 2. Persona Switcher
- **Implementation**: A dedicated `cl.Message` sent on `@cl.on_chat_start` with `cl.Action` buttons for each persona (Lookup, Grieve, Audit, Manage).
- **Callback**: `@cl.action_callback` will update the `cl.user_session["persona"]` and provide immediate visual feedback.
- **Benefit**: Reduces persona switching from 3 clicks (Gear -> Select -> Update) to 1 click.

### 3. Forensic Starters
- **Updated Starters**:
    - **"Discipline Analysis"**: `Analyze Article 14 (Discipline) requirements.`
    - **"Grievance Builder"**: `Help me build a grievance for a member.`
    - **"Policy Search"**: `Search for policies on [Topic].`
- **Iconography**: Use consistent SVG icons for a "premium" feel.

### 4. PIPA Actions (Ephemeral Control)
- **Export**: A `cl.Action(name="export_history", label="📤 Export Session")` button.
- **Clear**: A `cl.Action(name="clear_session", label="🗑️ Clear Session")` button.
- **Security**: These ensure that even though sessions are ephemeral, users have explicit control over their data lifecycle.

## Python 3.14 Compatibility Layer
- All patches in `app/main.py` will be moved to a dedicated `app/patches.py` to keep `main.py` focused on UI and RAG logic.
- This improves maintainability and makes it easier to track when these patches can be retired (e.g., when AnyIO/Chainlit release official 3.14 support).

## Data Flow
1. User interacts with Starters or Persona actions.
2. `cl.user_session` state is updated.
3. `on_message` uses the current session state to route to the appropriate RAG persona logic.
4. `rag_review_stream` generates the response with citations.
5. Inline file chips (`cl.File`) are provided for the specific documents cited.
