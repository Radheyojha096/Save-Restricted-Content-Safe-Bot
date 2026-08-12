# safe_repo
# Extra module: post cloned media to a public channel and return a
# MX Player / VLC streamable link (t.me/Link09660/MSGID).
# This module does NOT modify any existing upload/download logic.

import logging
import os
import uuid
from datetime import datetime
from pyrogram import filters
from safe_repo import app
from config import STREAM_CHANNEL, STREAM_CHANNEL_USERNAME, CLONE_LOG_CHANNEL
from safe_repo.core.media_links import append_stream_link, save_stream_file, read_stream_links
from safe_repo.web.study import build_public_study_url

logger = logging.getLogger(__name__)


def format_progress_bar(percent, title="Processing", note="Please wait"):
    """Create a compact Telegram-friendly progress message."""
    percent = max(0, min(100, int(percent)))
    filled = max(1, int(round(percent / 10)))
    empty = 10 - filled
    bar = "█" * filled + "░" * empty
    return (
        f"🎬 {title}\n"
        f"[{bar}] {percent}%\n"
        f"{note}"
    )


def format_failure_message(reason="Stream setup failed"):
    """Return a friendly failure message for link generation issues."""
    return (
        "⚠️ Stream link generate nahi ho paya\n\n"
        "Possible reasons:\n"
        "• file thoda badi ho sakti hai\n"
        "• bot ke paas temporary storage access nahi ho\n"
        "• public URL setup incomplete ho sakti hai\n\n"
        "Aap dobara try karo ya thodi der baad try karo."
    )


def get_archive_chat_ids():
    """Return chat IDs that should receive archived stream links."""
    configured_ids = []
    for raw_value in (os.environ.get("ARCHIVE_CHAT_ID"), os.environ.get("CLONE_LOG_CHANNEL"), str(CLONE_LOG_CHANNEL)):
        if not raw_value:
            continue
        for chunk in str(raw_value).replace(" ", "").split(","):
            if not chunk:
                continue
            try:
                configured_ids.append(int(chunk))
            except ValueError:
                configured_ids.append(chunk)
    return configured_ids


def extract_stream_metadata(message, fallback_title=None):
    """Extract a subject/description/title from an incoming media message."""
    caption = getattr(message, "caption", None) or getattr(message, "text", None) or ""
    caption = str(caption).strip()
    title = fallback_title or "Untitled"
    description = caption
    subject = "General"
    date = datetime.now().strftime("%Y-%m-%d")

    if caption:
        lines = [line.strip() for line in caption.splitlines() if line.strip()]
        if lines:
            title = lines[0]
        for line in lines:
            if line.lower().startswith("subject:"):
                subject = line.split(":", 1)[1].strip() or subject
                break
            if line.lower().startswith("topic:"):
                subject = line.split(":", 1)[1].strip() or subject
                break

    return {"subject": subject, "description": description, "title": title, "date": date}


def build_local_file_name(message):
    """Create a safe local filename based on the incoming message."""
    ext = ".mp4"
    if getattr(message, "document", None) is not None:
        mime = getattr(message.document, "mime_type", "") or ""
        if "image" in mime:
            ext = ".jpg"
        elif "audio" in mime:
            ext = ".mp3"
        elif "pdf" in mime:
            ext = ".pdf"
        else:
            ext = ".bin"
    elif getattr(message, "video", None) is not None:
        ext = ".mp4"
    elif getattr(message, "photo", None) is not None:
        ext = ".jpg"

    msg_id = getattr(message, "message_id", None)
    if msg_id is None:
        msg_id = getattr(message, "id", None)
    if msg_id is None:
        msg_id = "unknown"

    return f"stream_{msg_id}_{uuid.uuid4().hex[:8]}{ext}"


def has_media_payload(message):
    """Return True for direct or forwarded media messages."""
    forward_origin = getattr(message, "forward_origin", None)
    is_forwarded = bool(
        getattr(message, "forwarded", False)
        or getattr(message, "is_forwarded", False)
        or forward_origin is not None
    )
    return bool(
        getattr(message, "media", False)
        or getattr(message, "video", None) is not None
        or getattr(message, "document", None) is not None
        or getattr(message, "photo", None) is not None
        or getattr(message, "audio", None) is not None
        or getattr(message, "animation", None) is not None
        or getattr(message, "sticker", None) is not None
        or is_forwarded
    )


