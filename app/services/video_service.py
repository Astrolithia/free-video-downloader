"""Thin wrapper around yt-dlp for video info extraction and downloading."""

from __future__ import annotations

import asyncio
import re
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from yt_dlp import YoutubeDL
from yt_dlp.utils import DownloadError

from app.services import douyin as _douyin

DOWNLOADS_DIR = Path("downloads")
DOWNLOADS_DIR.mkdir(exist_ok=True)

# ---------------------------------------------------------------------------
# In-memory task store
# ---------------------------------------------------------------------------

@dataclass
class DownloadTask:
    task_id: str
    url: str
    title: str = ""
    status: str = "pending"          # pending | downloading | merging | done | error
    percent: float = 0.0
    speed: str = ""
    eta: str = ""
    filename: str = ""
    error: str = ""
    _listeners: list[asyncio.Queue] = field(default_factory=list, repr=False)

    def emit(self, event: dict):
        for q in self._listeners:
            q.put_nowait(event)

    def subscribe(self) -> asyncio.Queue:
        q: asyncio.Queue = asyncio.Queue()
        self._listeners.append(q)
        return q

    def unsubscribe(self, q: asyncio.Queue):
        self._listeners.remove(q)


_tasks: dict[str, DownloadTask] = {}


def get_task(task_id: str) -> DownloadTask | None:
    return _tasks.get(task_id)


# ---------------------------------------------------------------------------
# URL helpers
# ---------------------------------------------------------------------------

_URL_RE = re.compile(
    r"https?://[^\s<>\"'\u4e00-\u9fff\uff00-\uffef]+", re.IGNORECASE
)

_DIRECT_DOMAINS = (
    "bilibili.com", "b23.tv",
    "xiaohongshu.com", "xhslink.com",
    "weibo.com", "weibo.cn",
    "kuaishou.com",
    "ixigua.com",
    "douyin.com", "iesdouyin.com",
)


def _should_bypass_proxy(url: str) -> bool:
    """Return True if the URL targets a domestic site that should not go through proxy."""
    from urllib.parse import urlparse
    host = urlparse(url).hostname or ""
    return any(host == d or host.endswith("." + d) for d in _DIRECT_DOMAINS)


def extract_url(text: str) -> str | None:
    """Find the first HTTP(S) URL inside *text*, or return None."""
    m = _URL_RE.search(text.strip())
    return m.group(0).rstrip(",.;!?)\u3002\uff01") if m else None


# ---------------------------------------------------------------------------
# Info extraction (no download)
# ---------------------------------------------------------------------------

def _simplify_formats(raw_formats: list[dict]) -> list[dict]:
    """Return a de-duped, user-friendly list of download options.

    Also picks the best audio-only stream so the frontend can request
    ``video_format_id+audio_format_id`` for a guaranteed merge.
    """
    best_audio_id: str = ""
    best_audio_abr: float = 0

    for f in raw_formats:
        vcodec = f.get("vcodec", "none")
        acodec = f.get("acodec", "none")
        if vcodec == "none" and acodec != "none":
            abr = f.get("abr") or f.get("tbr") or 0
            if abr > best_audio_abr:
                best_audio_abr = abr
                best_audio_id = f.get("format_id", "")

    seen: set[str] = set()
    result: list[dict] = []

    for f in raw_formats:
        fmt_id = f.get("format_id", "")
        height = f.get("height")
        ext = f.get("ext", "")
        vcodec = f.get("vcodec", "none")
        acodec = f.get("acodec", "none")
        filesize = f.get("filesize") or f.get("filesize_approx")

        has_video = vcodec != "none"
        has_audio = acodec != "none"

        if not has_video:
            continue

        label = f"{height}p" if height else ext
        key = f"{label}-{ext}"
        if key in seen:
            continue
        seen.add(key)

        result.append({
            "format_id": fmt_id,
            "ext": ext,
            "height": height,
            "label": label,
            "has_audio": has_audio,
            "filesize": filesize,
            "best_audio_id": best_audio_id,
        })

    result.sort(key=lambda x: x.get("height") or 0, reverse=True)
    return result


async def extract_info(url: str, _retries: int = 2) -> dict[str, Any]:
    """Extract video metadata without downloading. Retries on transient failures."""

    if _douyin.is_douyin_url(url):
        return await _douyin.extract_info(url)

    ydl_opts: dict[str, Any] = {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
        "noplaylist": True,
        "ignore_no_formats_error": True,
    }

    if _should_bypass_proxy(url):
        ydl_opts["proxy"] = ""

    loop = asyncio.get_running_loop()

    def _extract():
        with YoutubeDL(ydl_opts) as ydl:
            return ydl.extract_info(url, download=False)

    last_exc: Exception | None = None
    info: dict[str, Any] = {}
    for attempt in range(_retries + 1):
        try:
            info = await loop.run_in_executor(None, _extract)
            break
        except Exception as exc:
            last_exc = exc
            if attempt < _retries:
                await asyncio.sleep(1)
    else:
        raise last_exc  # type: ignore[misc]

    formats = _simplify_formats(info.get("formats") or [])

    thumbnail = info.get("thumbnail", "")
    thumbnails = info.get("thumbnails") or []
    if not thumbnail and thumbnails:
        thumbnail = thumbnails[-1].get("url", "")

    return {
        "title": info.get("title", ""),
        "thumbnail": thumbnail,
        "duration": info.get("duration"),
        "uploader": info.get("uploader", ""),
        "webpage_url": info.get("webpage_url", url),
        "extractor": info.get("extractor", ""),
        "formats": formats,
    }


