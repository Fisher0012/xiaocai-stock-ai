# 飞书群机器人接入示例

30 分钟把 xiaocai-stock-ai 接进飞书群, 群友 @机器人 就能用。

## 前置

1. **飞书自建应用**(免费): [开发者后台](https://open.feishu.cn/app) 创建应用, 拿到 `APP_ID` + `APP_SECRET`
2. **应用权限**: 开 `im:message`, `im:message.group_at_msg`, `im:message:send_as_bot`, `im:chat`
3. **事件订阅**: 打开"接收消息"事件, 选**长连接**模式(无需公网 IP)
4. **添加机器人到群**: 应用后台 → 机器人 → 启用 → 邀请到你想跑的群

## 安装

```bash
git clone https://github.com/Fisher0012/xiaocai-stock-ai
cd xiaocai-stock-ai/examples/feishu-bot
pip install lark-oapi httpx
cp config.example.json config.json
# 编辑 config.json 填 APP_ID + APP_SECRET
python3 bot.py
```

## xiaocai 引擎两种接入方式

**方式 A: 用官方演示服务(零部署, 有限流)**

`config.json` 保持默认 `"XIAOCAI_API_ENDPOINT": "https://xiaocai.sque.site/api/ask"` 即可。演示服务每 IP 每天 20 次上限, 适合小群试玩。

**方式 B: 自部署引擎(推荐生产)**

先起 xiaocai-stock-ai 服务(见项目根 README):

```bash
cd ../..
docker-compose up -d       # 或 python3 serve_http.py
```

然后把 `config.json` 里的 `XIAOCAI_API_ENDPOINT` 改成你自己的:

```json
"XIAOCAI_API_ENDPOINT": "http://localhost:8080/api/ask"
```

## 用法(群里)

- **群聊**: `@机器人 中际旭创能上吗` — 必须 @, 普通聊天不打扰
- **私聊**: 直接发消息, 不用 @
- **追问**: 15 分钟内直接 @机器人 继续问, 记得上一轮

## 生产建议

- PM2 常驻: `pm2 start bot.py --interpreter python3 --name xiaocai-bot`
- systemd unit 见项目 `docs/DEPLOY.md`
- 日志按天切: `python3 bot.py >> /var/log/xiaocai-bot-$(date +%F).log 2>&1`

## 常见问题

- **机器人没回复**: 检查 `bot_open_id` 是否获取成功(启动日志), 权限是否给全
- **说"限流"**: 演示服务限流, 换自部署或减少提问频率
- **答非所问**: 更新到最新版, 引擎在持续改进; 或提 issue

问题反馈: [GitHub Issues](https://github.com/Fisher0012/xiaocai-stock-ai/issues)
