# 调研发现

## 文档侧

1. [docs/需求分析.md](/Users/shiro/Documents/Developer/free-video-downloader/docs/需求分析.md) 当前正式定义的下载完成行为是“显示保存文件按钮”，没有要求页内播放器。
2. [docs/方案设计.md](/Users/shiro/Documents/Developer/free-video-downloader/docs/方案设计.md) 里 `VideoResult.vue` 的职责仍是“缩略图、标题、格式选择、下载按钮”，播放器是新增交互，不属于原设计基线。
3. 当前产品主线仍是“解析 -> 下载 -> 保存文件”，AI 总结和字幕是增值能力，播放器属于新扩展功能。

## 代码侧

1. [frontend/src/App.vue](/Users/shiro/Documents/Developer/free-video-downloader/frontend/src/App.vue) 目前在 `onDownload()` 中立即执行 `inlinePlayerSrc.value = buildStreamUrl(...)`，这会导致点击下载后封面马上切成播放器。
2. [frontend/src/components/VideoResult.vue](/Users/shiro/Documents/Developer/free-video-downloader/frontend/src/components/VideoResult.vue) 现在已经支持在封面区域根据 `playerSrc` 切换成 `VideoPlayer`。
3. [app/api/download.py](/Users/shiro/Documents/Developer/free-video-downloader/app/api/download.py) 已经有 `/api/play/{task_id}`，可以在下载完成后以内联方式返回本地 MP4 文件。
4. [app/api/parse.py](/Users/shiro/Documents/Developer/free-video-downloader/app/api/parse.py) 已经有 `/api/stream`，可用于代理源视频流做 H5 播放。
5. 现有前端测试 [frontend/src/App.test.ts](/Users/shiro/Documents/Developer/free-video-downloader/frontend/src/App.test.ts) 目前锁定的是“点击下载就切播放器”，与新需求相反，后续必须一起调整。

## 实施结果

1. [frontend/src/App.vue](/Users/shiro/Documents/Developer/free-video-downloader/frontend/src/App.vue) 已改为：点击下载时仅发起下载，不再立即设置 `playerSrc`。
2. 下载状态进入 `done` 后，页面会把封面区域切换为 `/api/play/{task_id}` 的本地文件播放器。
3. [frontend/src/components/DownloadProgress.vue](/Users/shiro/Documents/Developer/free-video-downloader/frontend/src/components/DownloadProgress.vue) 的文案已改成“下载完成后再切换播放器”。
4. [frontend/src/App.test.ts](/Users/shiro/Documents/Developer/free-video-downloader/frontend/src/App.test.ts) 已更新为新交互：下载过程中保持封面，完成后才显示播放器。

## 新发现：播放器黑屏/无法播放

1. 本地下载出的 mp4 文件本身是正常的：`h264 + aac`，容器也是标准 `mp4`，不是编码不兼容问题。
2. 真正的风险点在 [app/api/download.py](/Users/shiro/Documents/Developer/free-video-downloader/app/api/download.py)：`/api/play/{task_id}` 之前只依赖内存中的 `_tasks` 查找文件。
3. 当后端进程重载或任务缓存丢失时，前端播放器仍会切出来，但拿到的是 404 JSON 而不是视频流，浏览器就会显示“无法播放”。
4. 现已改成“优先读任务缓存，失败后回退到 `downloads/` 目录按 `task_id` 找文件”，解决了播放器样式出现但媒体无法加载的问题。
