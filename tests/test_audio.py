from unittest.mock import AsyncMock, patch

import pytest

from app.services.audio import (
    AudioError,
    extract_audio_mp3,
    probe_duration_sec,
)


@pytest.mark.asyncio
async def test_extract_audio_calls_ffmpeg_with_mono_16k(tmp_path):
    src = tmp_path / "v.mp4"
    src.write_bytes(b"x")

    fake_proc = AsyncMock()
    fake_proc.communicate = AsyncMock(return_value=(b"", b""))
    fake_proc.returncode = 0

    captured_args: list = []

    async def fake_spawn(*args, **_kwargs):
        captured_args.extend(args)
        # Crear el archivo de salida para que la funcion no falle
        (tmp_path / "a.mp3").write_bytes(b"fake_audio")
        return fake_proc

    with patch("app.services.audio._spawn", side_effect=fake_spawn):
        out = await extract_audio_mp3(src, tmp_path, timeout=30)

    assert out == tmp_path / "a.mp3"
    assert captured_args[0] == "ffmpeg"
    assert "-ac" in captured_args
    assert "1" in captured_args
    assert "-ar" in captured_args
    assert "16000" in captured_args


@pytest.mark.asyncio
async def test_extract_audio_raises_on_nonzero_exit(tmp_path):
    src = tmp_path / "v.mp4"
    src.write_bytes(b"x")

    fake_proc = AsyncMock()
    fake_proc.communicate = AsyncMock(return_value=(b"", b"ffmpeg error"))
    fake_proc.returncode = 1

    async def fake_spawn(*_args, **_kwargs):
        return fake_proc

    with patch("app.services.audio._spawn", side_effect=fake_spawn):
        with pytest.raises(AudioError):
            await extract_audio_mp3(src, tmp_path, timeout=30)


@pytest.mark.asyncio
async def test_probe_returns_duration(tmp_path):
    src = tmp_path / "v.mp4"
    src.write_bytes(b"x")

    fake_proc = AsyncMock()
    fake_proc.communicate = AsyncMock(return_value=(b"42.5\n", b""))
    fake_proc.returncode = 0

    async def fake_spawn(*_args, **_kwargs):
        return fake_proc

    with patch("app.services.audio._spawn", side_effect=fake_spawn):
        d = await probe_duration_sec(src, timeout=10)

    assert d == 42.5