# ---------------------------------------------------------------------------
# Download
# ---------------------------------------------------------------------------

async def start_download(
    url: str,
    format_id: str | None = None,
    audio_id: str | None = None,
) -> DownloadTask:
    """Create a download task and run it in a background thread."""
    task_id = uuid.uuid4().hex[:12]
    task = DownloadTask(task_id=task_id, url=url)
    _tasks[task_id] = task

    loop = asyncio.get_running_loop()

    # ---- Douyin: custom downloader (no yt-dlp, no cookies) ----------------
    if _douyin.is_douyin_url(url):
        def _douyin_progress(pct: float, speed: str):
            task.status = "downloading"
            task.percent = pct
            task.speed = speed
            task.emit({"status": "downloading", "percent": pct, "speed": speed, "eta": ""})

        def _run_douyin():
            try:
                out = str(DOWNLOADS_DIR / f"{task_id}.mp4")
                _douyin.download_sync(url, out, progress_cb=_douyin_progress)
                task.filename = out
                task.status = "done"
                task.percent = 100.0
                task.emit({"status": "done", "percent": 100.0, "filename": out})
            except Exception as exc:
                task.status = "error"
                task.error = str(exc)
                task.emit({"status": "error", "error": task.error})

        loop.run_in_executor(None, _run_douyin)
        return task

    # ---- Generic: yt-dlp --------------------------------------------------
    def _progress_hook(d: dict):
        if d["status"] == "downloading":
            task.status = "downloading"
            raw = d.get("_percent_str", "0%").strip().replace("%", "")
            try:
                task.percent = float(raw)
            except ValueError:
                pass
            task.speed = d.get("_speed_str", "")
            task.eta = d.get("_eta_str", "")
            task.emit({
                "status": "downloading",
                "percent": task.percent,
                "speed": task.speed,
                "eta": task.eta,
            })
        elif d["status"] == "finished":
            task.status = "merging"
            task.percent = 100.0
            task.filename = d.get("filename", "")
            task.emit({"status": "merging", "percent": 100.0})

    def _run():
        try:
            if format_id and audio_id:
                fmt = f"{format_id}+{audio_id}/{format_id}/b"
            elif format_id:
                fmt = f"{format_id}+bestaudio/{format_id}/b"
            else:
                fmt = "bv*+ba/b"
            ydl_opts: dict[str, Any] = {
                "format": fmt,
                "outtmpl": str(DOWNLOADS_DIR / f"{task_id}.%(ext)s"),
                "merge_output_format": "mp4",
                "quiet": True,
                "no_warnings": True,
                "noplaylist": True,
                "ignore_no_formats_error": True,
                "progress_hooks": [_progress_hook],
            }
            if _should_bypass_proxy(url):
                ydl_opts["proxy"] = ""
            with YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                task.title = info.get("title", "")

            downloaded = list(DOWNLOADS_DIR.glob(f"{task_id}.*"))
            if downloaded:
                task.filename = str(downloaded[0])
                task.status = "done"
                task.percent = 100.0
                task.emit({"status": "done", "percent": 100.0, "filename": task.filename})
            else:
                task.status = "error"
                task.error = "下载完成但未找到文件"
                task.emit({"status": "error", "error": task.error})
        except DownloadError as exc:
            task.status = "error"
            task.error = str(exc)
            task.emit({"status": "error", "error": task.error})
        except Exception as exc:
            task.status = "error"
            task.error = str(exc)
            task.emit({"status": "error", "error": task.error})

    loop.run_in_executor(None, _run)

    return task


# ---------------------------------------------------------------------------
# Cleanup
# ---------------------------------------------------------------------------

def cleanup_task(task_id: str):
    """Remove task data and downloaded file."""
    task = _tasks.pop(task_id, None)
    if task and task.filename:
        p = Path(task.filename)
        if p.exists():
            p.unlink(missing_ok=True)


def cleanup_stale_files(max_age_seconds: int = 600):
    """Delete files in DOWNLOADS_DIR older than *max_age_seconds*."""
    now = time.time()
    for p in DOWNLOADS_DIR.iterdir():
        if p.is_file() and (now - p.stat().st_mtime) > max_age_seconds:
            try:
                p.unlink()
                task_prefix = p.stem
                _tasks.pop(task_prefix, None)
            except OSError:
                pass
