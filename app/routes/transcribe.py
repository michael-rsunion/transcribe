"""Endpoint /transcribe: orquesta validate -> download -> ffmpeg -> gemini -> cleanup."""

import asyncio
import time
import uuid
from pathlib import Path

import structlog
from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from app.auth import require_basic_auth
from app.config import Settings, get_settings
from app.constants.logging import LOG_KEYS, url_hmac
from app.constants.messages import ERROR_MESSAGES
from app.services.audio import AudioError, extract_audio_mp3, probe_duration_sec
from app.services.cleanup import drop_request_dir, make_request_dir
from app.services.concurrency import Gate, get_gate
from app.services.downloader import DownloadError, download_video
from app.services.gemini import GeminiError, transcribe_audio
from app.services.url_validator import UrlValidationError, validate_url

logger = structlog.get_logger()

router = APIRouter()

_TEMPLATES_DIR = Path(__file__).parent.parent / "templates"
_templates = Jinja2Templates(directory=str(_TEMPLATES_DIR))


def _gate_dep() -> Gate:
    return get_gate()


def _accepts_html(request: Request) -> bool:
    accept = request.headers.get("accept", "")
    return "text/html" in accept and "application/json" not in accept


def _err_response(request: Request, status_code: int, msg: str):
    if _accepts_html(request):
        return _templates.TemplateResponse(
            request,
            "_result.html",
            {"error": msg},
            status_code=status_code,
        )
    raise HTTPException(status_code=status_code, detail=msg)


def _ok_response(
    request: Request,
    *,
    texto: str,
    duracion_seg: float,
    modelo: str,
    platform: str,
):
    payload = {
        "texto": texto,
        "duracion_seg": duracion_seg,
        "modelo": modelo,
        "platform": platform,
    }
    if _accepts_html(request):
        return _templates.TemplateResponse(request, "_result.html", payload)
    return payload


@router.post(
    "/transcribe",
    dependencies=[Depends(require_basic_auth)],
    response_model=None,
)
async def transcribe(
    request: Request,
    url: str = Form(..., max_length=2048),
    settings: Settings = Depends(get_settings),
    gate: Gate = Depends(_gate_dep),
) -> HTMLResponse | dict:
    request_uuid = uuid.uuid4().hex
    start_t = time.time()

    try:
        v = validate_url(url)
    except UrlValidationError as e:
        logger.warning(
            "transcribe.invalid_url",
            **{LOG_KEYS["REQ_ID"]: request_uuid, "reason": str(e)[:120]},
        )
        return _err_response(request, 400, ERROR_MESSAGES["URL_NO_SOPORTADA"])

    logger.info(
        "transcribe.start",
        **{
            LOG_KEYS["REQ_ID"]: request_uuid,
            LOG_KEYS["URL_HMAC"]: url_hmac(v.raw, settings.HMAC_LOG_SECRET),
            LOG_KEYS["PLATFORM"]: v.platform,
        },
    )

    base = Path(settings.TMPFS_BASE_DIR)
    base.mkdir(parents=True, exist_ok=True)
    workdir = make_request_dir(base, request_uuid)

    try:
        async def _pipeline():
            video_path = await asyncio.to_thread(
                download_video,
                v.raw,
                workdir,
                max_size_mb=settings.MAX_DOWNLOAD_SIZE_MB,
                socket_timeout=settings.YT_DLP_SOCKET_TIMEOUT_SEC,
            )
            duration = await probe_duration_sec(
                video_path, timeout=settings.FFMPEG_TIMEOUT_SEC
            )
            if duration > settings.MAX_VIDEO_DURATION_SEC:
                raise HTTPException(413, ERROR_MESSAGES["VIDEO_LARGO"])
            audio = await extract_audio_mp3(
                video_path, workdir, timeout=settings.FFMPEG_TIMEOUT_SEC
            )
            text = await transcribe_audio(
                audio,
                api_key=settings.GEMINI_API_KEY,
                model=settings.GEMINI_MODEL,
                timeout=settings.GEMINI_TIMEOUT_SEC,
                max_inline_bytes=settings.MAX_INLINE_AUDIO_BYTES,
            )
            return text, duration

        async with gate.acquire():
            text, duration = await asyncio.wait_for(
                _pipeline(), timeout=settings.TOTAL_REQUEST_TIMEOUT_SEC
            )

        logger.info(
            "transcribe.success",
            **{
                LOG_KEYS["REQ_ID"]: request_uuid,
                LOG_KEYS["PLATFORM"]: v.platform,
                LOG_KEYS["DURATION_MS"]: int((time.time() - start_t) * 1000),
            },
        )
        return _ok_response(
            request,
            texto=text,
            duracion_seg=duration,
            modelo=settings.GEMINI_MODEL,
            platform=v.platform,
        )

    except HTTPException as e:
        if _accepts_html(request):
            return _templates.TemplateResponse(
                request,
                "_result.html",
                {"error": e.detail},
                status_code=e.status_code,
            )
        raise
    except DownloadError as e:
        logger.warning(
            "transcribe.download_error",
            **{LOG_KEYS["REQ_ID"]: request_uuid, "reason": str(e)[:120]},
        )
        return _err_response(request, 422, ERROR_MESSAGES["DESCARGA_FALLIDA"])
    except AudioError as e:
        logger.warning(
            "transcribe.audio_error",
            **{LOG_KEYS["REQ_ID"]: request_uuid, "reason": str(e)[:120]},
        )
        return _err_response(request, 504, ERROR_MESSAGES["TIMEOUT_SUBPROCESO"])
    except GeminiError as e:
        logger.warning(
            "transcribe.gemini_error",
            **{LOG_KEYS["REQ_ID"]: request_uuid, "reason": str(e)[:120]},
        )
        return _err_response(
            request, 502, ERROR_MESSAGES["TRANSCRIPCION_NO_DISPONIBLE"]
        )
    except asyncio.TimeoutError:
        logger.warning(
            "transcribe.total_timeout",
            **{LOG_KEYS["REQ_ID"]: request_uuid},
        )
        return _err_response(request, 504, ERROR_MESSAGES["TIMEOUT_TOTAL"])
    finally:
        drop_request_dir(workdir)
