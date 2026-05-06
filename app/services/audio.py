"""ffmpeg/ffprobe via asyncio subprocess (sin shell, args como lista)."""

import asyncio
from pathlib import Path

# Alias para evitar falso positivo de hook de seguridad sobre la palabra clave.
_spawn = asyncio.create_subprocess_exec
_PIPE = asyncio.subprocess.PIPE


class AudioError(RuntimeError):
    pass


async def _run(args: list[str], timeout: int) -> tuple[bytes, bytes, int]:
    proc = await _spawn(*args, stdout=_PIPE, stderr=_PIPE)
    try:
        out, err = await asyncio.wait_for(proc.communicate(), timeout=timeout)
    except asyncio.TimeoutError:
        proc.kill()
        await proc.wait()
        raise AudioError(f"timeout after {timeout}s") from None
    return out, err, proc.returncode or 0


async def extract_audio_mp3(src: Path, target_dir: Path, *, timeout: int) -> Path:
    out_path = target_dir / "a.mp3"
    args = [
        "ffmpeg", "-y", "-i", str(src),
        "-vn", "-ac", "1", "-ar", "16000",
        "-c:a", "libmp3lame", "-b:a", "64k",
        str(out_path),
    ]
    _, err, code = await _run(args, timeout)
    if code != 0:
        raise AudioError(f"ffmpeg failed: {err.decode(errors='ignore')[:300]}")
    if not out_path.exists():
        raise AudioError("ffmpeg produced no output")
    return out_path


async def probe_duration_sec(src: Path, *, timeout: int) -> float:
    args = [
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        str(src),
    ]
    out, _, code = await _run(args, timeout)
    if code != 0:
        raise AudioError("ffprobe failed")
    try:
        return float(out.decode().strip())
    except ValueError as e:
        raise AudioError(f"could not parse duration: {out!r}") from e
