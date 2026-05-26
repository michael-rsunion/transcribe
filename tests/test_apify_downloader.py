from pathlib import Path

import httpx
import pytest

from app.services.apify_downloader import (
    ApifyDownloadError,
    download_via_apify,
)


@pytest.mark.asyncio
async def test_raises_without_token(tmp_path):
    with pytest.raises(ApifyDownloadError, match="APIFY_TOKEN"):
        await download_via_apify(
            "https://www.instagram.com/reel/abc/", tmp_path, api_token=""
        )


@pytest.mark.asyncio
async def test_downloads_video_from_cdn_url(tmp_path, monkeypatch):
    cdn_url = "https://instagram.cdn.example/v/test.mp4"
    fake_apify_response = [
        {
            "videoUrl": cdn_url,
            "videoDuration": 12,
            "shortCode": "ABC123",
        }
    ]
    fake_mp4_content = b"\x00\x00\x00\x20ftypisom" + b"x" * 1000
    received_payload: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        if "api.apify.com" in str(request.url):
            import json as _json
            received_payload.update(_json.loads(request.content))
            return httpx.Response(200, json=fake_apify_response)
        if str(request.url) == cdn_url:
            return httpx.Response(200, content=fake_mp4_content)
        return httpx.Response(404)

    transport = httpx.MockTransport(handler)

    class _FakeAsyncClient(httpx.AsyncClient):
        def __init__(self, *a, **kw):
            kw["transport"] = transport
            super().__init__(*a, **kw)

    monkeypatch.setattr("app.services.apify_downloader.httpx.AsyncClient", _FakeAsyncClient)

    out = await download_via_apify(
        "https://www.instagram.com/reel/ABC123/",
        tmp_path,
        api_token="apify_test_token",
    )
    assert out == tmp_path / "v.mp4"
    assert out.read_bytes() == fake_mp4_content
    # Verifica que pasamos el campo correcto (`username`, no `directUrls`)
    assert received_payload.get("username") == [
        "https://www.instagram.com/reel/ABC123/"
    ]
    assert received_payload.get("resultsLimit") == 1


@pytest.mark.asyncio
async def test_raises_when_apify_returns_error(tmp_path, monkeypatch):
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, text="actor failed")

    transport = httpx.MockTransport(handler)

    class _FakeAsyncClient(httpx.AsyncClient):
        def __init__(self, *a, **kw):
            kw["transport"] = transport
            super().__init__(*a, **kw)

    monkeypatch.setattr("app.services.apify_downloader.httpx.AsyncClient", _FakeAsyncClient)

    with pytest.raises(ApifyDownloadError, match="apify HTTP 500"):
        await download_via_apify(
            "https://www.instagram.com/reel/abc/",
            tmp_path,
            api_token="t",
        )


@pytest.mark.asyncio
async def test_raises_when_no_video_url(tmp_path, monkeypatch):
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=[{"caption": "no video field"}])

    transport = httpx.MockTransport(handler)

    class _FakeAsyncClient(httpx.AsyncClient):
        def __init__(self, *a, **kw):
            kw["transport"] = transport
            super().__init__(*a, **kw)

    monkeypatch.setattr("app.services.apify_downloader.httpx.AsyncClient", _FakeAsyncClient)

    with pytest.raises(ApifyDownloadError, match="missing videoUrl"):
        await download_via_apify(
            "https://www.instagram.com/reel/abc/", tmp_path, api_token="t"
        )
