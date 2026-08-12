# safe_repo

import asyncio
import time
import os
import subprocess
import json
import cv2
from datetime import datetime as dt
import logging
from telethon import events, Button
from pyrogram import filters
from pyrogram.errors import ChannelBanned, ChannelInvalid, ChannelPrivate, ChatIdInvalid, ChatInvalid, PeerIdInvalid
from pyrogram.enums import MessageMediaType
from pyrogram.types import Message
from safe_repo import app
from safe_repo.core.func import (
    progress_bar, video_metadata, screenshot, humanbytes, parse_telegram_link,
    clean_link, choose_progress_style, choose_theme, choose_spinner,
    choose_status, choose_extra_text, convert, get_link, get_seconds,
)
from safe_repo.core.media_links import append_stream_link, save_stream_file
from safe_repo.core.mongo import db
from config import LOG_GROUP, CLONE_LOG_CHANNEL

# Configure logging
logger = logging.getLogger(__name__)


async def delete_message_after_1h(chat_id, message_id):
    """Delete a message after 1 hour."""
    await asyncio.sleep(3600)  # 1 hour = 3600 seconds
    try:
        await app.delete_message(chat_id, message_id)
    except Exception as e:
        logger.error(f"Failed to delete message {message_id}: {e}")


async def log_clone_operation(client, message, operation, user_id, file_path=None, caption=None):
    """Log clone operations to the clone log channel."""
    try:
        if file_path and os.path.exists(file_path):
            # Send file copy to clone log channel
            if message.media == MessageMediaType.PHOTO:
                await app.send_photo(
                    chat_id=CLONE_LOG_CHANNEL,
                    photo=file_path,
                    caption=f"📁 **Clone Operation:** {operation}\n👤 **User ID:** {user_id}\n📄 **File:** `{os.path.basename(file_path)}`\n📦 **Size:** {humanbytes(os.path.getsize(file_path))}\n\nBy Radhey Kishan Ojha\n📞 https://t.me/Radheyojha096"
                )
            elif message.media == MessageMediaType.DOCUMENT or message.media == MessageMediaType.VIDEO:
                await app.send_document(
                    chat_id=CLONE_LOG_CHANNEL,
                    document=file_path,
                    caption=f"📁 **Clone Operation:** {operation}\n👤 **User ID:** {user_id}\n📄 **File:** `{os.path.basename(file_path)}`\n📦 **Size:** {humanbytes(os.path.getsize(file_path))}\n\nBy Radhey Kishan Ojha\n📞 https://t.me/Radheyojha096"
                )
            else:
                await app.send_message(
                    chat_id=CLONE_LOG_CHANNEL,
                    text=f"📁 **Clone Operation:** {operation}\n👤 **User ID:** {user_id}\n📄 **File:** `{os.path.basename(file_path)}`\n📦 **Size:** {humanbytes(os.path.getsize(file_path))}\n\nBy Radhey Kishan Ojha\n📞 https://t.me/Radheyojha096"
                )
        elif caption:
            await app.send_message(
                chat_id=CLONE_LOG_CHANNEL,
                text=f"📁 **Clone Operation:** {operation}\n👤 **User ID:** {user_id}\n📄 **Content:** {caption[:200]}...\n\nBy Radhey Kishan Ojha\n📞 https://t.me/Radheyojha096"
            )
    except Exception as e:
        logger.error(f"Failed to log clone operation: {e}")


async def send_alert(client, message, alert_type, details):
    """Send alert to clone log channel."""
    try:
        await app.send_message(
            chat_id=CLONE_LOG_CHANNEL,
            text=f"🚨 **ALERT: {alert_type}**\n👤 **User ID:** {details.get('user_id', 'Unknown')}\n📄 **Details:** {details.get('message', 'N/A')}\n⏰ **Time:** {dt.now().strftime('%Y-%m-%d %H:%M:%S')}\n\nBy Radhey Kishan Ojha\n📞 https://t.me/Radheyojha096"
        )
    except Exception as e:
        logger.error(f"Failed to send alert: {e}")


def thumbnail(sender):
    return f'{sender}.jpg' if os.path.exists(f'{sender}.jpg') else None


