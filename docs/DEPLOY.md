# 部署文档

三种部署方式, 按你的实际场景选。

## 方式 1: Docker(推荐, 90% 场景)

```bash
git clone https://github.com/Fisher0012/xiaocai-stock-ai
cd xiaocai-stock-ai
cp .env.example .env
# 编辑 .env, 填 DEEPSEEK_API_KEY 和 TUSHARE_TOKEN
docker-compose up -d
# 验证
curl http://localhost:8080/health
```

修改代码后:
```bash
docker-compose up -d --build
```

查看日志:
```bash
docker-compose logs -f
```

## 方式 2: 裸机 Python(开发调试用)

```bash
git clone https://github.com/Fisher0012/xiaocai-stock-ai
cd xiaocai-stock-ai
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# 编辑 .env
python3 serve_http.py
```

## 方式 3: systemd 常驻(生产)

```bash
# 假设代码在 /opt/xiaocai-stock-ai
sudo tee /etc/systemd/system/xiaocai.service > /dev/null << 'EOF'
[Unit]
Description=xiaocai-stock-ai HTTP API
After=network.target

[Service]
Type=simple
User=xiaocai
WorkingDirectory=/opt/xiaocai-stock-ai
EnvironmentFile=/opt/xiaocai-stock-ai/.env
ExecStart=/usr/bin/python3 -m uvicorn serve_http:app --host 127.0.0.1 --port 8080
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable --now xiaocai
sudo systemctl status xiaocai
```

## nginx 反代 + HTTPS

```nginx
server {
    listen 443 ssl http2;
    server_name xiaocai.your-domain.com;

    ssl_certificate /etc/letsencrypt/live/xiaocai.your-domain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/xiaocai.your-domain.com/privkey.pem;

    # 引擎单次 10-60s, 超时放宽
    proxy_read_timeout 180s;
    proxy_send_timeout 180s;

    location / {
        proxy_pass http://127.0.0.1:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto https;
    }
}
```

Let's Encrypt 证书:
```bash
sudo certbot --nginx -d xiaocai.your-domain.com
```

## 演示服务模式(仅官方部署需要)

`.env` 里额外加:
```bash
XIAOCAI_DEMO_MODE=1
XIAOCAI_DEMO_DAILY_LIMIT=20
XIAOCAI_DEMO_MINUTE_LIMIT=3
```

启用后每个 IP 有限流保护, 防被撸崩。自部署实例**不建议开**(自用不用限自己)。

## 常见问题

- **端口冲突**: `HTTP_PORT=8081` 换端口
- **国内访问 OpenAI**: 用 DeepSeek 即可, 或 `OPENAI_BASE_URL` 指向国内代理
- **Tushare 积分不够**: 部分财务接口需要 Tushare Pro 积分(2000+), 免费账号只能用基础接口
- **首次启动慢**: 首次调用 tushare 会拉几秒, 后续走缓存
