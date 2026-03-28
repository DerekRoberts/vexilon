"""
app.py — BCGEU Steward Assistant (Modular Version)
--------------------------------------------
Tech stack:
  - src.vexilon: Modular RAG components (loaders, vector store, manifest)
  - Gradio 6   : Web UI at http://localhost:7860
"""

import os
import json
import time
import datetime
import tempfile
import threading
import logging
from pathlib import Path
from collections.abc import AsyncIterator

from src.vexilon import config, utils, loader, vector, manifest, prompts, ui_styles

# ─── Initialization ───────────────────────────────────────────────────────────
_info = utils.get_vexilon_info()
VEXILON_VERSION = _info["ver"]
utils.print_banner(_info)

_rate_limiter = utils.RateLimiter(
    max_per_minute=config.RATE_LIMIT_PER_MINUTE,
    max_per_hour=config.RATE_LIMIT_PER_HOUR,
)

_test_registry = prompts.TestRegistry()

# Millhaven fallback (loaded once at startup, used if TestRegistry misses)
MILLHAVEN_FACTORS_PATH = Path("./prompts/millhaven_audit_criteria.txt")
MILLHAVEN_FACTORS = ""
if MILLHAVEN_FACTORS_PATH.is_file():
    MILLHAVEN_FACTORS = MILLHAVEN_FACTORS_PATH.read_text(encoding="utf-8")

OFF_DUTY_KEYWORDS = {
    "off-duty", "personal conduct", "nexus", "outside of work", "facebook",
    "reddit", "social media", "arrest", "charged", "personal life",
    "instagram", "twitter", "tiktok", "personal blog", "off-site",
}

# ─── Attribution HTML (needs VEXILON_VERSION at module level) ─────────────────
ATTRIBUTION_HTML = f"""
<div style='text-align: center; color: #6b7280; font-size: 0.85rem; margin-top: 1rem;'>
    <a href='https://github.com/DerekRoberts/vexilon' target='_blank' style='color: #005691; text-decoration: none;'>View code or contribute on GitHub</a>
    <span style='margin-left: 0.5rem; opacity: 0.7;'>•</span>
    <a href='https://github.com/DerekRoberts/vexilon/pkgs/container/vexilon' target='_blank' style='color: #005691; text-decoration: none;'>{VEXILON_VERSION}</a>
</div>
"""

# ─── Clients ─────────────────────────────────────────────────────────────────
_anthropic_client = None


def get_anthropic():
    global _anthropic_client
    if _anthropic_client is None:
        import anthropic
        _anthropic_client = anthropic.AsyncAnthropic()
    return _anthropic_client


# ─── RAG App State ────────────────────────────────────────────────────────────
_chunks: list[dict] = []
_index = None


def startup(force_rebuild: bool = False) -> None:
    """Initialise the vector index and load document chunks."""
    global _chunks, _index
    get_anthropic()
    print(f"[startup] Starting Vexilon {VEXILON_VERSION}…")

    # Hidden cache setup
    config.PDF_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    _test_registry.load(config.TESTS_DIR)

    if not force_rebuild:
        index, chunks = vector.load_precomputed_index()
        if index is not None and chunks is not None:
            _index, _chunks = index, chunks
            loader.get_embed_model()  # Warm model
            print("[startup] Ready.")
            return

    _index, _chunks = vector.build_index_from_sources(force=force_rebuild)
    print("[startup] Ready.")