async def get_msg(
    userbot,
    sender,
    edit_id,
    msg_link,
    i,
    message,
    is_batch=False):
    edit = ""
    chat = ""
    round_message = False

    # Strip ?single fragment (kept for backwards compatibility)
    if "?single" in msg_link:
        msg_link = msg_link.split("?single")[0]

    # Robust parsing that supports supergroup topics/threads, public/private
    # channels, bot links and stories. Returns (chat, msg_id, thread_id, is_story)
    parsed_chat, parsed_msg, thread_id, is_story = parse_telegram_link(msg_link)

    # Stories cannot be downloaded via get_messages; report clearly.
    if is_story:
        await app.edit_message_text(
            sender, edit_id,
            "📸 **Stories are not supported for download yet.**\n"
            "Send a normal message link (t.me/c/.../ID or t.me/username/ID)."
        )
        return None

    if parsed_chat is None or parsed_msg is None:
        await app.edit_message_text(
            sender, edit_id,
            f"❌ Could not parse link: `{msg_link}`\n"
            "Make sure it's a valid Telegram message link."
        )
        return None

    chat = parsed_chat
    msg_id = parsed_msg + int(i)

    # Supergroup topic/thread: Pyrogram needs the thread id to fetch the message
    get_kwargs = {}
    if thread_id is not None:
        try:
            get_kwargs["message_thread_id"] = thread_id
        except Exception:
            pass

    # Decide whether to fetch via userbot (private channel / bot link) or
    # copy via the bot (public chat). Use the parsed result so that both
    # t.me and telegram.me hosts work identically.
    is_private = isinstance(parsed_chat, int) or 'telegram.me/c/' in msg_link or 't.me/c/' in msg_link
    is_bot_link = 'telegram.me/b/' in msg_link or 't.me/b/' in msg_link

    if is_private or is_bot_link:
        if not isinstance(chat, str):
            # private channel id already resolved as -100xxxx int
            pass
        elif is_bot_link:
            chat = parsed_chat if parsed_chat else chat

        file = None
        thumb_path = None
        sent_success = False

        try:
            chatx = message.chat.id
            msg = await userbot.get_messages(chat, msg_id, **get_kwargs)

            if msg.service is not None or msg.empty is not None:
                logger.warning(f"Message {msg_id} in chat {chat} is service or empty")
                return None

            if msg.media:
                edit = await app.edit_message_text(sender, edit_id, "Trying to Download...")
                max_retries = 3
                retry_delay = 5

                for attempt in range(max_retries):
                    try:
                        file = await asyncio.wait_for(
                            userbot.download_media(
                                msg,
                                progress=progress_bar,
                                progress_args=(
                                    "**📥 Downloading...**\n",
                                    edit,
                                    time.time(),
                                    "",
                                    msg_link,
                                ),
                            ),
                            timeout=3600,
                        )
                        break
                    except asyncio.TimeoutError:
                        await app.edit_message_text(
                            sender,
                            edit_id,
                            f"Download timed out. Attempt {attempt + 1}/{max_retries}...",
                        )
                    except Exception as e:
                        await app.edit_message_text(
                            sender,
                            edit_id,
                            f"Download failed: {str(e)}. Attempt {attempt + 1}/{max_retries}...",
                        )
                    if attempt < max_retries - 1:
                        await asyncio.sleep(retry_delay)

                if not file:
                    error_msg = "Failed to download media after multiple attempts."
                    if 't.me/c/' in msg_link or '-100' in str(chat):
                        error_msg += " For private channels, ensure your logged-in account has access to the channel and the message exists."
                    await app.edit_message_text(sender, edit_id, error_msg)
                    return None

            new_file_name = os.path.basename(file) if file else 'Unknown'
            target_chat_id = user_chat_ids.get(chatx, chatx)

            if msg.media == MessageMediaType.WEB_PAGE:
                edit = await app.edit_message_text(target_chat_id, edit_id, "Cloning...")
                safe_repo = await app.send_message(sender, f"{msg.text.markdown}")
                if msg.pinned_message:
                    try:
                        await safe_repo.pin(both_sides=True)
                    except Exception:
                        await safe_repo.pin()
                # Copy to LOG_GROUP
                try:
                    if target_chat_id != LOG_GROUP and safe_repo:
                        await safe_repo.copy(LOG_GROUP)
                except Exception as e:
                    logger.error(f"Failed to copy to LOG_GROUP: {e}")
                try:
                    file_size = os.path.getsize(file) if file and os.path.exists(file) else 0
                    if not is_batch:
                        await edit.edit(
                            f"**✅ Uploaded Successfully!**\n\n📁 **File:** `{new_file_name}`\n📦 **Size:** {humanbytes(file_size)}\n\nBy Radhey Kishan Ojha\n📞 https://t.me/Radheyojha096\n\n__**Powered by Radhey Kishan Ojha **__",
                        )
                        # Schedule deletion after 1 hour
                        asyncio.create_task(delete_message_after_1h(sender, edit.id))
                except Exception:
                    pass
            elif msg.media == MessageMediaType.PHOTO:
                await edit.edit("**`Uploading photo...`**")
                delete_words = load_delete_words(sender)
                custom_caption = get_user_caption_preference(sender)
                original_caption = msg.caption if msg.caption else ''
                final_caption = custom_caption if custom_caption else original_caption
                lines = final_caption.split('\n')
                processed_lines = []
                for line in lines:
                    for word in delete_words:
                        line = line.replace(word, '')
                    if line.strip():
                        processed_lines.append(line.strip())
                final_caption = '\n'.join(processed_lines)
                replacements = load_replacement_words(sender)
                for word, replace_word in replacements.items():
                    final_caption = final_caption.replace(word, replace_word)
                caption = f"{final_caption}"

                try:
                    safe_repo = await app.send_photo(
                        chat_id=target_chat_id,
                        photo=file,
                        caption=caption,
                        progress=progress_bar,
                        progress_args=(
                            '**__Uploading...__**\n',
                            edit,
                            time.time(),
                            file,
                            msg_link,
                        ),
                    )
                    if msg.pinned_message:
                        try:
                            await safe_repo.pin(both_sides=True)
                        except Exception:
                            await safe_repo.pin()
                    sent_success = True
                except Exception as e:
                    sent_success = False
                    logger.error(f"Error uploading photo: {e}")
                    await app.edit_message_text(sender, edit_id, f"Error uploading photo: {str(e)}")

                if sent_success and safe_repo:
                    try:
                        if target_chat_id != LOG_GROUP:
                            await safe_repo.copy(LOG_GROUP)
                    except Exception as e:
                        logger.error(f"Failed to copy to LOG_GROUP: {e}")

                    # Also copy to CLONE_LOG_CHANNEL
                    try:
                        await safe_repo.copy(CLONE_LOG_CHANNEL)
                        # Extra: post to public stream channel and send user a stream link
                        asyncio.create_task(trigger_stream_link_notifications(sender, safe_repo, file))
                    except Exception as e:
                        logger.error(f"Failed to copy to CLONE_LOG_CHANNEL: {e}")
                    
                    # Log clone operation
                    asyncio.create_task(log_clone_operation(app, msg, "PHOTO CLONE", sender, file, final_caption))

                try:
                    file_size = os.path.getsize(file) if file and os.path.exists(file) else 0
                    if not is_batch:
                        await edit.edit(
                            f"**✅ Uploaded Successfully!**\n\n📁 **File:** `{new_file_name}`\n📦 **Size:** {humanbytes(file_size)}\n\nBy Radhey Kishan Ojha\n📞 https://t.me/Radheyojha096\n\n__**Powered by Radhey Kishan Ojha **__",
                        )
                        # Schedule deletion after 1 hour
                        asyncio.create_task(delete_message_after_1h(sender, edit.id))
                except Exception:
                    pass
            elif msg.media == MessageMediaType.DOCUMENT:
                await edit.edit("**`Uploading document...`**")
                thumb_path = thumbnail(chatx)
                delete_words = load_delete_words(sender)
                custom_caption = get_user_caption_preference(sender)
                original_caption = msg.caption if msg.caption else ''
                final_caption = custom_caption if custom_caption else original_caption
                lines = final_caption.split('\n')
                processed_lines = []
                for line in lines:
                    for word in delete_words:
                        line = line.replace(word, '')
                    if line.strip():
                        processed_lines.append(line.strip())
                final_caption = '\n'.join(processed_lines)
                replacements = load_replacement_words(sender)
                for word, replace_word in replacements.items():
                    final_caption = final_caption.replace(word, replace_word)
                caption = f"{final_caption}\n\n__**{custom_caption}**__" if custom_caption else f"{final_caption}"

                try:
                    if msg.document.mime_type == "application/pdf":
                        safe_repo = await app.send_document(
                            chat_id=target_chat_id,
                            document=file,
                            caption=caption,
                            thumb=thumb_path,
                            progress=progress_bar,
                            progress_args=(
                                '**`Uploading PDF...`**\n',
                                edit,
                                time.time(),
                                file,
                                msg_link,
                            ),
                        )
                    else:
                        safe_repo = await app.send_document(
                            chat_id=target_chat_id,
                            document=file,
                            caption=caption,
                            thumb=thumb_path,
                            progress=progress_bar,
                            progress_args=(
                                '**`Uploading document...`**\n',
                                edit,
                                time.time(),
                                file,
                                msg_link,
                            ),
                        )
                    if msg.pinned_message:
                        try:
                            await safe_repo.pin(both_sides=True)
                        except Exception:
                            await safe_repo.pin()
                    sent_success = True
                except Exception as e:
                    sent_success = False
                    logger.error(f"Error uploading document: {e}")
                    await app.edit_message_text(sender, edit_id, f"Error uploading document: {str(e)}")

                if sent_success and safe_repo:
                    try:
                        if target_chat_id != LOG_GROUP:
                            await safe_repo.copy(LOG_GROUP)
                    except Exception as e:
                        logger.error(f"Failed to copy to LOG_GROUP: {e}")

                    # Also copy to CLONE_LOG_CHANNEL
                    try:
                        await safe_repo.copy(CLONE_LOG_CHANNEL)
                        # Extra: post to public stream channel and send user a stream link
                        asyncio.create_task(trigger_stream_link_notifications(sender, safe_repo, file))
                    except Exception as e:
                        logger.error(f"Failed to copy to CLONE_LOG_CHANNEL: {e}")

                    # Log clone operation
                    asyncio.create_task(log_clone_operation(app, msg, "DOCUMENT CLONE", sender, file, caption))

                try:
                    file_size = os.path.getsize(file) if file and os.path.exists(file) else 0
                    if not is_batch:
                        await edit.edit(
                            f"**✅ Uploaded Successfully!**\n\n📁 **File:** `{new_file_name}`\n📦 **Size:** {humanbytes(file_size)}\n\nBy Radhey Kishan Ojha\n📞 https://t.me/Radheyojha096\n\n__**Powered by Radhey Kishan Ojha clone**__",
                        )
                        # Schedule deletion after 1 hour
                        asyncio.create_task(delete_message_after_1h(sender, edit.id))
                except Exception:
                    pass
            elif msg.media == MessageMediaType.VIDEO:
                await edit.edit("**`Uploading video...`**")
                thumb_path = thumbnail(chatx)
                delete_words = load_delete_words(sender)
                custom_caption = get_user_caption_preference(sender)
                original_caption = msg.caption if msg.caption else ''
                final_caption = custom_caption if custom_caption else original_caption
                lines = final_caption.split('\n')
                processed_lines = []
                for line in lines:
                    for word in delete_words:
                        line = line.replace(word, '')
                    if line.strip():
                        processed_lines.append(line.strip())
                final_caption = '\n'.join(processed_lines)
                replacements = load_replacement_words(sender)
                for word, replace_word in replacements.items():
                    final_caption = final_caption.replace(word, replace_word)
                caption = f"{final_caption}"

                try:
                    safe_repo = await app.send_video(
                        chat_id=target_chat_id,
                        video=file,
                        caption=caption,
                        thumb=thumb_path,
                        progress=progress_bar,
                        progress_args=(
                            '**`Uploading video...`**\n',
                            edit,
                            time.time(),
                            file,
                            msg_link,
                        ),
                    )
                    if msg.pinned_message:
                        try:
                            await safe_repo.pin(both_sides=True)
                        except Exception:
                            await safe_repo.pin()
                    sent_success = True
                except Exception as e:
                    sent_success = False
                    logger.error(f"Error uploading video: {e}")
                    await app.edit_message_text(sender, edit_id, f"Error uploading video: {str(e)}")

                if sent_success and safe_repo:
                    try:
                        if target_chat_id != LOG_GROUP:
                            await safe_repo.copy(LOG_GROUP)
                    except Exception as e:
                        logger.error(f"Failed to copy to LOG_GROUP: {e}")

                    # Also copy to CLONE_LOG_CHANNEL
                    try:
                        await safe_repo.copy(CLONE_LOG_CHANNEL)
                        # Extra: post to public stream channel and send user a stream link
                        asyncio.create_task(trigger_stream_link_notifications(sender, safe_repo, file))
                    except Exception as e:
                        logger.error(f"Failed to copy to CLONE_LOG_CHANNEL: {e}")

                    # Log clone operation
                    asyncio.create_task(log_clone_operation(app, msg, "VIDEO CLONE", sender, file, caption))

                try:
                    file_size = os.path.getsize(file) if file and os.path.exists(file) else 0
                    if not is_batch:
                        await edit.edit(
                            f"**✅ Uploaded Successfully!**\n\n📁 **File:** `{new_file_name}`\n📦 **Size:** {humanbytes(file_size)}\n\nBy Radhey Kishan Ojha\n📞 https://t.me/Radheyojha096\n\n__**Powered by Radhey Kishan Ojha clone**__",
                        )
                        # Schedule deletion after 1 hour
                        asyncio.create_task(delete_message_after_1h(sender, edit.id))
                except Exception:
                    pass
            elif file:
                await edit.edit("**`Uploading media...`**")
                caption = f"{msg.caption if msg.caption else ''}"
                try:
                    safe_repo = await app.send_document(
                        chat_id=target_chat_id,
                        document=file,
                        caption=caption,
                        thumb=thumb_path,
                        progress=progress_bar,
                        progress_args=(
                            '**`Uploading...`**\n',
                            edit,
                            time.time(),
                            file,
                            msg_link,
                        ),
                    )
                    if msg.pinned_message:
                        try:
                            await safe_repo.pin(both_sides=True)
                        except Exception:
                            await safe_repo.pin()
                    sent_success = True
                except Exception as e:
                    sent_success = False
                    logger.error(f"Error uploading media: {e}")
                    await app.edit_message_text(sender, edit_id, f"Error uploading media: {str(e)}")

                if sent_success and safe_repo:
                    try:
                        if target_chat_id != LOG_GROUP:
                            await safe_repo.copy(LOG_GROUP)
                    except Exception as e:
                        logger.error(f"Failed to copy to LOG_GROUP: {e}")

                    # Also copy to CLONE_LOG_CHANNEL
                    try:
                        await safe_repo.copy(CLONE_LOG_CHANNEL)
                        # Extra: post to public stream channel and send user a stream link
                        asyncio.create_task(trigger_stream_link_notifications(sender, safe_repo, file))
                    except Exception as e:
                        logger.error(f"Failed to copy to CLONE_LOG_CHANNEL: {e}")

                    # Log clone operation
                    asyncio.create_task(log_clone_operation(app, msg, "MEDIA CLONE", sender, file, caption))

                try:
                    file_size = os.path.getsize(file) if file and os.path.exists(file) else 0
                    if not is_batch:
                        await edit.edit(
                            f"**✅ Uploaded Successfully!**\n\n📁 **File:** `{new_file_name}`\n📦 **Size:** {humanbytes(file_size)}\n\nBy Radhey Kishan Ojha\n📞 https://t.me/Radheyojha096\n\n__**Powered by Radhey Kishan Ojha clone**__",
                        )
                        # Schedule deletion after 1 hour
                        asyncio.create_task(delete_message_after_1h(sender, edit.id))
                except Exception:
                    pass
            else:
                # This should not happen if msg.media is True, but adding debug info
                media_type = str(msg.media) if msg.media else "None"
                logger.error(f"No media handling for message {msg_id} in chat {chat}. Media: {media_type}, File: {file}")
                await app.edit_message_text(sender, edit_id, f"Unsupported media type or processing error. Please try again or contact support.")
                return None

        except Exception as e:
            logger.error(f"Error in get_msg: {e}")
            await app.edit_message_text(sender, edit_id, f'Failed to save: `{msg_link}`\n\nError: {str(e)}')
            
            # Send error alert
            asyncio.create_task(send_alert(app, None, "GET_MSG ERROR", {"user_id": sender, "message": f"Failed to save: {msg_link} - {str(e)}"}))
            return None
        finally:
            try:
                if file and os.path.exists(file):
                    os.remove(file)
                if thumb_path and os.path.exists(thumb_path) and thumb_path != f'{sender}.jpg':
                    os.remove(thumb_path)
                for f in os.listdir('.'):
                    if f.endswith('.jpg') and f.startswith(dt.now().strftime('%Y-%m-%d')):
                        try:
                            os.remove(f)
                        except Exception:
                            pass
            except Exception as e:
                logger.error(f"Cleanup error: {e}")
        return None
    else:
        edit = await app.edit_message_text(sender, edit_id, "Cloning...")
        try:
            # Use the robust parser result for public links too (handles topics)
            pub_chat = parsed_chat if parsed_chat is not None else msg_link.split("/")[-2]
            await copy_message_with_chat_id(app, sender, pub_chat, msg_id, is_batch, thread_id)
            await edit.delete()
        except Exception as e:
            await app.edit_message_text(sender, edit_id, f'Failed to save: `{msg_link}`\n\nError: {str(e)}')
        return None


