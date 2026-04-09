"""DeepSeek LLM integration for video content analysis."""

from __future__ import annotations

import os
from collections.abc import Generator

from openai import OpenAI

_client: OpenAI | None = None


def _get_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(
            api_key=os.getenv("DEEPSEEK_API_KEY", ""),
            base_url=os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com"),
        )
    return _client


def _model() -> str:
    return os.getenv("DEEPSEEK_MODEL", "deepseek-chat")


SUMMARY_PROMPT = """\
你是一个专业的视频内容分析师。请根据提供的视频字幕生成结构化总结。

输出格式（使用 Markdown）：

## 一句话概要
（50字以内概括核心内容）

## 核心要点
- 💡 要点一
- 🔑 要点二
- 📌 要点三
（3-5条，每条配 emoji，简明扼要）

## 详细总结
（分段落，200-500字，涵盖视频主要内容和论点）

## 关键词
`关键词1` `关键词2` `关键词3`
（3-5个关键词，用反引号包裹）
"""

CHAT_SYSTEM_TEMPLATE = """\
你是一个视频内容助手。用户正在观看视频《{title}》。
请基于以下视频字幕内容回答用户的问题。回答要准确、有条理。
如果问题超出视频内容范围，请诚实说明这一点，但可以基于你的知识做适当延伸。

视频字幕：
{subtitle_text}
"""

MINDMAP_PROMPT = """\
请根据视频字幕内容，生成一个 Markdown 格式的思维导图大纲。

要求：
- 使用 Markdown 标题层级（# ## ### ####）表示节点层级
- 根节点使用 # 加上视频标题
- 第二层使用 ## 表示主要主题（3-6个）
- 第三层使用 ### 表示子要点
- 第四层使用 #### 表示具体细节（可选）
- 每个节点简洁精炼，不超过20个字
- 只输出 Markdown 大纲，不要输出任何解释性文字
"""


def _truncate_subtitle(text: str, max_chars: int = 12000) -> str:
    """Prevent extremely long subtitles from exceeding context limits."""
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + "\n\n[字幕内容过长，已截断]"


def stream_summary(subtitle_text: str, title: str) -> Generator[str, None, None]:
    client = _get_client()
    text = _truncate_subtitle(subtitle_text)
    response = client.chat.completions.create(
        model=_model(),
        messages=[
            {"role": "system", "content": SUMMARY_PROMPT},
            {"role": "user", "content": f"视频标题：{title}\n\n字幕内容：\n{text}"},
        ],
        stream=True,
    )
    for chunk in response:
        if chunk.choices and chunk.choices[0].delta.content:
            yield chunk.choices[0].delta.content


def stream_chat(
    subtitle_text: str,
    title: str,
    messages: list[dict[str, str]],
) -> Generator[str, None, None]:
    client = _get_client()
    text = _truncate_subtitle(subtitle_text)
    system_msg = CHAT_SYSTEM_TEMPLATE.format(title=title, subtitle_text=text)

    response = client.chat.completions.create(
        model=_model(),
        messages=[
            {"role": "system", "content": system_msg},
            *messages,
        ],
        stream=True,
    )
    for chunk in response:
        if chunk.choices and chunk.choices[0].delta.content:
            yield chunk.choices[0].delta.content


def stream_mindmap(subtitle_text: str, title: str) -> Generator[str, None, None]:
    client = _get_client()
    text = _truncate_subtitle(subtitle_text)
    response = client.chat.completions.create(
        model=_model(),
        messages=[
            {"role": "system", "content": MINDMAP_PROMPT},
            {"role": "user", "content": f"视频标题：{title}\n\n字幕内容：\n{text}"},
        ],
        stream=True,
    )
    for chunk in response:
        if chunk.choices and chunk.choices[0].delta.content:
            yield chunk.choices[0].delta.content
