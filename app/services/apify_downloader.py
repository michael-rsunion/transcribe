"""Descarga de Reels de Instagram via Apify (bypasses rate-limit de IP datacenter).

Flujo:
  1. Llamar al actor `apify/instagram-reel-scraper` con la URL del Reel.
  2. Apify nos devuelve el videoUrl (CDN de Instagram, signed temporary).
  3. Descargamos el MP4 directo del CDN (no consume creditos de Apify).
"""

from pathlib import Path

import httpx


class ApifyDownloadError(RuntimeError):
    pass


# Centralizado aqui — unico lugar que conoce el endpoint de Apify.
APIFY_ACTOR_ID = "apify~instagram-reel-scraper"
APIFY_API_BASE = "https://api.apify.com/v2"

_CDN_CHUNK_BYTES = 64 * 1024


async def download_via_apify(
    url: str,
    target_dir: Path,
    *,
    api_token: str,
    timeout_sec: int = 90,
) -> Path:
    """Descarga un Reel de Instagram usando Apify. Retorna ruta del MP4 local."""
    if not api_token:
        raise ApifyDownloadError("APIFY_TOKEN no configurado")

    actor_url = f"{APIFY_API_BASE}/acts/{APIFY_ACTOR_ID}/run-sync-get-dataset-items"
    actor_timeout = max(30, timeout_sec - 20)

    async with httpx.AsyncClient(timeout=timeout_sec) as client:
        try:
            # NOTA: el actor `apify/instagram-reel-scraper` usa el campo `username`
            # como entrada generica que acepta usernames, profile URLs, IDs O direct reel URLs.
            # Le pasamos la URL del Reel directo aqui. Ver schema en
            # https://apify.com/apify/instagram-reel-scraper/input-schema
            resp = await client.post(
                actor_url,
                params={"token": api_token, "timeout": actor_timeout},
                json={"username": [url], "resultsLimit": 1},
            )
        except httpx.HTTPError as e:
            raise ApifyDownloadError(f"apify request failed: {e}") from e

        # Apify devuelve 200 o 201 (Created) en run-sync segun estado interno,
        # ambos significan exito. Solo fallamos en 4xx/5xx.
        if not (200 <= resp.status_code < 300):
            raise ApifyDownloadError(
                f"apify HTTP {resp.status_code}: {resp.text[:200]}"
            )

        try:
            items = resp.json()
        except ValueError as e:
            raise ApifyDownloadError(f"apify response not JSON: {resp.text[:200]}") from e

        if not isinstance(items, list) or not items:
            raise ApifyDownloadError(f"apify empty dataset: {resp.text[:200]}")

        video_url = items[0].get("videoUrl")
        if not video_url:
            raise ApifyDownloadError(
                "apify response missing videoUrl (Reel sin video o privado)"
            )

        out_path = target_dir / "v.mp4"
        try:
            async with client.stream("GET", video_url, follow_redirects=True) as r:
                if r.status_code != 200:
                    raise ApifyDownloadError(f"CDN HTTP {r.status_code}")
                with out_path.open("wb") as f:
                    async for chunk in r.aiter_bytes(chunk_size=_CDN_CHUNK_BYTES):
                        f.write(chunk)
        except httpx.HTTPError as e:
            raise ApifyDownloadError(f"CDN download failed: {e}") from e

        if not out_path.exists() or out_path.stat().st_size == 0:
            raise ApifyDownloadError("downloaded file is empty")

        return out_path
