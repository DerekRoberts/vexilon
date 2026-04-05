import os
import asyncio
import logging
from typing import Dict, List
import html

try:
    from telegram import Update, constants
    from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters
except ImportError:
    print("Error: python-telegram-bot not installed. Run 'pip install python-telegram-bot'")
    exit(1)

# Import our RAG logic from app.py
from app import startup, rag_stream, VEXILON_VERSION

# Logging setup
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# In-memory history: {chat_id: list of messages}
# In a production app, this should be a persistent database (e.g. SQLite or Redis).
chat_histories: Dict[int, List[Dict[str, str]]] = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the /start command."""
    user = update.effective_user
    welcome_text = (
        f"👋 <b>Welcome to Vexilon v{VEXILON_VERSION}</b>\n\n"
        "I am your BCGEU Steward Assistant. I can help you find information in the "
        "Collective Agreement and other labour law documents.\n\n"
        "<b>How to use:</b>\n"
        "Just ask me a question like:\n"
        "• <i>What are my overtime rights?</i>\n"
        "• <i>How long is the probationary period?</i>\n"
        "• <i>Can my schedule change without notice?</i>\n\n"
        "⚠️ <i>Note: This is for informational purposes only. Consult your BCGEU representative "
        "or a legal advisor as appropriate.</i>"
    )
    await update.message.reply_text(welcome_text, parse_mode=constants.ParseMode.HTML)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle incoming text messages and run RAG pipeline."""
    if not update.message or not update.message.text:
        return

    chat_id = update.effective_chat.id
    user_query = update.message.text

    # Initialize history if new
    if chat_id not in chat_histories:
        chat_histories[chat_id] = []

    history = chat_histories[chat_id]

    # Show typing indicator
    await context.bot.send_chat_action(chat_id=chat_id, action=constants.ChatAction.TYPING)

    # Placeholder for the streaming response
    placeholder_msg = await update.message.reply_text("🔍 <i>Searching knowledge base...</i>", parse_mode=constants.ParseMode.HTML)
    
    accumulated_text = ""
    last_update_time = asyncio.get_event_loop().time()
    update_interval = 1.0  # Update every 1 second to avoid Telegram rate limits
    
    try:
        # Run the RAG stream from app.py
        # rag_stream yields (text_chunk, context_blob)
        # The first yield usually contains the full 'context' after retrieval
        async for chunk, _ in rag_stream(user_query, history):
            accumulated_text += chunk
            
            # Periodically update the message to simulate streaming
            now = asyncio.get_event_loop().time()
            if now - last_update_time > update_interval and accumulated_text.strip():
                try:
                    await context.bot.edit_message_text(
                        chat_id=chat_id,
                        message_id=placeholder_msg.message_id,
                        text=accumulated_text + "...",
                        parse_mode=None # Use None for partial to avoid HTML tag breaks
                    )
                    last_update_time = now
                except Exception:
                    # Message might not have changed or other Telegram error
                    pass

        # Final update with full markdown formatting (converted to HTML)
        if not accumulated_text.strip():
            accumulated_text = "I'm sorry, I couldn't find any information relevant to your question in the documents."
        
        # Simple Markdown to HTML conversion for Telegram (subset support)
        # Telegram supports <b>, <i>, <code>, <pre>, <a>, etc.
        # RAG output usually has markdown blockquotes (> ) and bold (**).
        formatted_text = accumulated_text.replace("**", "<b>").replace("__", "<i>")
        # Handle blockquotes (simple replacement)
        lines = []
        for line in formatted_text.split("\n"):
            if line.strip().startswith(">"):
                lines.append("<i>" + line.strip().lstrip(">").strip() + "</i>")
            else:
                lines.append(line)
        formatted_text = "\n".join(lines)

        await context.bot.edit_message_text(
            chat_id=chat_id,
            message_id=placeholder_msg.message_id,
            text=formatted_text,
            parse_mode=constants.ParseMode.HTML
        )

        # Update history
        history.append({"role": "user", "content": user_query})
        history.append({"role": "assistant", "content": accumulated_text})
        
        # Keep history manageable (e.g., last 10 turns)
        if len(history) > 20:
            chat_histories[chat_id] = history[-20:]

    except Exception as e:
        logging.error(f"Error handling Telegram message: {e}", exc_info=True)
        await context.bot.edit_message_text(
            chat_id=chat_id,
            message_id=placeholder_msg.message_id,
            text=f"⚠️ <b>An error occurred:</b> {html.escape(str(e))}",
            parse_mode=constants.ParseMode.HTML
        )

if __name__ == '__main__':
    # Initialize RAG
    startup()

    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        print("❌ Error: TELEGRAM_BOT_TOKEN environment variable not set.")
        exit(1)

    application = ApplicationBuilder().token(token).build()
    
    start_handler = CommandHandler('start', start)
    msg_handler = MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message)
    
    application.add_handler(start_handler)
    application.add_handler(msg_handler)
    
    print(f"🚀 Vexilon Telegram Bot v{VEXILON_VERSION} started...")
    application.run_polling()
