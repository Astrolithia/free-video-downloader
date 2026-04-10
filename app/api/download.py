import asyncio
import json
import mimetypes
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel

from app.services.video_service import (
    DOWNLOADS_DIR,
    start_download,
    get_task,
    cleanup_task,
    extract_url,
)

router = APIRouter()


class DownloadRequest(BaseModel):
    url: str
    format_id: str | None = None
    audio_id: str | None = None


def _resolve_downloaded_file(task_id: str) -> Path | None:
    exact_mp4 = DOWNLOADS_DIR / f"{task_id}.mp4"
    if exact_mp4.exists():
        return exact_mp4

    candidates = sorted(DOWNLOADS_DIR.glob(f"{task_id}.*"))
    if not candidates:
        return None

    mp4_candidates = [p for p in candidates if p.suffix.lower() == ".mp4"]
    if mp4_candidates:
        return sorted(mp4_candidates, key=lambda p: (len(p.name), p.name))[0]

    return candidates[0]


def _get_task_file(task_id: str) -> tuple[Path, str]:
    task = get_task(task_id)
    filepath: Path | None = None
    title = "video"

    if task and task.filename:
      filepath = Path(task.filename)
      title = task.title or title
      if filepath.exists():
          return filepath, title

    fallback = _resolve_downloaded_file(task_id)
    if fallback:
        return fallback, title

    raise HTTPException(status_code=404, detail="文件不存在")


@router.post("/download")
async def download_video(req: DownloadRequest):
    url = extract_url(req.url)
    if not url:
        raise HTTPException(status_code=400, detail="请输入有效的视频链接")

    task = await start_download(url, req.format_id, req.audio_id)
    return {"task_id": task.task_id}


@router.get("/progress/{task_id}")
async def progress_stream(task_id: str):
    task = get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")

    async def event_generator():
        queue = task.subscribe()
        try:
            # send current state immediately
            yield f"data: {json.dumps({'status': task.status, 'percent': task.percent})}\n\n"

            while True:
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=30.0)
                    yield f"data: {json.dumps(event)}\n\n"
                    if event.get("status") in ("done", "error"):
                        break
                except asyncio.TimeoutError:
                    yield f"data: {json.dumps({'status': 'heartbeat'})}\n\n"
        finally:
            task.unsubscribe(queue)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/file/{task_id}")
async def get_file(task_id: str):
    task = get_task(task_id)
    if task and task.status != "done":
        raise HTTPException(status_code=400, detail="文件尚未准备好")

    filepath, title = _get_task_file(task_id)

    safe_title = title.replace("/", "_").replace("\\", "_")
    ext = filepath.suffix
    download_name = f"{safe_title}{ext}"

    return FileResponse(
        path=str(filepath),
        filename=download_name,
        media_type="application/octet-stream",
    )


@router.get("/play/{task_id}")
async def play_file(task_id: str):
    task = get_task(task_id)
    if task and task.status != "done":
        raise HTTPException(status_code=400, detail="文件尚未准备好")

    filepath, _ = _get_task_file(task_id)

    media_type, _ = mimetypes.guess_type(filepath.name)

    return FileResponse(
        path=str(filepath),
        media_type=media_type or "video/mp4",
        filename=filepath.name,
        content_disposition_type="inline",
    )
