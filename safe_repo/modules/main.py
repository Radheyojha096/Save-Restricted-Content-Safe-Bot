#safe_repo

import time
import asyncio
from pyrogram import filters, Client
from safe_repo import app
from config import API_ID, API_HASH
from safe_repo.core.get_func import get_msg
from safe_repo.core.func import *
from safe_repo.core.func import parse_telegram_link
from safe_repo.core.mongo import db, plans_db
from pyrogram.errors import FloodWait, SessionRevoked, AuthKeyDuplicated, AuthKeyUnregistered
from safe_repo.core import script
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)



@app.on_message(filters.regex(r'https?://[^\s]+') & ~filters.command("batch") & ~filters.reply)
async def single_link(_, message):
    user_id = message.chat.id
    lol = await chk_user(message, user_id)
    if lol == 1:
        return
    
    link = get_link(message.text) 
    
    userbot = None
    try:
        join = await subscribe(_, message)
        if join == 1:
            return
     
        msg = await message.reply("Processing...")
        data = await db.get_data(user_id)
        
        if data and data.get("session"):
            session = data.get("session")
            try:
                userbot = Client(":userbot:", api_id=API_ID, api_hash=API_HASH, session_string=session)
                await userbot.start()                
            except (SessionRevoked, AuthKeyDuplicated, AuthKeyUnregistered):
                return await msg.edit_text("Login expired /login again...")
            except Exception as e:
                logger.error(f"Session start error: {e}")
                return await msg.edit_text("Failed to start session. Please try again.")
        else:
            await msg.edit_text("Login in bot first ...")
            return

        try:
            # Invite links (t.me/+, telegram.me/+) -> join the chat
            if '/+' in link or 'joinchat/' in link:
                q = await userbot_join(userbot, link)
                await msg.edit_text(q)
            else:
                # Let get_msg handle all message/story/topic/bot links via the
                # robust parser. It will reply with a clear error if the link
                # cannot be parsed.
                await get_msg(userbot, user_id, msg.id, link, 0, message, False)
        except Exception as e:
            logger.error(f"Processing error: {e}")
            await msg.edit_text(f"Link: `{link}`\n\n**Error:** {str(e)}")
                     
    except FloodWait as fw:
        await msg.edit_text(f'Try again after {fw.x} seconds due to floodwait from telegram.')
    except Exception as e:
        logger.error(f"Main error: {e}")
        await app.send_message(user_id, f"Link: `{link}`\n\n**Error:** {str(e)}")
    finally:
        # Ensure userbot is properly disconnected
        if userbot:
            try:
                await userbot.stop()
            except:
                pass


users_loop = {}

@app.on_message(filters.command("settings"))
async def settings_command(_, message):
    from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    
    buttons = InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("Set Chat ID", callback_data='setchat'), InlineKeyboardButton("Set Rename Tag", callback_data='setrename')],
            [InlineKeyboardButton("Caption", callback_data='setcaption'), InlineKeyboardButton("Replace Words", callback_data='setreplacement')],
            [InlineKeyboardButton("Remove Words", callback_data='delete'), InlineKeyboardButton("Reset", callback_data='reset')],
            [InlineKeyboardButton("Login", callback_data='addsession'), InlineKeyboardButton("Logout", callback_data='logout')],
            [InlineKeyboardButton("Set Thumbnail", callback_data='setthumb'), InlineKeyboardButton("Remove Thumbnail", callback_data='remthumb')],
            [InlineKeyboardButton("Report Errors", url="https://t.me/safe_repo")]
        ]
    )
    
    await message.reply_text(
        text="Customize by your end and Configure your settings ...",
        reply_markup=buttons
    )


@app.on_message(filters.command("cmdhelp"))
async def cmd_help_command(_, message):
    await message.reply_text(text=script.CMD_HELP_TXT, disable_web_page_preview=True)


