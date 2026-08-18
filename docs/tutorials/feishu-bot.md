# 接进飞书群 · 30 分钟

装完之后, 群友 @机器人 就能用小财。

## 前置准备

**1. 创建飞书自建应用** ([开发者后台](https://open.feishu.cn/app) → 创建企业自建应用):

- 应用名: 小财 (随意)
- 拿到 `App ID` (`cli_xxx`) 和 `App Secret`

**2. 开启机器人 + 权限**:

- 左侧 **添加应用能力** → **机器人** → 添加
- 左侧 **权限管理** 勾选: `im:message`, `im:message.group_at_msg`, `im:message:send_as_bot`, `im:chat`
- 左侧 **事件订阅** → 添加事件 `im.message.receive_v1` → 顶部选 **长连接** 模式
- 顶部 **版本管理与发布** → 创建版本 → 申请发布 (通常秒过)

**3. 把机器人加到群**: 群里右上角 ⋯ → 群机器人 → 添加你刚建的应用

**4. 拿两把 key**: [DeepSeek](https://platform.deepseek.com) + [Tushare](https://tushare.pro)

## 一次搞定

```bash
git clone https://github.com/Fisher0012/xiaocai-stock-ai ~/xiaocai
cd ~/xiaocai/examples/feishu-bot
pip install lark-oapi httpx
cp config.example.json config.json
```

编辑 `config.json` 填 3 项:

```json
{
  "APP_ID": "cli_你的App ID",
  "APP_SECRET": "你的App Secret",
  "XIAOCAI_API_ENDPOINT": "https://xiaocai.sque.site/api/ask"
}
```

启动:

```bash
python3 bot.py
```

群里 `@小财 中际旭创能上吗` 试试。

## 想去掉演示服务的限流

再开一个终端跑 `docker-compose up -d` [自部署引擎](self-deploy.md), 然后把 `config.json` 里的 `XIAOCAI_API_ENDPOINT` 改成 `http://localhost:8080/api/ask`。

## 24 小时不掉线

```bash
npm install -g pm2
pm2 start bot.py --interpreter python3 --name xiaocai-bot
pm2 save && pm2 startup
```

或部署到云服务器, systemd 常驻, 见 [DEPLOY.md](../DEPLOY.md)。

<details>
<summary>💥 遇到问题?</summary>

- bot 启动日志 `bot_open_id: 获取失败` → App Secret 填错 or 权限没开全
- 群里 @小财 没反应 → 应用没发布, 回前置第 2 步"申请发布"
- 说 "限流" → 演示服务每 IP 每天 20 次, 换自部署
- 追问不用 @ 也能问? → 15 分钟内直接 @小财 接着问就行 (bot 有会话记忆)
- 想改 ACK 话术 / 免责尾注 → 编辑 `config.json` 里的 `ACK_REPLY` 和 `DISCLAIMER`
- 想改人设 (直男/温和/正式) → 编辑 `~/xiaocai/core/persona.py` (先备份)

</details>

有问题 → [Issue](https://github.com/Fisher0012/xiaocai-stock-ai/issues) 或 [飞书群](../../README.md#-一起玩)
