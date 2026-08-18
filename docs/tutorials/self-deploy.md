# Docker 自部署 · 5 分钟

## 一次搞定

```bash
git clone https://github.com/Fisher0012/xiaocai-stock-ai
cd xiaocai-stock-ai
cp .env.example .env
```

编辑 `.env` 填两把 key:

```
DEEPSEEK_API_KEY=sk-xxx
TUSHARE_TOKEN=tsxxx
```

一行起服务:

```bash
docker-compose up -d
```

验证:

```bash
curl http://localhost:8080/health
# 应返回 {"ok":true,"version":"1.0.0","model":"deepseek-chat"}

curl -X POST http://localhost:8080/api/ask \
  -H "Content-Type: application/json" \
  -d '{"question":"中际旭创能上吗"}'
```

## 从哪拿 key

- **DeepSeek**: https://platform.deepseek.com — 新用户送 10 元
- **Tushare**: https://tushare.pro — 免费注册

## 常用命令

```bash
docker-compose logs -f          # 看日志
docker-compose restart          # 重启
docker-compose down             # 停服务
docker-compose up -d --build    # 更新代码后重建
```

<details>
<summary>💥 遇到问题?</summary>

- 首次启动 2-3 分钟 → 正常, 装 pandas/tushare 大包, 之后重启秒起
- 端口 8080 被占 → `.env` 加 `HTTP_PORT=8081`, 重启
- 报 `TUSHARE_TOKEN not set` → 改完 .env 要 `docker-compose down && up -d`
- 部分财务分析说"数据不足" → Tushare 免费账号高级接口需要积分, 完善资料自动加到 2000+ 就够用

</details>

## 生产环境 (公网 HTTPS)

nginx 反代示例见 [DEPLOY.md](../DEPLOY.md)。

有问题 → [Issue](https://github.com/Fisher0012/xiaocai-stock-ai/issues) 或 [飞书群](../../README.md#-一起玩)
