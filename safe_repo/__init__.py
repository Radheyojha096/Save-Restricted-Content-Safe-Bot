#safe_repo


import asyncio
import logging
from pyrogram import Client
from config import API_ID, API_HASH, BOT_TOKEN


loop = asyncio.get_event_loop()


logging.basicConfig(
    format="[%(levelname) 5s/%(asctime)s] %(name)s: %(message)s",
    level=logging.INFO,
)

# Ensure we only create one instance of the client
if not hasattr(__import__(__name__), 'app'):
    # Pyrogram client configuration optimized for maximum stability
    app = Client(
        ":RestrictBot:",
        api_id=API_ID,
        api_hash=API_HASH,
        bot_token=BOT_TOKEN,
        workers=10,  # Reduced from 20 to prevent resource exhaustion
        sleep_threshold=180,  # Reduced from 300s to 3 minutes for faster recovery
        max_concurrent_transmissions=1,  # Keep at 1 to prevent timeouts
        no_updates=False  # Ensure we receive all updates
    )

    # Initialize listeners attribute for pyromod compatibility
    from pyromod.listen.client import ListenerTypes
    app.listeners = {
        ListenerTypes.MESSAGE: [],
        ListenerTypes.CALLBACK_QUERY: []
    }


async def restrict_bot():
    global BOT_ID, BOT_NAME, BOT_USERNAME
    try:
        getme = await app.get_me()
        BOT_ID = getme.id
        BOT_USERNAME = getme.username
        if getme.last_name:
            BOT_NAME = getme.first_name + " " + getme.last_name
        else:
            BOT_NAME = getme.first_name
        logging.info(f"Bot initialized: {BOT_NAME} (@{BOT_USERNAME})")
    except Exception as e:
        logging.error(f"Bot initialization failed: {e}")
        raise e


