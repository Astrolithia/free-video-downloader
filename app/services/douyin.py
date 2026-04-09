"""Cookie-free Douyin video extraction & download.

Uses the mobile share page (iesdouyin.com) which embeds video metadata in
``window._ROUTER_DATA`` — no cookies, a_bogus, or login required.
"""

from __future__ import annotations

import json
import re
from typing import Any, Callable

import httpx

_MOBILE_UA = (
    "Mozilla/5.0 (Linux; Android 8.0.0; SM-G955U Build/R16NW) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/116.0.0.0 Mobile Safari/537.36"
)
_REFERER = "https://www.douyin.com/?is_from_mobile_home=1&recommend=1"
_HEADERS = {"User-Agent": _MOBILE_UA, "Referer": _REFERER}

_ROUTER_RE = re.compile(r"window\._ROUTER_DATA\s*=\s*(.*?)</script>", re.S)

# Module-level cache: webpage_url -> download_url (avoids re-extraction)
_download_url_cache: dict[str, str] = {}


def is_douyin_url(url: str) -> bool:
    return "douyin.com" in url or "iesdouyin.com" in url


async def _resolve_short_url(url: str) -> str:
    """Follow redirects on a short link and return the final URL."""
    async with httpx.AsyncClient(
        follow_redirects=True, timeout=10, headers=_HEADERS
    ) as client:
        resp = await client.get(url)
        return str(resp.url)


def _extract_video_id(url: str) -> str | None:
    m = re.search(r"/video/(\d+)", url)
    if m:
        return m.group(1)
    m = re.search(r"(\d{15,})", url)
    return m.group(1) if m else None


async def extract_info(url: str) -> dict[str, Any]:
    """Return video metadata in the same shape as video_service.extract_info."""
    resolved = url
    if "v.douyin.com" in url or "/share/" not in url:
        resolved = await _resolve_short_url(url)

    video_id = _extract_video_id(resolved)
    if not video_id:
        raise ValueError("无法从链接中提取抖音视频ID")

    share_url = f"https://www.iesdouyin.com/share/video/{video_id}/"

    async with httpx.AsyncClient(
        follow_redirects=True, timeout=15, headers=_HEADERS
    ) as client:
        resp = await client.get(share_url)
        resp.raise_for_status()
        html = resp.text

    m = _ROUTER_RE.search(html)
    if not m:
        raise ValueError("无法解析抖音视频数据（页面结构可能已变更）")

    raw = m.group(1).strip().rstrip(";")
    data = json.loads(raw)

    items = (
        data.get("loaderData", {})
        .get("video_(id)/page", {})
        .get("videoInfoRes", {})
        .get("item_list", [])
    )
    if not items:
        raise ValueError("视频信息为空，可能已被删除或无权访问")

    item = items[0]
    title = item.get("desc", "")
    author = item.get("author", {}).get("nickname", "")

    cover = ""
    cover_list = item.get("video", {}).get("cover", {}).get("url_list", [])
    if cover_list:
        cover = cover_list[0]

    uri = item.get("video", {}).get("play_addr", {}).get("uri", "")
    if uri and not uri.startswith("http") and "mp3" not in uri:
        download_url = (
            f"https://www.douyin.com/aweme/v1/play/"
            f"?video_id={uri}&ratio=1080p&line=0"
        )
    elif uri.startswith("http"):
        download_url = uri
    else:
        download_url = ""

    duration_ms = item.get("video", {}).get("duration", 0)
    height = item.get("video", {}).get("height", 0)
    width = item.get("video", {}).get("width", 0)

    webpage_url = f"https://www.douyin.com/video/{video_id}"
    if download_url:
        _download_url_cache[webpage_url] = download_url

    return {
        "title": title,
        "thumbnail": cover,
        "duration": (duration_ms / 1000) if duration_ms else None,
        "uploader": author,
        "webpage_url": webpage_url,
        "extractor": "Douyin",
        "formats": [
            {
                "format_id": "douyin_best",
                "ext": "mp4",
                "height": height or None,
                "label": f"{height}p" if height else "最佳画质",
                "has_audio": True,
                "filesize": None,
                "best_audio_id": "",
            }
        ],
    }


def _extract_download_url_sync(url: str) -> str:
    """Synchronous fallback to obtain the Douyin download URL."""
    with httpx.Client(follow_redirects=True, timeout=15, headers=_HEADERS) as client:
        resolved = url
        if "v.douyin.com" in url or "/share/" not in url:
            resp = client.get(url)
            resolved = str(resp.url)

        vid = _extract_video_id(resolved)
        if not vid:
            raise ValueError("无法从链接中提取抖音视频ID")

        resp = client.get(f"https://www.iesdouyin.com/share/video/{vid}/")
        resp.raise_for_status()

    m = _ROUTER_RE.search(resp.text)
    if not m:
        raise ValueError("无法解析抖音视频数据")

    data = json.loads(m.group(1).strip().rstrip(";"))
    items = (
        data.get("loaderData", {})
        .get("video_(id)/page", {})
        .get("videoInfoRes", {})
        .get("item_list", [])
    )
    if not items:
        raise ValueError("视频信息为空")

    uri = items[0].get("video", {}).get("play_addr", {}).get("uri", "")
    if uri and not uri.startswith("http") and "mp3" not in uri:
        return (
            f"https://www.douyin.com/aweme/v1/play/"
            f"?video_id={uri}&ratio=1080p&line=0"
        )
    if uri.startswith("http"):
        return uri
    raise ValueError("未找到视频播放地址")


def download_sync(
    webpage_url: str,
    output_path: str,
    progress_cb: Callable[[float, str], None] | None = None,
) -> str:
    """Blocking download — intended to run inside ``run_in_executor``.

    Returns the final file path.
    """
    video_url = _download_url_cache.get(webpage_url, "")
    if not video_url:
        video_url = _extract_download_url_sync(webpage_url)
        _download_url_cache[webpage_url] = video_url

    with httpx.Client(
        follow_redirects=True, timeout=120, headers=_HEADERS
    ) as client:
        with client.stream("GET", video_url) as resp:
            resp.raise_for_status()
            total = int(resp.headers.get("content-length", 0))
            downloaded = 0

            with open(output_path, "wb") as f:
                for chunk in resp.iter_bytes(chunk_size=65536):
                    f.write(chunk)
                    downloaded += len(chunk)
                    if progress_cb and total:
                        pct = downloaded / total * 100
                        speed = ""
                        progress_cb(pct, speed)

    return output_path