async def download_media_payload(client, message, progress_sender=None, progress_message_id=None):
    """Download media with a fallback for forwarded files."""
    file_name = build_local_file_name(message)
    media_file = None

    try:
        media_file = await client.download_media(message, file_name=file_name)
    except Exception:
        media_file = None

    if not media_file:
        try:
            media_file = await message.download(file_name=file_name)
        except Exception:
            media_file = None

    if progress_sender and progress_message_id and media_file:
        try:
            await app.edit_message_text(
                progress_sender,
                progress_message_id,
                format_progress_bar(100, "Link ready", "Almost done"),
            )
        except Exception:
            pass

    return media_file


async def post_to_stream_channel(message):
    """Clone the given message to the public stream channel and return the streamable links.

    This is the fallback path for forwarded media and very large files when local
    caching is not possible or practical.
    """
    try:
        if message is None:
            return None

        forwarded = None
        for action in ("copy", "forward"):
            try:
                if action == "copy":
                    forwarded = await message.copy(STREAM_CHANNEL)
                else:
                    forwarded = await message.forward(STREAM_CHANNEL)
                if forwarded is not None:
                    break
            except Exception as inner_error:
                logger.debug(f"Stream channel {action} attempt failed: {inner_error}")

        if forwarded is None:
            return None
        msg_id = getattr(forwarded, "id", None)
        if msg_id is None:
            return None
        base = f"https://t.me/{STREAM_CHANNEL_USERNAME}/{msg_id}"
        return {
            "link": base,
            "embed": base + "?embed=1",
        }
    except Exception as e:
        logger.error(f"Stream channel post failed: {e}")
        return None


async def build_public_stream_link(message, media_file=None):
    """Build a public stream link from local cache when possible, else fall back to a Telegram channel post for large or unsupported files."""
    if media_file and os.path.exists(media_file):
        try:
            saved = save_stream_file(media_file)
            if saved:
                return {
                    "source": "cache",
                    "player_url": saved["player_url"],
                    "stream_url": saved["stream_url"],
                    "token": saved["token"],
                }
        except Exception:
            pass

    result = await post_to_stream_channel(message)
    if result:
        return {
            "source": "channel",
            "player_url": result["embed"],
            "stream_url": result["link"],
            "token": None,
        }
    return None


def build_public_study_link(metadata=None, base_url=None):
    """Create a public study-site URL that can jump to the subject/date catalog view."""
    metadata = metadata or {}
    subject = str(metadata.get("subject") or "").strip() or None
    date = str(metadata.get("date") or "").strip() or None
    title = str(metadata.get("title") or "").strip() or None

    if not base_url:
        base_url = (
            os.environ.get("PUBLIC_BASE_URL")
            or os.environ.get("APP_URL")
            or os.environ.get("RENDER_EXTERNAL_URL")
            or os.environ.get("BASE_URL")
            or "https://save-by-radhey.onrender.com"
        ).strip()

    if subject and date and title:
        return build_public_study_url(base_url, subject=subject, date=date, q=title)

    if subject and date:
        return build_public_study_url(base_url, subject=subject, date=date)

    if subject:
        return build_public_study_url(base_url, subject=subject)

    return build_public_study_url(base_url)


def build_stream_reply_text(public_link, study_url=None):
    """Build a Telegram reply that includes both player and website links."""
    lines = [
        "✅ **Stream link ready**",
        "",
        f"📺 Player: {public_link['player_url']}",
        f"🔗 Direct Stream: {public_link['stream_url']}",
    ]
    if study_url:
        lines.extend([
            "",
            f"🌐 Website link: {study_url}",
            "Is website link par click karke subject/date wise videos dekh sakte ho.",
        ])
    else:
        lines.extend([
            "",
            "🌐 Website link abhi generate nahi ho saka."
        ])
    return "\n".join(lines)


async def archive_stream_link(message, player_url, stream_url, study_url=None):
    """Send the generated stream links to the configured archive chats."""
    try:
        text = (
            "🎬 **Stream link ready**\n\n"
            f"📺 Player: {player_url}\n"
            f"🔗 Stream: {stream_url}"
        )
        if study_url:
            text = text + f"\n🌐 Study site: {study_url}"
        for chat_id in get_archive_chat_ids():
            if not chat_id:
                continue
            try:
                await app.send_message(chat_id=chat_id, text=text)
            except Exception as inner_error:
                logger.warning(f"Failed to archive stream link to {chat_id}: {inner_error}")
    except Exception as e:
        logger.warning(f"archive_stream_link failed: {e}")


