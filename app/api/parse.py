from urllib.parse import unquote

import httpx
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.services.video_service import extract_info, extract_url, get_best_stream_format_id, get_stream_source
from app.services.subtitle_service import extract_subtitles

router = APIRouter()


class ParseRequest(BaseModel):
    url: str


@router.post("/parse")
async def parse_video(req: ParseRequest):
    url = extract_url(req.url)
    if not url:
        raise HTTPException(status_code=400, detail="请输入有效的视频链接")

    try:
        info = await extract_info(url)
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"解析失败: {exc}")

    if not info.get("title"):
        raise HTTPException(status_code=422, detail="无法解析该链接，请确认链接是否正确")

    # Rewrite thumbnail URL through our proxy so the browser can load it
    thumb = info.get("thumbnail", "")
    if thumb:
        info["thumbnail"] = f"/api/thumb?url={thumb}"

    # Add the best previewable stream ID for the in-page player
    info["stream_format_id"] = get_best_stream_format_id(url)

    return info


@router.post("/subtitle")
async def get_subtitle(req: ParseRequest):
    url = extract_url(req.url)
    if not url:
        raise HTTPException(status_code=400, detail="请输入有效的视频链接")

    try:
        result = await extract_subtitles(url)
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"字幕提取失败: {exc}")

    return result


@router.get("/thumb")
async def proxy_thumbnail(url: str):
    """Proxy remote thumbnails to avoid Referer / CORS restrictions."""
    real_url = unquote(url)
    try:
        async with httpx.AsyncClient(follow_redirects=True, timeout=10) as client:
            resp = await client.get(real_url, headers={"Referer": real_url})
            content_type = resp.headers.get("content-type", "image/jpeg")
            return StreamingResponse(
                iter([resp.content]),
                media_type=content_type,
                headers={"Cache-Control": "public, max-age=86400"},
            )
    except Exception:
        raise HTTPException(status_code=502, detail="缩略图加载失败")


@router.get("/stream")
async def stream_video(request: Request, url: str, format_id: str = ""):
    """Proxy video stream with Range support for HTML5 video player."""
    if not url:
        raise HTTPException(status_code=400, detail="缺少视频 URL")

    stream_source = get_stream_source(url, format_id or None)
    if not stream_source:
        raise HTTPException(status_code=404, detail="视频流不可用，请先解析视频")
    stream_url, upstream_headers = stream_source

    range_header = request.headers.get("range", "")

    headers = {
        k: v
        for k, v in upstream_headers.items()
        if k.lower() != "accept-encoding"
    }
    headers.setdefault("Referer", url)
    if range_header:
        headers["Range"] = range_header

    async with httpx.AsyncClient(follow_redirects=True, timeout=60) as client:
        req = client.build_request("GET", stream_url, headers=headers)
        resp = await client.send(req, stream=True)

        resp_headers = {}
        if "content-range" in resp.headers:
            resp_headers["Content-Range"] = resp.headers["content-range"]
        if "content-length" in resp.headers:
            resp_headers["Content-Length"] = resp.headers["content-length"]
        if "accept-ranges" in resp.headers:
            resp_headers["Accept-Ranges"] = resp.headers["accept-ranges"]
        else:
            resp_headers["Accept-Ranges"] = "bytes"
        resp_headers["Content-Type"] = resp.headers.get("content-type", "video/mp4")
        resp_headers["Cache-Control"] = "no-cache"

        status_code = resp.status_code

        async def generate():
            try:
                async for chunk in resp.aiter_bytes(chunk_size=65536):
                    yield chunk
            finally:
                await resp.aclose()

        return StreamingResponse(
            generate(),
            status_code=status_code,
            headers=resp_headers,
            media_type=resp_headers.get("Content-Type", "video/mp4"),
        )
