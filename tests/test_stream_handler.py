import asyncio

from safe_repo.modules.stream import build_local_file_name, has_media_payload, get_archive_chat_ids, format_progress_bar
from safe_repo.core.get_func import trigger_stream_link_notifications


class DummyMessage:
    message_id = 42

    class DummyMedia:
        pass

    video = DummyMedia()


def test_build_local_file_name_uses_video_extension():
    filename = build_local_file_name(DummyMessage())
    assert filename.startswith("stream_42_")
    assert filename.endswith(".mp4")


def test_build_local_file_name_falls_back_to_id():
    class MessageWithId:
        id = 77
        video = object()

    filename = build_local_file_name(MessageWithId())
    assert filename.startswith("stream_77_")
    assert filename.endswith(".mp4")


def test_has_media_payload_for_forwarded_message():
    class ForwardedMessage:
        forwarded = True
        media = False

    assert has_media_payload(ForwardedMessage())


def test_has_media_payload_for_forward_origin_field():
    class ForwardOriginMessage:
        forward_origin = object()
        media = False

    assert has_media_payload(ForwardOriginMessage())


def test_get_archive_chat_ids_includes_configured_channel(monkeypatch):
    monkeypatch.delenv("ARCHIVE_CHAT_ID", raising=False)
    monkeypatch.delenv("CLONE_LOG_CHANNEL", raising=False)
    ids = get_archive_chat_ids()
    assert -1003886456761 in ids


def test_format_progress_bar_contains_percentage_and_label():
    text = format_progress_bar(60, "Downloading media", "Please wait")
    assert "60%" in text
    assert "Downloading media" in text
    assert "Please wait" in text


def test_trigger_stream_link_notifications_schedules_both_paths(monkeypatch):
    calls = []

    async def fake_share(sender, result_msg):
        calls.append(("share", sender, result_msg))

    async def fake_notify(sender, file_path):
        calls.append(("notify", sender, file_path))

    monkeypatch.setattr("safe_repo.core.get_func.share_stream_link", fake_share)
    monkeypatch.setattr("safe_repo.core.get_func.notify_stream_links", fake_notify)

    asyncio.run(trigger_stream_link_notifications(123, "message", "/tmp/file"))

    assert calls == [
        ("share", 123, "message"),
        ("notify", 123, "/tmp/file"),
    ]
