import asyncio
import sys
import logging
import os
import time
from gradio_client import Client

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("smoke-multi")

def test_target(url, name):
    """Sync wrapper for gradio_client calls which are blocking."""
    try:
        logger.info(f"[{name}] Connecting to {url}...")
        client = Client(url, verbose=False)
        
        logger.info(f"[{name}] Sending query: 'What is the nexus test?'")
        # chat_handler inputs: [message, history, persona]
        # persona is index 2, defaults to "Lookup"
        result = client.predict(
            "What is the nexus test?", 
            [], 
            "Lookup", 
            api_name="/chat_handler"
        )
        
        # Result structure: [chatbot_list, msg_val, submit_val, toolbox_val]
        # In Gradio 5.x+, chatbot output is a list of message dicts
        chatbot = result[0]
        if not chatbot:
            logger.error(f"[{name}] FAILURE: Chatbot history is empty.")
            return False
            
        last_msg = chatbot[-1]
        answer = last_msg.get("content", "")
        
        logger.info(f"[{name}] Received answer (length {len(answer)})")
        
        if len(answer) < 50:
            logger.error(f"[{name}] FAILURE: Answer too short. RAG might be failing.")
            return False
            
        logger.info(f"[{name}] SUCCESS: Environment verified.")
        return True
    except Exception as e:
        logger.error(f"[{name}] FAILURE: {e}")
        return False

async def main():
    targets = {
        "DEV": os.getenv("SMOKE_TARGET_DEV", "http://dev:7860"),
        "STAGING": os.getenv("SMOKE_TARGET_STAGING", "http://staging:7861")
    }
    
    # We run these in a threadpool to keep the async loop happy 
    # as gradio_client is primarily synchronous.
    loop = asyncio.get_event_loop()
    tasks = [
        loop.run_in_executor(None, test_target, url, name) 
        for name, url in targets.items()
    ]
    
    results = await asyncio.gather(*tasks)
    
    if all(results):
        print("\n🏆 GRAND SLAM SUCCESS: All environments verified!\n")
        sys.exit(0)
    else:
        print("\n❌ GRAND SLAM FAILURE: One or more environments failed.\n")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