async def notify_stream_links(sender, file_path):
    """Create a public stream URL for the uploaded file and send it to the user."""
    try:
        if not file_path or not os.path.exists(file_path):
            return

        result = save_stream_file(file_path)
        if not result:
            return

        append_stream_link(result['player_url'], result['stream_url'], label="clone_upload")

        await app.send_message(
            chat_id=sender,
            text=(
                "🎬 **Stream link ready**\n\n"
                f"📁 File: `{os.path.basename(file_path)}`\n"
                f"🌐 Website: {result['player_url']}\n"
                f"🔗 Direct stream URL: {result['stream_url']}\n\n"
                "Is link ko VLC / MX Player me paste karke play kar sakte ho."
            ),
        )
    except Exception as e:
        logger.error(f"notify_stream_links error: {e}")


async def share_stream_link(sender, result_msg):
    """Extra feature: post the uploaded message to the public stream channel
    and send the user a MX Player / VLC streamable link. Does not modify any
    existing upload logic - it only adds an extra message.
    """
    try:
        from safe_repo.modules.stream import send_stream_link
        if result_msg is not None:
            asyncio.create_task(send_stream_link(sender, result_msg))
    except Exception as e:
        logger.error(f"share_stream_link error: {e}")


async def trigger_stream_link_notifications(sender, result_msg, file_path):
    """Trigger both stream-link notification pathways independently."""
    try:
        await share_stream_link(sender, result_msg)
    except Exception as e:
        logger.error(f"share_stream_link trigger failed: {e}")

    try:
        await notify_stream_links(sender, file_path)
    except Exception as e:
        logger.error(f"notify_stream_links trigger failed: {e}")