@app.on_message(filters.command("howtocopy"))
async def how_to_copy_command(_, message):
    copy_guide = """
🎯 **HOW TO COPY MEDIA USING THIS BOT** 🎯

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📋 **STEP BY STEP GUIDE:**

**1️⃣ LOGIN FIRST (REQUIRED):**
• Send: `/login`
• Follow the instructions to login with your session
• This allows bot to access your private channels

**2️⃣ COPY SINGLE MEDIA:**
• Just paste any Telegram link directly:
  📹 `https://t.me/channel_name/12345`
  🔒 `https://t.me/c/channel_id/12345`
  🤖 `https://t.me/b/bot_username/12345`

**3️⃣ COPY MULTIPLE MEDIA (BATCH):**
• Send: `/batch`
• Bot will ask for start link: `https://t.me/c/12345/100`
• Bot will ask for end link: `https://t.me/c/12345/105`
• Bot downloads messages 100-105 automatically

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🎬 **SUPPORTED CONTENT TYPES:**
• Videos (MP4, MKV, AVI, etc.)
• Photos & Images
• Documents (PDF, DOC, ZIP, etc.)
• Audio files
• Text messages
• Stickers & Animations

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

⚙️ **CUSTOMIZE YOUR OUTPUT:**
• Use `/settings` to configure:
  📝 Custom captions
  🖼️ Thumbnails
  📁 File renaming
  🎯 Target chat ID

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

💡 **TIPS FOR SUCCESS:**

✅ **For Private Channels:**
• Must be logged in with `/login`
• Your account must have access to the channel

✅ **For Public Channels:**
• Works without login
• Just paste the link directly

✅ **For Large Files:**
• Be patient, downloads may take time
• Premium users get faster processing

✅ **For Batch Processing:**
• Use `/cancel` to stop if needed
• Free users: max 100 messages
• Premium users: unlimited

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

❌ **COMMON ISSUES & SOLUTIONS:**

🔸 "Login expired" → Use `/login` again
🔸 "Have you joined the channel?" → Login with correct session
🔸 "Floodwait" → Wait for the specified time
🔸 "File too large" → Contact admin for help

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📞 **NEED HELP?**
Contact: @Radheyojha096

💝 **All copied media includes:**
"BY @Radheyojha096" credit

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🚀 **START NOW:**
1. Send `/login` to login
2. Send `/settings` to customize
3. Paste any media link to copy!

__**Powered by safe_repo**__
"""
    await message.reply_text(copy_guide, disable_web_page_preview=True)


@app.on_callback_query(filters.regex(r'^(setchat|setrename|setcaption|setreplacement|addsession|delete|logout|setthumb|reset|remthumb)$'))
async def callback_query_handler(_, callback_query):
    user_id = callback_query.from_user.id
    
    if callback_query.data == 'setchat':
        await callback_query.answer("Send me the ID of that chat:")
        # We'll need to implement session management for this
    elif callback_query.data == 'setrename':
        await callback_query.answer("Send me the rename tag:")
    elif callback_query.data == 'setcaption':
        await callback_query.answer("Send me the caption:")
    elif callback_query.data == 'setreplacement':
        await callback_query.answer("Send me the replacement words in the format: 'WORD(s)' 'REPLACEWORD'")
    elif callback_query.data == 'addsession':
        await callback_query.answer("This method is deprecated ... use /login")
    elif callback_query.data == 'delete':
        await callback_query.answer("Send words separated by space to delete them from caption/filename ...")
    elif callback_query.data == 'logout':
        from safe_repo.modules.login import delete_session_files
        files_deleted = await delete_session_files(user_id)
        if files_deleted:
            await callback_query.answer("Logged out and deleted session successfully.")
        else:
            await callback_query.answer("You are not logged in")
    elif callback_query.data == 'setthumb':
        await callback_query.answer('Please send the photo you want to set as the thumbnail.')
    elif callback_query.data == 'reset':
        try:
            # Clear delete words for this user
            from safe_repo.core.get_func import save_delete_words
            save_delete_words(user_id, set())
            await callback_query.answer("All words have been removed from your delete list.")
        except Exception as e:
            await callback_query.answer(f"Error clearing delete list: {e}")
    elif callback_query.data == 'remthumb':
        try:
            import os
            os.remove(f'{user_id}.jpg')
            await callback_query.answer('Thumbnail removed successfully!')
        except FileNotFoundError:
            await callback_query.answer("No thumbnail found to remove.")


