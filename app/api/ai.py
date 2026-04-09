"""AI-powered endpoints: summary, chat, mind map — all streamed via SSE."""

import asyncio
import json
import logging
import os

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.services.video_service import extract_url
from app.services.subtitle_service import extract_subtitles
from app.services import ai_service

logger = logging.getLogger(__name__)

router = APIRouter()


class AIRequest(BaseModel):
    url: str
    title: str = ""


class ChatRequest(BaseModel):
    url: str
    title: str = ""
    messages: list[dict[str, str]]


async def _get_subtitle_text(url: str) -> str:
    """Helper: extract subtitles and return the full text, or raise."""
    result = await extract_subtitles(url)
    text = result.get("full_text", "")
    if not text:
        raise HTTPException(
            status_code=422,
            detail=result.get("error", "该视频没有可用的字幕，无法进行 AI 分析"),
        )
    return text


def _check_api_key():
    """Pre-flight check: raise if DeepSeek API key is not configured."""
    key = os.getenv("DEEPSEEK_API_KEY", "")
    if not key or key == "sk-your-api-key-here":
        raise HTTPException(
            status_code=503,
            detail="AI 功能未配置：请在 .env 文件中设置 DEEPSEEK_API_KEY",
        )


def _sse_stream(gen_func, *args):
    """Wrap a blocking generator as an async SSE stream with error handling."""

    async def event_generator():
        loop = asyncio.get_running_loop()
        try:
            gen = await loop.run_in_executor(None, gen_func, *args)
        except Exception as exc:
            logger.exception("AI stream init error")
            yield f"data: {json.dumps({'error': f'AI 服务初始化失败: {exc}'})}\n\n"
            return

        def _next(g):
            try:
                return ("token", next(g))
            except StopIteration:
                return ("done", None)
            except Exception as exc:
                return ("error", str(exc))

        while True:
            result = await loop.run_in_executor(None, _next, gen)
            kind, value = result
            if kind == "done":
                yield f"data: {json.dumps({'done': True})}\n\n"
                break
            elif kind == "error":
                logger.error("AI stream error: %s", value)
                yield f"data: {json.dumps({'error': value})}\n\n"
                break
            else:
                yield f"data: {json.dumps({'token': value})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/summary")
async def generate_summary(req: AIRequest):
    url = extract_url(req.url)
    if not url:
        raise HTTPException(status_code=400, detail="请输入有效的视频链接")

    _check_api_key()
    subtitle_text = await _get_subtitle_text(url)
    title = req.title or "未知视频"

    return _sse_stream(ai_service.stream_summary, subtitle_text, title)


@router.post("/chat")
async def ai_chat(req: ChatRequest):
    url = extract_url(req.url)
    if not url:
        raise HTTPException(status_code=400, detail="请输入有效的视频链接")

    if not req.messages:
        raise HTTPException(status_code=400, detail="消息不能为空")

    _check_api_key()
    subtitle_text = await _get_subtitle_text(url)
    title = req.title or "未知视频"

    return _sse_stream(ai_service.stream_chat, subtitle_text, title, req.messages)


@router.post("/mindmap")
async def generate_mindmap(req: AIRequest):
    url = extract_url(req.url)
    if not url:
        raise HTTPException(status_code=400, detail="请输入有效的视频链接")

    _check_api_key()
    subtitle_text = await _get_subtitle_text(url)
    title = req.title or "未知视频"

    return _sse_stream(ai_service.stream_mindmap, subtitle_text, title)
