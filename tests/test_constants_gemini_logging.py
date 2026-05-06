from app.constants.gemini import DEFAULT_GEMINI_MODEL, GEMINI_PROMPT
from app.constants.logging import LOG_KEYS, url_hmac


def test_gemini_prompt_says_no_translation():
    p = GEMINI_PROMPT.lower()
    assert "no translation" in p
    assert "original language" in p


def test_default_model_is_2_5_flash():
    assert DEFAULT_GEMINI_MODEL == "gemini-2.5-flash"


def test_url_hmac_is_8_hex_chars_and_deterministic():
    h1 = url_hmac("https://x.com/a", "secret")
    h2 = url_hmac("https://x.com/a", "secret")
    assert len(h1) == 8
    assert h1 == h2
    assert all(c in "0123456789abcdef" for c in h1)


def test_url_hmac_changes_with_secret():
    assert url_hmac("a", "b") != url_hmac("a", "c")


def test_log_keys_present():
    for k in ("REQ_ID", "URL_HMAC", "PLATFORM", "DURATION_MS", "EVENT"):
        assert k in LOG_KEYS
