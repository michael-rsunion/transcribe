from app.constants.platforms import (
    ALLOWED_HOSTS,
    PLATFORM_PATH_RULES,
    platform_for_host,
)


def test_allowed_hosts_lowercase_and_clean():
    for h in ALLOWED_HOSTS:
        assert h == h.lower()
        assert "://" not in h
        assert "/" not in h


def test_known_hosts_present():
    expected = {
        "instagram.com", "www.instagram.com",
        "tiktok.com", "www.tiktok.com", "vm.tiktok.com",
        "youtube.com", "www.youtube.com", "youtu.be",
        "facebook.com", "www.facebook.com", "fb.watch",
        "twitter.com", "www.twitter.com", "x.com", "www.x.com",
    }
    assert expected.issubset(ALLOWED_HOSTS)


def test_path_rules_instagram_accepts_reel():
    assert PLATFORM_PATH_RULES["instagram.com"]({"path": "/reel/abc"}) is True
    assert PLATFORM_PATH_RULES["instagram.com"]({"path": "/p/abc"}) is True
    assert PLATFORM_PATH_RULES["instagram.com"]({"path": "/random/abc"}) is False


def test_path_rules_youtube_accepts_shorts():
    assert PLATFORM_PATH_RULES["youtube.com"]({"path": "/shorts/abc"}) is True
    assert PLATFORM_PATH_RULES["youtube.com"]({"path": "/random"}) is False


def test_platform_for_host():
    assert platform_for_host("www.instagram.com") == "instagram"
    assert platform_for_host("vm.tiktok.com") == "tiktok"
    assert platform_for_host("youtu.be") == "youtube"
    assert platform_for_host("fb.watch") == "facebook"
    assert platform_for_host("x.com") == "twitter"