@app.on_message(filters.command("batch"))
async def batch_link(_, message):
    user_id = message.chat.id    
    lol = await chk_user(message, user_id)
    if lol == 1:
        return    
    
    text = message.text.strip()
    parts = text.split()
    
    if len(parts) >= 3:
        start_link = parts[1]
        end_link = parts[2]
        start_id = get_link(start_link)
        if not start_id:
            await app.send_message(message.chat.id, "Invalid start link format. Please send a valid Telegram message link.")
            return
        last_id = get_link(end_link)
        if not last_id:
            await app.send_message(message.chat.id, "Invalid end link format. Please send a valid Telegram message link.")
            return
    else:
        start = await app.ask(message.chat.id, text="Please send the start link.")
        # Check if user sent a valid message with text
        if not start.text or not start.text.strip():
            await app.send_message(message.chat.id, "No link provided. Please send a valid Telegram message link.")
            return
        
        start_id = get_link(start.text)
        if not start_id:
            await app.send_message(message.chat.id, "Invalid start link format. Please send a valid Telegram message link.")
            return
            
        last = await app.ask(message.chat.id, text="Please send the end link.")
        # Check if user sent a valid message with text
        if not last.text or not last.text.strip():
            await app.send_message(message.chat.id, "No link provided. Please send a valid Telegram message link.")
            return
        
        last_id = get_link(last.text)
        if not last_id:
            await app.send_message(message.chat.id, "Invalid end link format. Please send a valid Telegram message link.")
            return
    
    # Extract message ID from start link (handle query parameters like ?single)
    s = start_id.split("/")[-1]
    if "?" in s:
        s = s.split("?")[0]
    try:
        cs = int(s)
    except ValueError:
        await app.send_message(message.chat.id, "Invalid start link format. Please send a valid Telegram message link.")
        return
    
    # Extract message ID from end link (handle query parameters like ?single)
    l = last_id.split("/")[-1]
    if "?" in l:
        l = l.split("?")[0]
    try:
        cl = int(l)
    except ValueError:
        await app.send_message(message.chat.id, "Invalid end link format. Please send a valid Telegram message link.")
        return

    # Calculate total media to process
    total_messages = cl - cs + 1
    await app.send_message(message.chat.id, f"Total messages to process: {total_messages}")

    # Check if user is premium before enforcing batch size limit
    is_premium = await plans_db.check_premium(user_id)
    if not is_premium and cl - cs > 100:
        await app.send_message(message.chat.id, "Only 100 messages allowed in batch size... Purchase premium to fly 💸")
        return
    
    userbot = None
    try:     
        data = await db.get_data(user_id)
        
        if data and data.get("session"):
            session = data.get("session")
            try:
                userbot = Client(":userbot:", api_id=API_ID, api_hash=API_HASH, session_string=session)
                await userbot.start()                
            except (SessionRevoked, AuthKeyDuplicated, AuthKeyUnregistered):
                return await app.send_message(message.chat.id, "Your login expired ... /login again")
            except Exception as e:
                logger.error(f"Session start error: {e}")
                return await app.send_message(message.chat.id, "Failed to start session. Please try again.")
        else:
            await app.send_message(message.chat.id, "Login in bot first ...")
            return

        try:
            users_loop[user_id] = True
            processed_count = 0
            
            for i in range(int(s), int(l) + 1):
                if user_id in users_loop and users_loop[user_id]:
                    remaining = total_messages - processed_count
                    msg = await app.send_message(message.chat.id, f"Processing! ({processed_count + 1}/{total_messages})\nRemaining: {remaining} messages")
                    try:
                        # Rebuild the link for batch iteration while preserving
                        # supergroup topic/thread context from the start link.
                        b_chat, b_start, b_thread, b_story = parse_telegram_link(start_id)
                        if b_story or b_chat is None:
                            url = start_id
                        elif b_thread is not None:
                            url = f"https://t.me/c/{b_chat}/{b_thread}/{i}" if isinstance(b_chat, int) else f"https://t.me/{b_chat}/{b_thread}/{i}"
                        else:
                            url = f"https://t.me/c/{b_chat}/{i}" if isinstance(b_chat, int) else f"https://t.me/{b_chat}/{i}"

                        # Process the message
                        await get_msg(userbot, user_id, msg.id, url, 0, message, True)
                        
                        # Increment processed count
                        processed_count += 1
                        sleep_msg = await app.send_message(message.chat.id, "Sleeping for 10 seconds to avoid flood...")
                        await asyncio.sleep(8)
                        await sleep_msg.delete()
                        await asyncio.sleep(2)                                                
                    except Exception as e:
                        logger.error(f"Error processing link {url}: {e}")
                        await app.send_message(message.chat.id, f"Error processing link {url}: {str(e)}")
                        continue
                else:
                    break
        except Exception as e:
            logger.error(f"Batch processing error: {e}")
            await app.send_message(message.chat.id, f"Error: {str(e)}")
                     
    except FloodWait as fw:
        await app.send_message(message.chat.id, f'Try again after {fw.x} seconds due to floodwait from Telegram.')
    except Exception as e:
        logger.error(f"Main batch error: {e}")
        await app.send_message(message.chat.id, f"Error: {str(e)}")
    finally:
        # Ensure userbot is properly disconnected
        if userbot:
            try:
                await userbot.stop()
            except:
                pass
        
        # Show completion message after batch processing
        if processed_count > 0:
            await app.send_message(message.chat.id, 
                f"✅ **Batch Processing Complete!**\n\n📦 Total files processed: {processed_count}\n\nPowered by Radhey Kishan Ojha clone\n📞 https://t.me/Radheyojha096\n\n__**Powered by safe_repo**__")


@app.on_message(filters.command("cancel"))
async def stop_batch(_, message):
    user_id = message.chat.id
    if user_id in users_loop:
        users_loop[user_id] = False
        await app.send_message(message.chat.id, "Batch processing stopped.")
    else:
        await app.send_message(message.chat.id, "No active batch processing to stop.")