# ─── RAG Query Logic ──────────────────────────────────────────────────────────
async def condense_query(message: str, history: list[dict]) -> str:
    """Condense history into a standalone search query."""
    if not history:
        return message
    client = get_anthropic()

    context_lines = []
    for turn in history[-config.CONDENSE_QUERY_HISTORY_TURNS:]:
        role = "User" if turn["role"] == "user" else "Assistant"
        raw_content = str(turn["content"])
        content = raw_content[:config.CONDENSE_QUERY_CONTENT_MAX_LEN] + (
            "..." if len(raw_content) > config.CONDENSE_QUERY_CONTENT_MAX_LEN else ""
        )
        context_lines.append(f"{role}: {content}")

    prompt = (
        "Rephrase user follow-up as a standalone search query based on history. "
        "Only provide query text.\n\n"
        f"History:\n{chr(10).join(context_lines)}\n\n"
        f"User: {message}"
    )

    try:
        response = await client.messages.create(
            model=config.CONDENSE_MODEL,
            max_tokens=100,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.content[0].text.strip().strip('"')
    except Exception as exc:
        print(f"[rag] Condense failed: {exc}")
        return message


async def rag_review_stream(
    message: str,
    history: list[dict],
    use_reviewer: bool = False,
    persona_mode: str = "Explorer",
) -> AsyncIterator[str]:
    """
    Retrieve relevant chunks, build the prompt, stream from Bot A (RAG),
    and optionally pass through Bot B (reviewer) for verification.
    """
    if _index is None:
        yield "⚠️ The index is not ready yet. Please wait a moment and try again."
        return

    # Rewrite query for RAG if there is history
    query = await condense_query(message, history)
    relevant_chunks = vector.search_index(_index, _chunks, query)

    # Build context block from retrieved chunks
    context_parts = []
    for chunk in relevant_chunks:
        context_parts.append(
            f"[Source: {chunk.get('source', 'Unknown')}, Page: {chunk['page']}]\n{chunk['text']}"
        )
    context = "\n\n---\n\n".join(context_parts)

    # Build message list for Claude: prior history + new user message
    messages = []
    for turn in history:
        if turn["role"] in ("user", "assistant"):
            messages.append({"role": turn["role"], "content": turn["content"]})
    messages.append({"role": "user", "content": message})

    client = get_anthropic()

    try:
        # 1. Resolve System Prompt based on Persona
        base_prompt = persona_mode if persona_mode != "Explore" else prompts.SYSTEM_PROMPT
        if base_prompt in ["Direct", "Defend"]:
            base_prompt = prompts.get_persona_prompt(base_prompt)

        formatted_prompt = base_prompt.format(
            manifest=manifest.get_knowledge_manifest(),
            verify_message=prompts.VERIFY_STEWARD_MESSAGE,
        )

        # 2. Audit Logic (Issue #161 Refactor)
        if persona_mode != "Explore":
            matched_tests = _test_registry.find_matches(message + " " + query)

            # New Registry Tests
            for test in matched_tests:
                formatted_prompt += f"\n\n--- MANDATORY LOGIC CHECK: {test.name.upper()} ---\n"
                formatted_prompt += f"This case involves potential {test.name}. You MUST audit the facts against these criteria:\n{test.content}\n"
                formatted_prompt += f"In your response, identify which factors in the {test.name} management HAS NOT PROVEN."

            # Legacy Millhaven Fallback (if registry doesn't catch it)
            if not matched_tests and MILLHAVEN_FACTORS:
                msg_lower = message.lower()
                query_lower = query.lower()
                is_off_duty = any(k in msg_lower or k in query_lower for k in OFF_DUTY_KEYWORDS)
                if is_off_duty:
                    formatted_prompt += "\n\n--- MANDATORY LOGIC CHECK: MILLHAVEN AUDIT ---\n"
                    formatted_prompt += f"This case involves potential off-duty conduct. You MUST audit the facts against these 5 factors:\n{MILLHAVEN_FACTORS}\n"
                    formatted_prompt += "In your response, identify which factors management HAS NOT PROVEN."

        # Bot A: Get raw RAG response
        raw_response = ""
        async with client.messages.stream(
            model=config.CLAUDE_MODEL,
            max_tokens=1024,
            system=[
                {
                    "type": "text",
                    "text": formatted_prompt,
                    "cache_control": {"type": "ephemeral"},
                },
                {
                    "type": "text",
                    "text": (
                        "--- AGREEMENT EXCERPTS ---\n\n"
                        + context
                        + "\n\n--- END EXCERPTS ---"
                    ),
                    "cache_control": {"type": "ephemeral"},
                },
            ],
            messages=messages,
        ) as stream:
            async for text_chunk in stream.text_stream:
                raw_response += text_chunk
                yield text_chunk
            final = await stream.get_final_message()
            usage = final.usage
            print(
                f"[rag] Tokens — input: {usage.input_tokens}, "
                f"output: {usage.output_tokens}"
            )

        # Automatic verification if enabled
        if config.VERIFY_ENABLED:
            verify_res = await verify_response(raw_response, context)
            if verify_res:
                yield f"\n\n---\n\n**🔍 Verification:**\n{verify_res}"

        # Bot B: Review the response if enabled
        if use_reviewer:
            yield "\n\n---\n\n**🔍 Senior Rep Review:**\n"
            async for review_chunk in review_stream(raw_response, query, context):
                yield review_chunk

    except Exception as exc:
        yield f"\n\n⚠️ API error: {exc}"


async def review_stream(raw_response: str, query: str, context: str) -> AsyncIterator[str]:
    client = get_anthropic()
    prompt = f"Review steward output.\nQUERY: {query}\nRESPONSE: {raw_response}\nCONTEXT: {context[:2000]}\n{prompts.REVIEWER_SYSTEM_PROMPT}"
    try:
        review_text = ""
        async with client.messages.stream(
            model=config.REVIEWER_MODEL,
            max_tokens=512,
            messages=[{"role": "user", "content": prompt}],
        ) as stream:
            async for chunk in stream.text_stream:
                review_text += chunk
                yield chunk
            final = await stream.get_final_message()

            # Parse score from response
            import re
            score = 5
            score_match = re.search(r"SCORE:\s*(\d+)", review_text, re.IGNORECASE)
            if score_match:
                score = int(score_match.group(1))

            # Log the review
            utils.log_review(query, raw_response, review_text, score)
            print(f"[review] Score: {score}/10 for query '{query[:20]}...'")
    except Exception as exc:
        yield f"⚠️ Review error: {exc}"


async def verify_response(response_text: str, context: str) -> str:
    """Verification Bot: Check claims against context."""
    if not config.VERIFY_ENABLED:
        return ""
    client = get_anthropic()
    prompt = f"Verify claims.\nCONTEXT: {context[:4000]}\nRESPONSE: {response_text}\n{prompts.VERIFIER_SYSTEM_PROMPT}"
    try:
        msg = await client.messages.create(
            model=config.VERIFY_MODEL,
            max_tokens=512,
            messages=[{"role": "user", "content": prompt}],
        )
        return msg.content[0].text
    except Exception as exc:
        print(f"[verify] Failed: {exc}")
        return f"⚠️ Verification unavailable: {exc}"


# ─── Export & Import ──────────────────────────────────────────────────────────
def history_to_markdown(history: list[dict]) -> str:
    """Convert chat history to a Markdown string."""
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    md = f"# Vexilon Conversation Export - {timestamp}\n\n"

    for turn in history:
        role = turn["role"].capitalize()
        content = turn["content"]
        if isinstance(content, list):
            text_parts = [
                part.get("text", "") if isinstance(part, dict) else str(part)
                for part in content
            ]
            content = "".join(text_parts)

        md += f"### {role}\n{content}\n\n"
    return md


def markdown_to_history(file_path: str) -> list[dict]:
    """Parse a Markdown conversation file back into a list of dicts."""
    with open(file_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    history = []
    current_role = None
    current_content = []

    for line in lines:
        new_role = None
        if line.startswith("### User"):
            new_role = "user"
        elif line.startswith("### Assistant"):
            new_role = "assistant"

        if new_role:
            if current_role:
                history.append(
                    {"role": current_role, "content": "\n".join(current_content).strip()}
                )
            current_role = new_role
            current_content = []
        elif current_role:
            current_content.append(line.rstrip("\n"))

    # Append the last turn
    if current_role:
        history.append(
            {"role": current_role, "content": "\n".join(current_content).strip()}
        )

    return history


# ─── Gradio UI ────────────────────────────────────────────────────────────────
def build_ui() -> "gr.Blocks":
    """Assemble and return the Gradio Blocks application."""
    import gradio as gr

    with gr.Blocks(title="Collective Agreement Explorer") as demo:
        # ── Header ────────────────────────────────────────────────────────────
        gr.Markdown("## BCGEU Steward Assistant")

        with gr.Accordion("Knowledge Base & Priority", open=False):
            gr.Markdown(
                "**The Collective Agreement and Primary Statutes** are our primary references. Anything else provides additional context."
            )
            # Use gr.HTML() to preserve clickable links (gr.Markdown sanitizes HTML)
            gr.HTML(manifest.build_pdf_download_links())
            gr.Markdown(
                f"[📁 Browse Knowledge Base on GitHub]({config.GITHUB_LABOUR_LAW_URL})"
            )

        # ── Disclaimer (persistent, non-dismissible) ──────────────────────────
        disclaimer_box = gr.HTML(ui_styles.DISCLAIMER_HTML)

        with gr.Row(visible=True) as chip_row:
            chip_btns = [gr.Button(q, size="sm") for q in ui_styles.EXAMPLE_QUESTIONS]

        # ── Chat interface ────────────────────────────────────────────────────
        chatbot = gr.Chatbot(
            height=480,
            buttons=["copy"],
            render_markdown=True,
            show_label=False,
        )

        # ── Reviewer Toggle & Management ──────────────────────────────────────
        with gr.Row(variant="compact", elem_classes="compact-row"):
            persona_selector = gr.Radio(
                choices=["Explore", "Direct", "Defend"],
                value="Explore",
                show_label=False,
                container=False,
                scale=3,
                elem_id="persona_selector",
            )
            reviewer_toggle = gr.Checkbox(
                label="Reviewer",
                value=config.USE_REVIEWER,
                container=False,
                scale=1,
                elem_id="reviewer_toggle",
            )
            export_btn = gr.DownloadButton("⬇️ Save", variant="secondary", size="sm", scale=1, elem_classes="sm-btn")
            import_btn = gr.UploadButton("⬆️ Load", file_types=[".md"], variant="secondary", size="sm", scale=1, elem_classes="sm-btn")

        # ── Input row ─────────────────────────────────────────────────────────
        with gr.Row():
            msg_input = gr.Textbox(
                placeholder="Ask about the collective agreement…",
                label="",
                lines=2,
                max_lines=6,
                scale=5,
                show_label=False,
                container=False,
            )
            send_btn = gr.Button("Send ➤", scale=1, variant="primary")

        # ── Submit handlers ───────────────────────────────────────────────────
        async def submit(
            message: str,
            history: list[dict],
            use_reviewer: bool,
            persona_mode: str,
            **kwargs,
        ) -> AsyncIterator[tuple[list[dict], str, dict, dict]]:
            import gradio as gr

            # 1. Identify Banner
            top_banner = ui_styles.DISCLAIMER_HTML
            if persona_mode == "Direct":
                top_banner = ui_styles.DIRECT_MODE_HTML
            elif persona_mode == "Defend":
                top_banner = ui_styles.CASE_BUILDER_HTML

            request = kwargs.get("request")
            hide = gr.update(visible=False)
            show = gr.update(visible=True)
            if not message.strip():
                yield history, "", show, gr.update()
                return

            user_id = request.client.host if request else "default"
            allowed, rate_msg = _rate_limiter.is_allowed(user_id)
            if not allowed:
                history = list(history) + [
                    {"role": "user", "content": message},
                    {"role": "assistant", "content": rate_msg},
                ]
                yield history, "", show, gr.update()
                return

            message, was_flagged = utils.sanitize_input(message)
            if was_flagged:
                yield (
                    history,
                    "Your input was flagged for security review. Please try a different question.",
                    show,
                    gr.update(),
                )
                return
            prior_history = list(history)
            # Append user turn; seed an empty assistant bubble for streaming.
            # Hide onboarding components on first message.
            history = prior_history + [
                {"role": "user", "content": message},
                {"role": "assistant", "content": ""},
            ]
            yield history, "", hide, gr.update(value=top_banner)
            # Stream tokens from RAG; accumulate into the assistant bubble
            accumulated = ""
            async for chunk in rag_review_stream(
                message, prior_history, use_reviewer, persona_mode
            ):
                accumulated += chunk
                history[-1]["content"] = accumulated
                yield history, "", hide, gr.update(value=top_banner)

        submit_inputs = [msg_input, chatbot, reviewer_toggle, persona_selector]
        submit_outputs = [chatbot, msg_input, chip_row, disclaimer_box]

        send_btn.click(fn=submit, inputs=submit_inputs, outputs=submit_outputs)
        msg_input.submit(fn=submit, inputs=submit_inputs, outputs=submit_outputs)

        # ── Chip click handlers — populate input and auto-submit ──────────────
        for chip in chip_btns:
            chip.click(
                fn=lambda q: q,
                inputs=[chip],
                outputs=[msg_input],
            ).then(
                fn=submit,
                inputs=submit_inputs,
                outputs=submit_outputs,
            )

        # ── Export/Import Handlers ───────────────────────────────────────────
        def handle_export(history):
            if not history:
                return None
            md_str = history_to_markdown(history)
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M")
            filename = f"vexilon_chat_{timestamp}.md"
            save_path = os.path.join(tempfile.gettempdir(), filename)
            with open(save_path, "w", encoding="utf-8") as f:
                f.write(md_str)
            threading.Timer(600, lambda: os.path.exists(save_path) and os.remove(save_path)).start()
            return save_path

        export_btn.click(fn=handle_export, inputs=[chatbot], outputs=[export_btn])

        def handle_import(file):
            if file is None:
                return gr.update()
            try:
                new_history = markdown_to_history(file.name)
                # Hide onboarding if history is restored
                return new_history, gr.update(visible=False)
            except Exception:
                logging.error("[ui] Import failed", exc_info=True)
                return gr.update(), gr.update()

        import_btn.upload(
            fn=handle_import, inputs=[import_btn], outputs=[chatbot, chip_row]
        )

        # ── Attribution Footer ────────────────────────────────────────────────
        gr.HTML(ATTRIBUTION_HTML)

    return demo


# ─── Entry Point ──────────────────────────────────────────────────────────────
if __name__ == "__main__":
    startup()
    build_ui().launch(
        server_name="0.0.0.0",
        server_port=7860,
        css=ui_styles.CUSTOM_CSS,
        allowed_paths=[config.LABOUR_LAW_DIR.absolute()],
    )