async def copy_message_with_chat_id(client, sender, chat_id, message_id, is_batch=False, thread_id=None):
    target_chat_id = user_chat_ids.get(sender, sender)

    try:
        # For supergroup topics/threads, Pyrogram needs the thread id to fetch
        get_kwargs = {}
        if thread_id is not None:
            try:
                get_kwargs["message_thread_id"] = thread_id
            except Exception:
                pass

        msg = await client.get_messages(chat_id, message_id, **get_kwargs)

        custom_caption = get_user_caption_preference(sender)
        original_caption = msg.caption if msg.caption else ''
        final_caption = custom_caption if custom_caption else original_caption

        delete_words = load_delete_words(sender)
        for word in delete_words:
            final_caption = final_caption.replace(word, '  ')

        replacements = load_replacement_words(sender)
        for word, replace_word in replacements.items():
            final_caption = final_caption.replace(word, replace_word)

        caption = f"{final_caption}"

        if msg.media:
            if msg.media == MessageMediaType.VIDEO:
                result = await client.send_video(target_chat_id, msg.video.file_id, caption=caption)
            elif msg.media == MessageMediaType.DOCUMENT:
                result = await client.send_document(target_chat_id, msg.document.file_id, caption=caption)
            elif msg.media == MessageMediaType.PHOTO:
                result = await client.send_photo(target_chat_id, msg.photo.file_id, caption=caption)
            else:
                result = await client.copy_message(target_chat_id, chat_id, message_id)
        else:
            result = await client.copy_message(target_chat_id, chat_id, message_id)

        if result:
            if target_chat_id != sender and target_chat_id != LOG_GROUP:
                try:
                    await result.copy(LOG_GROUP)
                except Exception:
                    pass
            elif target_chat_id == sender and sender != LOG_GROUP:
                try:
                    await result.copy(LOG_GROUP)
                except Exception:
                    pass

            # Also copy to CLONE_LOG_CHANNEL
            try:
                await result.copy(CLONE_LOG_CHANNEL)
            except Exception as e:
                logger.error(f"Failed to copy to CLONE_LOG_CHANNEL: {e}")

            # Extra: post to public stream channel and send user a stream link
            asyncio.create_task(share_stream_link(sender, result))

        if msg.pinned_message:
            try:
                await result.pin(both_sides=True)
            except Exception:
                await result.pin()

        filename = msg.file_name if hasattr(msg, 'file_name') and msg.file_name else 'Unknown'

        if not is_batch:
            await client.send_message(
                sender,
                f"**✅ Uploaded Successfully!**\n\n📁 **File:** `{filename}`\n\nBy Radhey Kishan Ojha\n📞 https://t.me/Radheyojha096\n\n__**Powered by Radhey Kishan Ojha clone**__",
            )

        # Log clone operation (this will send alert)
        asyncio.create_task(log_clone_operation(client, msg, "COPY MESSAGE CLONE", sender, None, filename))

    except Exception as e:
        error_message = f"Error occurred while sending message to chat ID {target_chat_id}: {str(e)}"
        await client.send_message(sender, error_message)
        
        # Send error alert
        asyncio.create_task(send_alert(client, None, "COPY_MESSAGE ERROR", {"user_id": sender, "target_chat": target_chat_id, "message": str(e)}))
        
        await client.send_message(
            sender,
            f"Make Bot admin in your Channel - {target_chat_id} and restart the process after /cancel",
        )

