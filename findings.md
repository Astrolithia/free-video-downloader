# 调研发现

## 文档与现状

1. [docs/需求分析.md](/Users/shiro/Documents/Developer/free-video-downloader/docs/需求分析.md) 当前正式定义了“解析、下载、进度、保存文件”，但没有正式定义“网页内播放原视频”。
2. [docs/方案设计.md](/Users/shiro/Documents/Developer/free-video-downloader/docs/方案设计.md) 里的基础架构已经有前后端分离、Vite 代理和 FastAPI API 层，适合继续扩展一条“播放代理链路”。
3. 项目已经完成视频总结、字幕提取和下载后本地文件播放，因此“原视频播放”更适合设计成一条并行能力，而不是把下载链路硬改成播放器链路。

## 代码侧发现

1. [app/api/parse.py](/Users/shiro/Documents/Developer/free-video-downloader/app/api/parse.py) 已提供 `/api/stream`，会代理 `Range` 请求并透传 yt-dlp 给出的上游请求头。
2. [app/services/video_service.py](/Users/shiro/Documents/Developer/free-video-downloader/app/services/video_service.py) 的 `get_stream_source()` 目前只返回单个直链和请求头；对于音视频分离平台，只能选到“最佳可预览单路流”，不能完整表达多轨信息。
3. [frontend/src/components/VideoPlayer.vue](/Users/shiro/Documents/Developer/free-video-downloader/frontend/src/components/VideoPlayer.vue) 当前基于原生 `<video>`，适合 MP4 这类单资源播放，但对 DASH/HLS 和多轨扩展能力较弱。
4. [frontend/src/App.vue](/Users/shiro/Documents/Developer/free-video-downloader/frontend/src/App.vue) 已经有 `withMediaOrigin()` 这类媒体来源适配逻辑，后续接入“原视频播放地址”时可以复用。

## 开源方案调研

1. [Video.js](https://videojs.org/) 是成熟的开源 HTML5 播放器，生态完整，适合标准 MP4/HLS/DASH 播放器改造。
2. [Shaka Player](https://shaka-player-demo.appspot.com/docs/api/tutorial-welcome.html) 官方文档明确支持 DASH 和 HLS，适合处理自适应流和后续字幕扩展。
3. [ArtPlayer](https://artplayer.org/document/en/start/option.html) 对中文项目更友好，原生支持播放器 UI 定制，并可接入 `hls.js`、`dash.js`、`mpegts.js` 等第三方库。
4. [西瓜播放器 xgplayer](https://v2.h5player.bytedance.com/en/gettingStarted/) 也是成熟的前端播放器方案，支持 MP4/HLS/DASH，适合国内产品风格。
5. [yt-dlp-web-ui](https://github.com/marcopiovanello/yt-dlp-web-ui) 和 [webui-yt-dlp](https://github.com/neoxnitro/webui-yt-dlp) 说明“解析 + 格式选择 + Web UI”这条路线成熟，但它们的重点仍在下载管理，不直接解决复杂平台的浏览器内原视频播放。

## 关键技术判断

1. 如果只做“后端给一个 `/api/stream` 地址，前端 `<video src>` 直接播”，在拥有 progressive MP4 的平台上可行，但对 B 站这类常见的 DASH 音视频分离流覆盖不完整。
2. 真正稳定的“原视频播放”需要后端先识别资源类型：
   - Progressive 单文件
   - HLS manifest
   - DASH manifest
   - 音视频分离但无 manifest 的双路直链
3. 推荐的统一抽象不是“播放 URL”，而是“播放源描述”：
   - `type`
   - `video_url`
   - `audio_url`
   - `manifest_url`
   - `headers`
   - `poster`
   - `duration`
4. 当平台无法直接提供浏览器友好的 manifest，而只有分离的音视频直链时，P0 阶段应优先降级为“不支持原视频页内播放，请先下载后播放”，而不是硬上不稳定的伪播放。
