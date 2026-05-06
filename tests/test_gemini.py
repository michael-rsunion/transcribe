from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.gemini import GeminiError, transcribe_audio


@pytest.mark.asyncio
async def test_transcribe_returns_text(tmp_path):
    audio = tmp_path / "a.mp3"
    audio.write_bytes(b"\x00" * 1000)

    fake_response = MagicMock()
    fake_response.text = "hola mundo"

    fake_client = MagicMock()
    fake_client.aio.models.generate_content = AsyncMock(return_value=fake_response)

    with patch("app.services.gemini.genai.Client", return_value=fake_client):
        text = await transcribe_audio(
            audio, api_key="k", model="gemini-2.5-flash", timeout=45
        )

    assert text == "hola mundo"
    fake_client.aio.models.generate_content.assert_awaited_once()


@pytest.mark.asyncio
async def test_raises_when_audio_oversize(tmp_path):
    audio = tmp_path / "a.mp3"
    audio.write_bytes(b"\x00" * 30_000_000)
    with pytest.raises(GeminiError):
        await transcribe_audio(
            audio,
            api_key="k",
            model="m",
            timeout=45,
            max_inline_bytes=20_000_000,
        )


@pytest.mark.asyncio
async def test_raises_on_empty_response(tmp_path):
    audio = tmp_path / "a.mp3"
    audio.write_bytes(b"\x00" * 100)

    fake_response = MagicMock()
    fake_response.text = "  "

    fake_client = MagicMock()
    fake_client.aio.models.generate_content = AsyncMock(return_value=fake_response)

    with patch("app.services.gemini.genai.Client", return_value=fake_client):
        with pytest.raises(GeminiError):
            await transcribe_audio(audio, api_key="k", model="m", timeout=45)
