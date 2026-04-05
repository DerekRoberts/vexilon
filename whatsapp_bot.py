import os
import asyncio
import logging
import html
from typing import Dict, List

try:
    from fastapi import FastAPI, Request, Form
    from fastapi.responses import Response
    from twilio.rest import Client
    from twilio.twiml.messaging_response import MessagingResponse
    import uvicorn
except ImportError:
    print("Error: fastapi, uvicorn, or twilio not installed. Run 'pip install fastapi uvicorn twilio'")
    exit(1)

# Import our RAG logic from app.py
from app import startup, rag_stream, VEXILON_VERSION

# Logging setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

# In-memory history: {phone_number: list of messages}
chat_histories: Dict[str, List[Dict[str, str]]] = {}

# Twilio Client (only used for async sends if needed)
account_sid = os.getenv("TWILIO_ACCOUNT_SID")
auth_token = os.getenv("TWILIO_AUTH_TOKEN")
twilio_from = os.getenv("TWILIO_WHATSAPP_FROM", "whatsapp:+14155238886") # Default Twilio sandbox
client = Client(account_sid, auth_token) if account_sid and auth_token else None

@app.post("/whatsapp")
async def whatsapp_webhook(
    Body: str = Form(...),
    From: str = Form(...)
):
    """Handle incoming WhatsApp messages from Twilio."""
    user_id = From # WhatsApp ID (phone number)
    user_query = Body
    
    logger.info(f"Received WhatsApp message from {user_id}: {user_query}")

    # Initialize history
    if user_id not in chat_histories:
        chat_histories[user_id] = []

    history = chat_histories[user_id]
    
    accumulated_text = ""
    try:
        # Run RAG (full response needed for WhatsApp as it doesn't stream well via TwiML)
        # For a truly responsive bot, we'd send an immediate "Thinking..." message
        # but Twilio/WhatsApp doesn't have a direct equivalent to Telegram's "typing" or async edits
        # as cleanly without the full messaging API permissions.
        async for chunk, _ in rag_stream(user_query, history):
            accumulated_text += chunk

        if not accumulated_text.strip():
            accumulated_text = "I'm sorry, I couldn't find any information relevant to your question in the documents."

        # Twilio Messaging Response (TwiML)
        # Note: WhatsApp supports simple Markdown (*bold*, _italic_, ~strikethrough~, ```code```)
        # but not blockquotes the same way as standard Markdown.
        # We'll just clean up the output slightly.
        formatted_text = accumulated_text.replace("### ", "*").replace("## ", "*")
        
        # WhatsApp doesn't like very long messages (over 1600 chars in some cases)
        # We'll truncate or split if needed, but for now just send.
        resp = MessagingResponse()
        msg = resp.message(formatted_text)
        
        # Update history
        history.append({"role": "user", "content": user_query})
        history.append({"role": "assistant", "content": accumulated_text})
        
        # Keep history manageable
        if len(history) > 20:
            chat_histories[user_id] = history[-20:]
            
        return Response(content=str(resp), media_type="application/xml")

    except Exception as e:
        logger.error(f"Error handling WhatsApp message: {e}", exc_info=True)
        resp = MessagingResponse()
        resp.message(f"⚠️ An error occurred: {str(e)}")
        return Response(content=str(resp), media_type="application/xml")

@app.on_event("startup")
async def on_startup():
    """Run Vexilon RAG startup on server boot."""
    startup()
    logger.info(f"🚀 Vexilon WhatsApp Service v{VEXILON_VERSION} started...")

if __name__ == "__main__":
    port = int(os.getenv("WHATSAPP_PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)
