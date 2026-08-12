import os

from app import app, build_stream_response


def test_build_stream_response_uses_inline_video_mimetype(tmp_path):
    media_path = tmp_path / "sample.mp4"
    media_path.write_bytes(b"fake mp4")

    with app.test_request_context('/'):
        response = build_stream_response(str(media_path), as_attachment=False)

    assert response.mimetype == "video/mp4"
    assert "inline" in response.headers.get("Content-Disposition", "")


def test_build_stream_response_uses_attachment_for_download(tmp_path):
    media_path = tmp_path / "sample.mp4"
    media_path.write_bytes(b"fake mp4")

    with app.test_request_context('/'):
        response = build_stream_response(str(media_path), as_attachment=True)

    assert response.mimetype == "video/mp4"
    assert "attachment" in response.headers.get("Content-Disposition", "")
