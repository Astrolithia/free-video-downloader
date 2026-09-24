# 部署到 VPS（Docker 方式）

## 前置条件

VPS 上需要安装 Docker 和 Docker Compose：

```bash
# Ubuntu / Debian
curl -fsSL https://get.docker.com | sh
sudo apt-get install -y docker-compose-plugin
```

---

## 步骤一：上传代码到服务器

```bash
# 方式 A：Git（推荐）
git clone https://github.com/your-repo/free-video-downloader.git
cd free-video-downloader

# 方式 B：直接 scp
scp -r . user@your-server-ip:/home/user/free-video-downloader
```

---

## 步骤二：配置环境变量

```bash
cp .env.example .env
nano .env   # 填入你的 DEEPSEEK_API_KEY
```

---

## 步骤三：构建并启动

```bash
docker compose up -d --build
```

构建完成后访问 `http://your-server-ip:8000`

---

## 步骤四（可选）：配置 Nginx 反向代理 + HTTPS

安装 Nginx 和 Certbot（Let's Encrypt 免费证书）：

```bash
sudo apt-get install -y nginx certbot python3-certbot-nginx
```

创建站点配置 `/etc/nginx/sites-available/fvd`：

```nginx
server {
    listen 80;
    server_name your-domain.com;

    client_max_body_size 100M;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        # 支持 SSE（AI 流式输出）
        proxy_buffering off;
        proxy_read_timeout 300s;
    }
}
```

```bash
sudo ln -s /etc/nginx/sites-available/fvd /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx

# 申请 HTTPS 证书
sudo certbot --nginx -d your-domain.com
```

---

## 常用运维命令

```bash
# 查看日志
docker compose logs -f

# 停止服务
docker compose down

# 更新代码后重新部署
git pull
docker compose up -d --build

# 手动清理下载缓存
docker compose exec app python -c "from app.services.video_service import cleanup_stale_files; cleanup_stale_files(0)"
```

---

## 注意事项

- **防火墙**：确保云服务器安全组放行 `8000` 端口（或 `80/443`）
- **磁盘空间**：`downloads/` 目录每 10 分钟自动清理，但仍建议监控磁盘用量
- **AI 功能**：不填写 `DEEPSEEK_API_KEY` 时，视频解析和下载功能仍可正常使用，仅 AI 分析功能不可用
