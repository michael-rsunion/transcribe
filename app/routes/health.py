"""Healthcheck minimo para Coolify. NO requiere auth."""

from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
