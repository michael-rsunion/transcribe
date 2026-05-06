"""Manejo de directorio temporal por request + barrido de huerfanos."""

import shutil
import time
from pathlib import Path


def make_request_dir(base: Path, request_uuid: str) -> Path:
    d = base / request_uuid
    d.mkdir(parents=True, exist_ok=False)
    return d


def drop_request_dir(d: Path) -> None:
    shutil.rmtree(d, ignore_errors=True)


def sweep_orphans(base: Path, max_age_seconds: int = 3600) -> int:
    """Borra subdirectorios mas viejos que max_age_seconds. Retorna cuenta."""
    if not base.exists():
        return 0
    now = time.time()
    removed = 0
    for child in base.iterdir():
        try:
            if now - child.stat().st_mtime > max_age_seconds:
                shutil.rmtree(child, ignore_errors=True)
                removed += 1
        except FileNotFoundError:
            pass
    return removed
