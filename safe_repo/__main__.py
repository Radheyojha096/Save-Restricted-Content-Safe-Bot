#safe_repo

import asyncio
import importlib
import logging
from aiojobs import create_scheduler
from pyrogram import idle
from safe_repo.modules import ALL_MODULES
from safe_repo.core.mongo.plans_db import check_and_remove_expired_users

# Fix Pyrogram channel ID limitation
import pyrogram.utils
pyrogram.utils.MIN_CHANNEL_ID = -1009999999999

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

loop = asyncio.get_event_loop()

async def keep_alive_task():
    """Background task to keep the bot alive and prevent sleep mode"""
    logger.info("Keep-alive task started")
    while True:
        try:
            # Simple ping to keep the session active
            logger.debug("Bot is alive and responding")
            await asyncio.sleep(60)  # Ping every 60 seconds
        except Exception as e:
            logger.error(f"Keep-alive task error: {e}")
            await asyncio.sleep(30)

async def schedule_expiry_check():
    scheduler = await create_scheduler()
    while True:
        try:
            await scheduler.spawn(check_and_remove_expired_users())
        except Exception as e:
            logger.error(f"Error in expiry check: {e}")
        await asyncio.sleep(3600)  # Check every hour

import sys

import asyncio
from safe_repo.core.get_func import send_alert
from config import CLONE_LOG_CHANNEL

async def safe_repo_boot():
    try:
        logger.info(f"Importing {len(ALL_MODULES)} modules...")
        # Track imported modules and prevent re-importing
        for all_module in ALL_MODULES:
            module_name = f"safe_repo.modules.{all_module}"
            if module_name not in sys.modules:
                logger.info(f"Importing module: {all_module}")
                importlib.import_module(module_name)
            else:
                logger.debug(f"Module already imported: {all_module}")
        logger.info("»»»» ʙᴏᴛ ᴅᴇᴘʟᴏʏ sᴜᴄᴄᴇssғᴜʟʟʏ ✨ 🎉")

        # Start background tasks
        asyncio.create_task(schedule_expiry_check())
        asyncio.create_task(keep_alive_task())

        # Start the Pyrogram client
        # Handle 409 Conflict: if another instance is logged in with the same
        # bot token, Telegram rejects the new login. We terminate the other
        # session(s) and retry so the bot can recover without manual restart.
        from safe_repo import app
        try:
            await app.start()
        except Exception as e:
            err = str(e)
            logger.error(f"Bot start failed: {err}")
            if "409" in err or "Conflict" in err or "TERMINATED" in err.upper():
                logger.warning("409 Conflict detected - terminating other sessions and retrying...")
                try:
                    await app.terminate()
                except Exception:
                    pass
                await asyncio.sleep(3)
                await app.start()
            else:
                raise
        logger.info("Bot client started successfully")
        
        # Send bot start notification
        try:
            await app.send_message(
                chat_id=CLONE_LOG_CHANNEL,
                text="🤖 **BOT STARTED**\n✅ Bot is now online and operational\n⏰ Time: " + __import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M:%S') + "\n\nBy Radhey Kishan Ojha\n📞 https://t.me/Radheyojha096"
            )
        except Exception as e:
            logger.error(f"Failed to send bot start notification: {e}")
        
        await idle()
        logger.info("»» ɢᴏᴏᴅ ʙʏᴇ ! sᴛᴏᴘᴘɪɴɢ ʙᴏᴛ.")
        
        # Send bot stop notification
        try:
            from safe_repo import app
            await app.send_message(
                chat_id=CLONE_LOG_CHANNEL,
                text="🛑 **BOT STOPPED**\n⚠️ Bot has been stopped\n⏰ Time: " + __import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M:%S') + "\n\nBy Radhey Kishan Ojha\n📞 https://t.me/Radheyojha096"
            )
        except Exception as e:
            logger.error(f"Failed to send bot stop notification: {e}")
        
        await app.stop()
    except Exception as e:
        logger.error(f"Error in bot boot: {e}")
        # Attempt to restart the bot after 5 seconds
        logger.info("Attempting to restart bot in 5 seconds...")
        await asyncio.sleep(5)
        # Instead of recursive call, just stop and let the outer loop restart
        try:
            from safe_repo import app
            await app.stop()
        except:
            pass
        raise

if __name__ == "__main__":
    try:
        loop.run_until_complete(safe_repo_boot())
    except Exception as e:
        logger.error(f"Critical error: {e}")
        logger.info("Bot will not restart automatically to prevent duplicate handlers")
    logger.info("Bot process completed")
