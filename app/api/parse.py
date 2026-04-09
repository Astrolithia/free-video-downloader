from urllib.parse import unquote

import httpx
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.services.video_service import extract_info, looks_like_url

router = APIRouter()


class ParseRequest(BaseModel):
    url: str


@router.post("/parse")
async def parse_video(req: ParseRequest):
    url = req.url.strip()
    if not looks_like_url(url):
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

    return info


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
