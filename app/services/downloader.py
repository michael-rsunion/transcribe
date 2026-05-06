"""Wrapper de yt-dlp con args seguros (no shell, UUID-only outtmpl, etc)."""

from pathlib import Path

from yt_dlp import YoutubeDL


class DownloadError(RuntimeError):
    pass


def download_video(
    url: str,
    target_dir: Path,
    *,
    max_size_mb: int,
    socket_timeout: int,
) -> Path:
    """Descarga el video a target_dir/v.<ext>. Retorna ruta del archivo."""
    outtmpl = str(target_dir / "v.%(ext)s")
    opts = {
        "outtmpl": outtmpl,
        "noplaylist": True,
        "max_filesize": max_size_mb * 1024 * 1024,
        "socket_timeout": socket_timeout,
        "cookiefile": None,
        "no_warnings": True,
        "quiet": True,
    }
    try:
        with YoutubeDL(opts) as ydl:
            ydl.download([url])
    except Exception as e:
        raise DownloadError(str(e)) from e
    files = list(target_dir.glob("v.*"))
    if not files:
        raise DownloadError("yt-dlp produced no file")
    return files[0]