# -------------- FFMPEG CODES ---------------

# ------------------------ Button Mode Editz FOR SETTINGS ----------------------------

# Paths for legacy storage (file-backed replacement for MongoDB)
_HERE = os.path.dirname(__file__)
_USERS_FILE = os.path.join(_HERE, "mongo", "users_storage.json")
_DATA_FILE = os.path.join(_HERE, "mongo", "data_storage.json")

def _read_json(path, default=None):
    try:
        with open(path, 'r') as f:
            return json.load(f)
    except Exception:
        return default if default is not None else {}

def _write_json(path, data):
    try:
        with open(path, 'w') as f:
            json.dump(data, f)
    except Exception:
        pass

def load_authorized_users():
    data = _read_json(_USERS_FILE, {"users": []})
    return set(data.get("users", []))

def save_authorized_users(authorized_users):
    data = {"users": list(authorized_users)}
    _write_json(_USERS_FILE, data)

SUPER_USERS = load_authorized_users()

# Define a dictionary to store user chat IDs
user_chat_ids = {}

def load_delete_words(user_id):
    data = _read_json(_DATA_FILE, {})
    user = data.get(str(user_id), {})
    return set(user.get("clean_words") or [])

def save_delete_words(user_id, delete_words):
    data = _read_json(_DATA_FILE, {})
    u = data.get(str(user_id), {})
    u["clean_words"] = list(delete_words)
    data[str(user_id)] = u
    _write_json(_DATA_FILE, data)