async def send_stream_link(sender, message, caption_prefix="🎬 **Stream Link:**"):
    """Post the uploaded message to the public stream channel and send the
    streamable link(s) back to the user as an extra message.
    """
    try:
        result = await post_to_stream_channel(message)
        if not result:
            # Post failed (likely bot is not admin in the public channel).
            await app.send_message(
                chat_id=sender,
                text="⚠️ **Stream link generate nahi ho paya.**\n"
                     f"Bot ko channel @{STREAM_CHANNEL_USERNAME} mein **admin** banaayein "
                     "(post permission ke sath) taaki stream link mile.",
            )
            return
        text = (
            f"{caption_prefix}\n"
            f"🔗 Direct link: {result['link']}\n\n"
            "Is link ko VLC / MX Player ya kisi bhi media player mein open kar sakte ho."
        )
        await app.send_message(chat_id=sender, text=text)
    except Exception as e:
        logger.error(f"send_stream_link failed: {e}")


@app.on_message(filters.media)
async def handle_direct_media(client, message):
    """Generate a public stream link for any media sent directly to the bot."""
    try:
        if not has_media_payload(message):
            return

        chat_id = message.chat.id
        status_message = await app.send_message(
            chat_id,
            format_progress_bar(15, "Processing media", "Starting download"),
        )
        media_file = await download_media_payload(
            client,
            message,
            progress_sender=chat_id,
            progress_message_id=status_message.id,
        )
        if not media_file:
            await app.edit_message_text(
                chat_id,
                status_message.id,
                "⚠️ Media download fail ho gaya.\n\nPlease try again in a moment.",
            )
            return

        try:
            await app.edit_message_text(
                chat_id,
                status_message.id,
                format_progress_bar(60, "Preparing stream link", "Generating public link"),
            )
        except Exception:
            pass

        public_link = await build_public_stream_link(message, media_file)
        if not public_link:
            try:
                os.remove(media_file)
            except Exception:
                pass
            await app.edit_message_text(chat_id, status_message.id, format_failure_message())
            return

        metadata = extract_stream_metadata(message, fallback_title=os.path.basename(media_file))
        study_url = build_public_study_link(metadata)
        append_stream_link(
            public_link['player_url'],
            public_link['stream_url'],
            label="direct_media",
            subject=metadata['subject'],
            description=metadata['description'],
            title=metadata['title'],
            token=public_link.get('token'),
        )
        await archive_stream_link(message, public_link['player_url'], public_link['stream_url'], study_url=study_url)

        text = build_stream_reply_text(public_link, study_url=study_url)
        await app.edit_message_text(chat_id, status_message.id, text)

        try:
            os.remove(media_file)
        except Exception:
            pass
    except Exception as e:
        logger.error(f"handle_direct_media failed: {e}")
        await app.send_message(chat_id, f"⚠️ Error: {str(e)}")


@app.on_message(filters.forwarded)
async def handle_forwarded_media(client, message):
    """Generate stream links for forwarded media messages as well."""
    if not has_media_payload(message):
        return
    await handle_direct_media(client, message)


@app.on_message(filters.command("links"))
async def export_stream_links(_, message):
    """Send a text file containing all generated stream links."""
    try:
        content = read_stream_links()
        if not content.strip():
            await app.send_message(message.chat.id, "📄 Abhi tak koi stream link archive nahi hui.")
            return

        archive_path = os.path.join(os.getcwd(), "stream_links.txt")
        with open(archive_path, "w", encoding="utf-8") as handle:
            handle.write(content)

        await app.send_document(
            chat_id=message.chat.id,
            document=archive_path,
            caption="📄 Generated stream links archive",
        )
    except Exception as e:
        logger.error(f"export_stream_links failed: {e}")
        await app.send_message(message.chat.id, f"⚠️ Error: {str(e)}")


@app.on_message(filters.command("exportlinks"))
async def export_stream_links_alias(_, message):
    await export_stream_links(_, message)
