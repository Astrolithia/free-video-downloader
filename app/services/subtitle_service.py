"""Extract subtitles from videos via yt-dlp (platform-provided captions)."""

from __future__ import annotations

import asyncio
import json
import re
import time
import xml.etree.ElementTree as ET
from typing import Any

import httpx

from yt_dlp import YoutubeDL

from app.services.video_service import _should_bypass_proxy

_SUBTITLE_CACHE: dict[str, tuple[float, dict[str, Any]]] = {}
_CACHE_TTL = 600  # 10 minutes

_PREFERRED_LANGS = ["zh-Hans", "zh", "zh-CN", "en", "ja", "ko"]

_HTTP_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
    ),
    "Referer": "https://www.bilibili.com/",
}


def _get_cached(url: str) -> dict[str, Any] | None:
    entry = _SUBTITLE_CACHE.get(url)
    if entry and (time.time() - entry[0]) < _CACHE_TTL:
        return entry[1]
    if entry:
        del _SUBTITLE_CACHE[url]
    return None


def _set_cache(url: str, data: dict[str, Any]) -> None:
    _SUBTITLE_CACHE[url] = (time.time(), data)


def _parse_json3(raw: str) -> list[dict[str, Any]]:
    """Parse yt-dlp json3 subtitle format into a flat list of segments."""
    data = json.loads(raw)
    events = data.get("events", [])
    segments: list[dict[str, Any]] = []
    for ev in events:
        segs = ev.get("segs")
        if not segs:
            continue
        text = "".join(s.get("utf8", "") for s in segs).strip()
        if not text or text == "\n":
            continue
        start_ms = ev.get("tStartMs", 0)
        dur_ms = ev.get("dDurationMs", 0)
        segments.append({
            "start": round(start_ms / 1000, 2),
            "end": round((start_ms + dur_ms) / 1000, 2),
            "text": text,
        })
    return segments


def _parse_bilibili_json_subtitle(raw: str) -> list[dict[str, Any]]:
    """Parse Bilibili CC subtitle JSON ({"body": [{"from":..,"to":..,"content":..}, ...]})."""
    data = json.loads(raw)
    body = data.get("body", [])
    segments: list[dict[str, Any]] = []
    for item in body:
        text = item.get("content", "").strip()
        if not text:
            continue
        segments.append({
            "start": round(item.get("from", 0), 2),
            "end": round(item.get("to", 0), 2),
            "text": text,
        })
    return segments


def _parse_danmaku_xml(raw: str) -> list[dict[str, Any]]:
    """Parse Bilibili danmaku XML into time-sorted segments."""
    try:
        root = ET.fromstring(raw)
    except ET.ParseError:
        return []
    segments: list[dict[str, Any]] = []
    for d in root.findall("d"):
        p_attr = d.get("p", "")
        text = (d.text or "").strip()
        if not text or not p_attr:
            continue
        parts = p_attr.split(",")
        try:
            start = float(parts[0])
        except (ValueError, IndexError):
            continue
        segments.append({
            "start": round(start, 2),
            "end": round(start + 5, 2),
            "text": text,
        })
    segments.sort(key=lambda s: s["start"])
    return segments


def _parse_srv_formats(raw: str) -> list[dict[str, Any]]:
    """Fallback: parse SRT/VTT-like text into segments."""
    lines = raw.strip().split("\n")
    segments: list[dict[str, Any]] = []
    ts_re = re.compile(r"(\d+):(\d+):(\d+)[.,](\d+)")
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        match = re.search(r"(\d+:\d+:\d+[.,]\d+)\s*-->\s*(\d+:\d+:\d+[.,]\d+)", line)
        if match:
            def _to_sec(s: str) -> float:
                m = ts_re.match(s)
                if not m:
                    return 0.0
                h, mi, sc, ms = int(m[1]), int(m[2]), int(m[3]), int(m[4])
                return h * 3600 + mi * 60 + sc + ms / 1000

            start = _to_sec(match.group(1))
            end = _to_sec(match.group(2))
            i += 1
            text_parts: list[str] = []
            while i < len(lines) and lines[i].strip() and not lines[i].strip().isdigit():
                text_parts.append(re.sub(r"<[^>]+>", "", lines[i].strip()))
                i += 1
            text = " ".join(text_parts).strip()
            if text:
                segments.append({"start": round(start, 2), "end": round(end, 2), "text": text})
        else:
            i += 1
    return segments


