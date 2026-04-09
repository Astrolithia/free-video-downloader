# FreeVidGrab — 万能视频下载器

一个基于 Python + FastAPI + yt-dlp 的万能视频下载网站，支持 1000+ 平台。

## 快速开始

### 前置依赖

- Python 3.10+
- Node.js 18+（用于前端构建）
- ffmpeg（用于音视频合并）

```bash
# macOS
brew install ffmpeg node

# Ubuntu / Debian
sudo apt install ffmpeg nodejs npm
```

### 安装 & 启动

```bash
# 安装 Python 依赖
pip install -r requirements.txt

# 安装前端依赖并构建
cd frontend && npm install && npm run build && cd ..

# 启动服务
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

打开浏览器访问 `http://localhost:8000` 即可使用。

### 开发模式

前后端分别启动，享受 Vite HMR 热更新：

```bash
# 终端 1：启动后端
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 终端 2：启动前端开发服务器
cd frontend && npm run dev
```

开发时访问 `http://localhost:5173`，API 请求自动代理到后端。

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
| 前端     | Vue 3 + Tailwind CSS + TypeScript (Vite) |
| 进度推送 | Server-Sent Events |

## 免责声明

本工具仅供个人学习和研究使用，请尊重版权，勿用于商业用途。使用者应自行承担因使用本工具而产生的一切风险。
