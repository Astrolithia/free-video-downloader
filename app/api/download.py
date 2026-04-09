import asyncio
import json
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel

from app.services.video_service import (
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
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    if task.status != "done":
        raise HTTPException(status_code=400, detail="文件尚未准备好")

    filepath = Path(task.filename)
    if not filepath.exists():
        raise HTTPException(status_code=404, detail="文件不存在")

    safe_title = (task.title or "video").replace("/", "_").replace("\\", "_")
    ext = filepath.suffix
    download_name = f"{safe_title}{ext}"

    return FileResponse(
        path=str(filepath),
        filename=download_name,
        media_type="application/octet-stream",
    )
