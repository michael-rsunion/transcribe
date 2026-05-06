from unittest.mock import patch

import pytest

from app.services.downloader import DownloadError, download_video


def test_builds_safe_ydl_opts(tmp_path):
    captured = {}

    class FakeYDL:
        def __init__(self, opts):
            captured.update(opts)

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def download(self, _urls):
            (tmp_path / "v.mp4").write_bytes(b"fake")
            return 0

    with patch("app.services.downloader.YoutubeDL", FakeYDL):
        out = download_video(
            "https://x.com/a", tmp_path, max_size_mb=100, socket_timeout=30
        )

    assert out == tmp_path / "v.mp4"
    assert captured["noplaylist"] is True
    assert captured["max_filesize"] == 100 * 1024 * 1024
    assert captured["socket_timeout"] == 30
    assert captured["cookiefile"] is None
    assert captured["outtmpl"].endswith("v.%(ext)s")
    assert "%(title)s" not in captured["outtmpl"]


def test_raises_on_download_error(tmp_path):
    class FakeYDL:
        def __init__(self, _opts):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def download(self, _urls):
            raise RuntimeError("boom")

    with patch("app.services.downloader.YoutubeDL", FakeYDL):
        with pytest.raises(DownloadError):
            download_video(
                "https://x.com/a", tmp_path, max_size_mb=100, socket_timeout=30
            )


def test_raises_when_no_file_produced(tmp_path):
    class FakeYDL:
        def __init__(self, _opts):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def download(self, _urls):
            return 0

    with patch("app.services.downloader.YoutubeDL", FakeYDL):
        with pytest.raises(DownloadError):
            download_video(
                "https://x.com/a", tmp_path, max_size_mb=100, socket_timeout=30
            )
