import pytest

from app.services.url_validator import UrlValidationError, validate_url


@pytest.fixture(autouse=True)
def _force_public(monkeypatch):
    monkeypatch.setattr(
        "app.services.url_validator._resolve_is_public", lambda _h: True
    )


@pytest.mark.parametrize(
    "url",
    [
        "https://www.instagram.com/reel/abc/",
        "https://instagram.com/p/abc/",
        "https://www.tiktok.com/@user/video/123",
        "https://vm.tiktok.com/ABC/",
        "https://www.youtube.com/shorts/abc",
        "https://youtu.be/abc",
        "https://www.facebook.com/reel/123",
        "https://fb.watch/xyz",
        "https://x.com/u/status/1",
        "https://twitter.com/u/status/1",
    ],
)
def test_accepts_valid(url):
    parts = validate_url(url)
    assert parts.host
    assert parts.platform != "unknown"


@pytest.mark.parametrize(
    "url",
    [
        "http://www.instagram.com/reel/abc",
        "https://evil.com/?x=instagram.com/reel/abc",
        "https://malicious.com/r",
        "https://instagram.com/random/abc",
        "https://youtube.com/random",
        "ftp://x.com/a",
        "not a url",
        "",
    ],
)
def test_rejects_invalid(url):
    with pytest.raises(UrlValidationError):
        validate_url(url)


def test_rejects_private_ip(monkeypatch):
    monkeypatch.setattr(
        "app.services.url_validator._resolve_is_public", lambda _h: False
    )
    with pytest.raises(UrlValidationError):
        validate_url("https://x.com/u/status/1")