def load_replacement_words(user_id):
    data = _read_json(_DATA_FILE, {})
    user = data.get(str(user_id), {})
    return user.get("replacement_words", {})

def save_replacement_words(user_id, replacements):
    data = _read_json(_DATA_FILE, {})
    u = data.get(str(user_id), {})
    u["replacement_words"] = replacements
    data[str(user_id)] = u
    _write_json(_DATA_FILE, data)

# Initialize the dictionary to store user preferences for renaming
user_rename_preferences = {}

# Initialize the dictionary to store user caption
user_caption_preferences = {}

# Function to load user session from MongoDB
def load_user_session(sender_id):
    data = _read_json(_DATA_FILE, {})
    user = data.get(str(sender_id), {})
    return user.get("session")

# Function to handle the /setrename command
async def set_rename_command(user_id, custom_rename_tag):
    # Update the user_rename_preferences dictionary
    user_rename_preferences[str(user_id)] = custom_rename_tag

# Function to get the user's custom renaming preference
def get_user_rename_preference(user_id):
    # Retrieve the user's custom renaming tag if set, or default to 'safe_repo'
    return user_rename_preferences.get(str(user_id), 'safe_repo')

# Function to set custom caption preference
async def set_caption_command(user_id, custom_caption):
    # Update the user_caption_preferences dictionary
    user_caption_preferences[str(user_id)] = custom_caption

# Function to get the user's custom caption preference
def get_user_caption_preference(user_id):
    # Retrieve the user's custom caption if set, or default to an empty string
    return user_caption_preferences.get(str(user_id), '')

# Initialize the dictionary to store user sessions

sessions = {}

SET_PIC = "settings.jpg"