def _fetch_subtitle_content(sub_url: str, page_url: str) -> str:
    """Fetch raw subtitle/danmaku content with proper headers."""
    headers = dict(_HTTP_HEADERS)
    if "bilibili.com" in page_url or "bilibili.com" in sub_url:
        headers["Referer"] = "https://www.bilibili.com/"
    elif "youtube.com" in page_url or "youtu.be" in page_url:
        headers["Referer"] = "https://www.youtube.com/"
    else:
        headers["Referer"] = page_url

    with httpx.Client(follow_redirects=True, timeout=15, headers=headers) as client:
        resp = client.get(sub_url)
        resp.raise_for_status()
        return resp.text


def _detect_and_parse(raw_text: str, sub_url: str) -> list[dict[str, Any]]:
    """Detect format and parse subtitle text into segments."""
    stripped = raw_text.strip()

    if stripped.startswith("{"):
        try:
            data = json.loads(stripped)
        except json.JSONDecodeError:
            return []
        if "events" in data:
            return _parse_json3(raw_text)
        if "body" in data:
            return _parse_bilibili_json_subtitle(raw_text)
        return _parse_json3(raw_text)

    if stripped.startswith("<?xml") or stripped.startswith("<i>"):
        return _parse_danmaku_xml(raw_text)

    return _parse_srv_formats(raw_text)


_BILIBILI_BV_RE = re.compile(r"BV[a-zA-Z0-9]+")


def _extract_bilibili_info(url: str) -> tuple[str, str, str] | None:
    """Extract (bvid, cid, title) from a Bilibili URL via their web API.

    Returns None when the URL is not a Bilibili video or the API call fails.
    """
    if "bilibili.com" not in url and "b23.tv" not in url:
        return None

    m = _BILIBILI_BV_RE.search(url)
    if not m:
        bvid_param = re.search(r"[?&]bvid=(BV[a-zA-Z0-9]+)", url)
        if not bvid_param:
            return None
        bvid = bvid_param.group(1)
    else:
        bvid = m.group(0)

    try:
        with httpx.Client(timeout=10, headers=_HTTP_HEADERS) as client:
            resp = client.get(
                "https://api.bilibili.com/x/web-interface/view",
                params={"bvid": bvid},
            )
            data = resp.json()
            if data.get("code") != 0:
                return None
            video = data["data"]
            return bvid, str(video["cid"]), video.get("title", "")
    except Exception:
        return None


def _fetch_bilibili_cc_subtitles(
    bvid: str, cid: str, title: str,
) -> dict[str, Any] | None:
    """Fetch CC subtitles from Bilibili's dm/view API (works without login).

    Returns a complete subtitle result dict, or None if no CC subtitles exist.
    """
    try:
        with httpx.Client(timeout=10, headers=_HTTP_HEADERS) as client:
            resp = client.get(
                "https://api.bilibili.com/x/v2/dm/view",
                params={"type": 1, "oid": cid, "pid": bvid},
            )
            data = resp.json()
            if data.get("code") != 0:
                return None

            subtitles_list = (
                data.get("data", {}).get("subtitle", {}).get("subtitles") or []
            )
            if not subtitles_list:
                return None

            chosen: dict | None = None
            for lang in _PREFERRED_LANGS:
                for entry in subtitles_list:
                    if entry.get("lan") == lang:
                        chosen = entry
                        break
                if chosen:
                    break
            if not chosen:
                chosen = subtitles_list[0]

            sub_url = chosen.get("subtitle_url", "")
            if not sub_url:
                return None
            if sub_url.startswith("//"):
                sub_url = "https:" + sub_url
            elif sub_url.startswith("http://"):
                sub_url = "https://" + sub_url[7:]

            sub_resp = client.get(sub_url)
            sub_resp.raise_for_status()
            raw_text = sub_resp.text

    except Exception:
        return None

    segments = _parse_bilibili_json_subtitle(raw_text)
    if not segments:
        return None

    full_text = "\n".join(seg["text"] for seg in segments)
    available = [e.get("lan", "") for e in subtitles_list]

    return {
        "subtitles": segments,
        "language": chosen.get("lan", ""),
        "full_text": full_text,
        "is_auto": False,
        "is_danmaku": False,
        "available_langs": available,
    }


