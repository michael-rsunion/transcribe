"""Anti-duplicacion: garantiza que la centralizacion no se rompa."""

from pathlib import Path

ROOT = Path(__file__).parent.parent / "app"


def _files() -> list[Path]:
    return [p for p in ROOT.rglob("*.py") if "__pycache__" not in str(p)]


def test_os_environ_only_in_config():
    for f in _files():
        if f.name == "config.py":
            continue
        src = f.read_text()
        assert "os.environ" not in src, f"os.environ leak in {f}"


def test_gemini_url_only_in_services_gemini():
    for f in _files():
        if f.parts[-2:] == ("services", "gemini.py"):
            continue
        src = f.read_text()
        assert "generativelanguage.googleapis" not in src, f"gemini url in {f}"


def test_no_inline_error_messages():
    needles = [
        "Plataforma no soportada",
        "No se pudo descargar",
        "demasiado largo",
        "Demasiados intentos fallidos",
    ]
    for f in _files():
        if f.parts[-2:] == ("constants", "messages.py"):
            continue
        src = f.read_text()
        for n in needles:
            assert n not in src, f"inline error '{n}' in {f}"


def test_no_inline_platform_regex():
    needles = ["instagram.com", "tiktok.com", "youtube.com"]
    for f in _files():
        if f.parts[-2:] == ("constants", "platforms.py"):
            continue
        src = f.read_text()
        for n in needles:
            assert n not in src, f"inline platform host '{n}' in {f}"
