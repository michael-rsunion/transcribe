"""Cliente Gemini: inline bytes (no File API), prompt centralizado."""

import asyncio
from pathlib import Path

from google import genai
from google.genai import types

from app.constants.gemini import GEMINI_PROMPT


class GeminiError(RuntimeError):
    pass


async def transcribe_audio(
    audio_path: Path,
    *,
    api_key: str,
    model: str,
    timeout: int,
    max_inline_bytes: int = 20_000_000,
) -> str:
    """Transcribe el audio en su idioma original. Retorna texto plano."""
    data = audio_path.read_bytes()
    if len(data) > max_inline_bytes:
        raise GeminiError(
            f"audio {len(data)}B excede inline limit {max_inline_bytes}B"
        )
    client = genai.Client(api_key=api_key)
    audio_part = types.Part.from_bytes(data=data, mime_type="audio/mp3")
    try:
        resp = await asyncio.wait_for(
            client.aio.models.generate_content(
                model=model,
                contents=[GEMINI_PROMPT, audio_part],
            ),
            timeout=timeout,
        )
    except asyncio.TimeoutError:
        raise GeminiError(f"gemini timeout after {timeout}s") from None
    except Exception as e:
        raise GeminiError(str(e)) from e
    text = (resp.text or "").strip()
    if not text:
        raise GeminiError("empty transcription")
    return text
