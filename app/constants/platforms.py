"""Whitelist de plataformas y reglas de path. Cero regex inline en endpoints."""

from collections.abc import Callable

ALLOWED_HOSTS: frozenset[str] = frozenset(
    {
        "instagram.com",
        "www.instagram.com",
        "tiktok.com",
        "www.tiktok.com",
        "vm.tiktok.com",
        "youtube.com",
        "www.youtube.com",
        "youtu.be",
        "facebook.com",
        "www.facebook.com",
        "fb.watch",
        "twitter.com",
        "www.twitter.com",
        "x.com",
        "www.x.com",
    }
)


def _ig_ok(parts: dict) -> bool:
    return parts["path"].startswith(("/reel/", "/reels/", "/p/"))


def _yt_main_ok(parts: dict) -> bool:
    return parts["path"].startswith("/shorts/") or parts["path"].startswith("/watch")


def _fb_ok(parts: dict) -> bool:
    return parts["path"].startswith(("/reel/", "/watch"))


def _always_ok(_parts: dict) -> bool:
    return True


PLATFORM_PATH_RULES: dict[str, Callable[[dict], bool]] = {
    "instagram.com": _ig_ok,
    "www.instagram.com": _ig_ok,
    "tiktok.com": _always_ok,
    "www.tiktok.com": _always_ok,
    "vm.tiktok.com": _always_ok,
    "youtube.com": _yt_main_ok,
    "www.youtube.com": _yt_main_ok,
    "youtu.be": _always_ok,
    "facebook.com": _fb_ok,
    "www.facebook.com": _fb_ok,
    "fb.watch": _always_ok,
    "twitter.com": _always_ok,
    "www.twitter.com": _always_ok,
    "x.com": _always_ok,
    "www.x.com": _always_ok,
}


def platform_for_host(host: str) -> str:
    """Nombre canonico de la plataforma para logging."""
    h = host.lower()
    if "instagram" in h:
        return "instagram"
    if "tiktok" in h:
        return "tiktok"
    if "youtu" in h:
        return "youtube"
    if "facebook" in h or "fb.watch" in h:
        return "facebook"
    if "twitter" in h or "x.com" in h:
        return "twitter"
    return "unknown"