def _extract_subtitles_sync(url: str) -> dict[str, Any]:
    """Blocking subtitle extraction — run in executor."""

    # --- Bilibili fast path: use dm/view API for real CC subtitles ---
    bili_info = _extract_bilibili_info(url)
    if bili_info:
        bvid, cid, title = bili_info
        cc_result = _fetch_bilibili_cc_subtitles(bvid, cid, title)
        if cc_result:
            return cc_result

    # --- Generic path via yt-dlp (also serves as Bilibili danmaku fallback) ---
    ydl_opts: dict[str, Any] = {
        "skip_download": True,
        "writesubtitles": True,
        "writeautomaticsub": True,
        "subtitleslangs": _PREFERRED_LANGS,
        "subtitlesformat": "json3/srv3/srv2/srv1/vtt/srt/best",
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
    }

    if _should_bypass_proxy(url):
        ydl_opts["proxy"] = ""

    with YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)

    subs = info.get("subtitles") or {}
    auto_subs = info.get("automatic_captions") or {}
    page_url = info.get("webpage_url", url)

    real_subs = {k: v for k, v in subs.items() if k != "danmaku"}
    danmaku_data = subs.get("danmaku")

    chosen_lang = ""
    chosen_data: list[dict] | None = None
    is_auto = False
    is_danmaku = False

    for lang in _PREFERRED_LANGS:
        if lang in real_subs and real_subs[lang]:
            chosen_lang = lang
            chosen_data = real_subs[lang]
            break
    if not chosen_data:
        for lang in _PREFERRED_LANGS:
            if lang in auto_subs and auto_subs[lang]:
                chosen_lang = lang
                chosen_data = auto_subs[lang]
                is_auto = True
                break

    if not chosen_data:
        if real_subs:
            chosen_lang = next(iter(real_subs))
            chosen_data = real_subs[chosen_lang]
        elif auto_subs:
            chosen_lang = next(iter(auto_subs))
            chosen_data = auto_subs[chosen_lang]
            is_auto = True

    if not chosen_data and danmaku_data:
        chosen_lang = "danmaku"
        chosen_data = danmaku_data
        is_danmaku = True

    if not chosen_data:
        return {
            "subtitles": [],
            "language": "",
            "full_text": "",
            "is_auto": False,
            "is_danmaku": False,
            "available_langs": [],
            "error": "该视频没有可用的字幕",
        }

    sub_url = ""
    if not is_danmaku:
        for fmt in chosen_data:
            if fmt.get("ext") == "json3":
                sub_url = fmt.get("url", "")
                break
    if not sub_url and chosen_data:
        sub_url = chosen_data[0].get("url", "")

    if not sub_url:
        return {
            "subtitles": [],
            "language": chosen_lang,
            "full_text": "",
            "is_auto": is_auto,
            "is_danmaku": is_danmaku,
            "available_langs": list(subs.keys()) + list(auto_subs.keys()),
            "error": "字幕 URL 获取失败",
        }

    try:
        raw_text = _fetch_subtitle_content(sub_url, page_url)
    except httpx.HTTPStatusError as e:
        return {
            "subtitles": [],
            "language": chosen_lang,
            "full_text": "",
            "is_auto": is_auto,
            "is_danmaku": is_danmaku,
            "available_langs": list(subs.keys()) + list(auto_subs.keys()),
            "error": f"字幕内容获取失败 (HTTP {e.response.status_code})",
        }

    segments = _detect_and_parse(raw_text, sub_url)
    full_text = "\n".join(seg["text"] for seg in segments)

    return {
        "subtitles": segments,
        "language": chosen_lang,
        "full_text": full_text,
        "is_auto": is_auto,
        "is_danmaku": is_danmaku,
        "available_langs": list(set(list(subs.keys()) + list(auto_subs.keys()))),
    }


async def extract_subtitles(url: str) -> dict[str, Any]:
    """Extract subtitles for *url*. Uses in-memory cache."""
    cached = _get_cached(url)
    if cached is not None:
        return cached

    loop = asyncio.get_running_loop()
    result = await loop.run_in_executor(None, _extract_subtitles_sync, url)

    if not result.get("error"):
        _set_cache(url, result)

    return result
