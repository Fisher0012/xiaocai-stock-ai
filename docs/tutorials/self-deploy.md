# 自己部署整套小财服务 · 5 分钟教程

自部署有两个好处: **没有限流**, **数据不经过第三方**。

推荐用 Docker, 最简单。

---

## 前置

- 一台电脑 (Mac / Linux / Windows 都行) 或一台服务器
- 装了 Docker (还没装? [Mac](https://docs.docker.com/desktop/install/mac-install/) / [Windows](https://docs.docker.com/desktop/install/windows-install/) / [Linux](https://docs.docker.com/engine/install/))
- 装了 git

---

## Step 1 · 拿两把 key (5 分钟, 都免费)

- **DeepSeek key**: 打开 https://platform.deepseek.com → 注册 → API Keys → 创建 → 复制 (新用户送 10 元额度, 够用很久)
- **Tushare token**: 打开 https://tushare.pro → 注册 → 个人主页 → 复制 "接口 TOKEN"

---

## Step 2 · 下载代码 + 配置 (2 分钟)

```bash
git clone https://github.com/Fisher0012/xiaocai-stock-ai
cd xiaocai-stock-ai
cp .env.example .env
```

用文本编辑器打开 `.env`, 填两把 key:

```bash
DEEPSEEK_API_KEY=sk-你的DeepSeek key
TUSHARE_TOKEN=你的Tushare token
```

其他保持默认即可。保存。

---

## Step 3 · 一行命令起服务 (2 分钟)

```bash
docker-compose up -d
```

**你会看到**: Docker 拉镜像 + 装依赖 + 启动容器, 最后输出 `Container xiaocai-stock-ai Started`

**首次启动约 2-3 分钟** (要装 pandas/tushare 等大包), 之后重启秒起。

---

## Step 4 · 验证服务

```bash
curl http://localhost:8080/health
```

**你会看到**: `{"ok":true,"version":"1.0.0","model":"deepseek-chat"}`

实际问一句:

```bash
curl -X POST http://localhost:8080/api/ask \
  -H "Content-Type: application/json" \
  -d '{"question":"中际旭创能上吗"}'
```

**你会看到**: 15 秒后, 返回一个 JSON, `answer` 字段是完整的分析。

**看到这个就成功了 🎉**

---

## 常用管理命令

```bash
docker-compose logs -f          # 看日志 (Ctrl+C 退出)
docker-compose restart          # 重启
docker-compose down             # 停服务
docker-compose up -d --build    # 更新代码后重新构建
```

---

## 生产建议

想在公网跑, 加 nginx 反代 HTTPS:

```nginx
server {
    listen 443 ssl http2;
    server_name xiaocai.你的域名.com;
    ssl_certificate /etc/letsencrypt/live/xiaocai.你的域名.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/xiaocai.你的域名.com/privkey.pem;

    proxy_read_timeout 180s;
    proxy_send_timeout 180s;

    location / {
        proxy_pass http://127.0.0.1:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}
```

Let's Encrypt 证书: `sudo certbot --nginx -d xiaocai.你的域名.com`

完整方案见 [DEPLOY.md](../DEPLOY.md)。

---

## 💥 常见问题

**Q: 端口 8080 被占**
A: 编辑 `.env` 加一行 `HTTP_PORT=8081`, 然后 `docker-compose up -d`。

**Q: 首次启动很慢**
A: 装 pandas/tushare 等大包要几分钟, 只有第一次。之后重启秒起。

**Q: 报 `TUSHARE_TOKEN not set`**
A: `.env` 文件的 key 没填, 或者 docker-compose 没重启 (改完 .env 要 `docker-compose down && up -d`)。

**Q: 部分财务分析说"数据不足"**
A: Tushare 免费账号有些高级接口需要积分, 完善个人主页资料可以自动加积分, 2000+ 就够用大部分。

**Q: 想让其他机器也能调用**
A: 默认 `docker-compose.yml` 已经暴露到 0.0.0.0:8080, 内网直接用 `http://这台机器IP:8080`。公网需要加 nginx HTTPS 反代 (见上)。

---

## 用起来之后

服务跑起来后, 任何一种方式都能接:
- [接进飞书群](feishu-bot.md) (改 `XIAOCAI_API_ENDPOINT` 为你的地址)
- [接进 Coze / Kimi](coze-kimi.md)
- [MCP 客户端](mcp.md) 也可以通过 HTTP 方式访问
- [自己写 Python agent](python-sdk.md)

有问题 → [提 Issue](https://github.com/Fisher0012/xiaocai-stock-ai/issues) 或 [加飞书群](../../README.md#-一起玩)
