"""HTML index. Requiere Basic Auth."""

from pathlib import Path

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from app.auth import require_basic_auth

router = APIRouter()

_TEMPLATES_DIR = Path(__file__).parent.parent / "templates"
_templates = Jinja2Templates(directory=str(_TEMPLATES_DIR))


@router.get(
    "/",
    response_class=HTMLResponse,
    dependencies=[Depends(require_basic_auth)],
)
def index(request: Request) -> HTMLResponse:
    return _templates.TemplateResponse(request, "index.html", {})
