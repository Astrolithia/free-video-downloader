# FreeVidGrab — 万能视频下载器

一个基于 Python + FastAPI + yt-dlp 的万能视频下载网站，支持 1000+ 平台。

## 快速开始

### 前置依赖

- Python 3.10+
- ffmpeg（用于音视频合并）

```bash
# macOS
brew install ffmpeg

# Ubuntu / Debian
sudo apt install ffmpeg
```

### 安装 & 启动

```bash
# 安装 Python 依赖
pip install -r requirements.txt

# 启动服务
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

打开浏览器访问 `http://localhost:8000` 即可使用。

## 功能

- 粘贴视频链接 → 一键解析 → 选择清晰度 → 下载
- 支持 YouTube、B 站、抖音/TikTok、Twitter/X、Instagram 等 1000+ 平台
- 实时下载进度展示
- 移动端完美适配

## 技术栈

| 层级     | 技术               |
| -------- | ------------------ |
| 后端     | FastAPI + uvicorn  |
| 核心引擎 | yt-dlp (Python API) |
| 前端     | HTML + TailwindCSS + Vanilla JS |
| 进度推送 | Server-Sent Events |

## 免责声明

本工具仅供个人学习和研究使用，请尊重版权，勿用于商业用途。使用者应自行承担因使用本工具而产生的一切风险。
