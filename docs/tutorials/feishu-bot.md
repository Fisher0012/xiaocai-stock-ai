# 接进飞书群, 群友 @机器人 就能用 · 30 分钟教程

装完之后, 你飞书群里的人 @你的机器人, 就能得到小财的分析。就像我自己的群一样(每天真实群问答可到 [飞书群](../../README.md#-一起玩) 看)。

---

## 前置

- 你有一个飞书账号 (个人号即可, 免费)
- 你想让机器人在的那个飞书群
- 一台电脑或服务器 (机器人要 24 小时跑, 可以是你自己的 Mac / Windows / 或云服务器)
- Python 3.10+ 和 git

---

## Step 1 · 创建飞书自建应用 (5 分钟)

小财机器人的身份是"你自己创建的飞书自建应用"。

1. 打开 https://open.feishu.cn/app
2. 点 **创建企业自建应用**
3. 应用名填 "小财" (或你想要的名字), Logo 随便传
4. 创建后, 进入应用详情页, 你会看到:
   - **App ID** (`cli_xxx`)
   - **App Secret** (点"查看"能复制)

**先把这两个记事本存着**, 后面配置要用。

---

## Step 2 · 开启机器人能力 + 权限 (3 分钟)

在应用后台:

1. 左侧 **添加应用能力** → 找到 **机器人** → 点 **添加**
2. 左侧 **权限管理** → 搜索并勾选以下权限:
   - `im:message` (读消息)
   - `im:message.group_at_msg` (读群里 @ 消息)
   - `im:message:send_as_bot` (以机器人身份发消息)
   - `im:chat` (读群信息)
3. 左侧 **事件订阅** → **添加事件** → 搜索并勾选 `im.message.receive_v1` (收到消息事件)
4. 左侧 **事件订阅** → 顶部选 **长连接** 模式 (无需公网 IP, 你在自己电脑上跑就行)
5. 顶部导航 **版本管理与发布** → **创建版本** → 简单填一下说明 → **申请发布** → 通常自建应用秒过

---

## Step 3 · 把机器人加到你的群 (30 秒)

打开你的飞书群 → 右上角 **⋯** → **群机器人** → **添加机器人** → 找到你刚建的应用 → 添加。

现在群里能看到"小财已加入"。

---

## Step 4 · 拿两把 key (各 3 分钟, 都免费)

小财的引擎需要:
- **DeepSeek key**: 打开 https://platform.deepseek.com → 注册 → API Keys → 创建 → 复制 (新用户送 10 元)
- **Tushare token**: 打开 https://tushare.pro → 注册 → 个人主页 → 复制 "接口 TOKEN"

---

## Step 5 · 下载 bot 代码 + 装依赖 (2 分钟)

在你要跑 bot 的那台电脑上:

```bash
git clone https://github.com/Fisher0012/xiaocai-stock-ai ~/xiaocai
cd ~/xiaocai/examples/feishu-bot
pip install lark-oapi httpx
```

**你会看到**: 终端输出 `Cloning...done.` 然后 pip 装完 `Successfully installed`。

---

## Step 6 · 选一种"引擎运行方式" (2 分钟)

小财 bot 需要一个"引擎"来做分析。两种选择:

### 方式 A · 用官方演示服务 (推荐先跑起来)

不用自己部署, 直接用我们的演示服务 `xiaocai.sque.site`。**限制**: 每 IP 每天 20 次, 适合小群试玩。

### 方式 B · 自部署引擎 (推荐生产用)

再开一个终端窗口, 跑:

```bash
cd ~/xiaocai
cp .env.example .env
# 编辑 .env, 填上面 Step 4 的两把 key
docker-compose up -d
```

引擎会在 `http://localhost:8080` 跑。**没有 20 次上限, 但烧的是你自己的 DeepSeek 额度**。

---

## Step 7 · 配置 bot 并启动 (2 分钟)

```bash
cd ~/xiaocai/examples/feishu-bot
cp config.example.json config.json
```

用文本编辑器打开 `config.json`, 改这 3 处:

```json
{
  "APP_ID": "把 Step 1 复制的 App ID 填这",
  "APP_SECRET": "把 Step 1 复制的 App Secret 填这",
  "XIAOCAI_API_ENDPOINT": "https://xiaocai.sque.site/api/ask"
}
```

如果选了 **方式 B (自部署)**, 把 `XIAOCAI_API_ENDPOINT` 改成 `http://localhost:8080/api/ask`。

保存, 启动 bot:

```bash
python3 bot.py
```

**你会看到**: 终端输出 `[feishu-bot] 启动, 引擎: xxx, bot_open_id: 已获取` 然后就等着接消息。

---

## Step 8 · 群里试一下

在你的飞书群里发一条:

> @小财 中际旭创能上吗

**你会看到**:
1. 秒回 "好的，马上分析"
2. 15 秒后, 一段带 BIAS、主力资金、操作建议、止损位的分析

**看到这个就成功了 🎉**

---

## 让 bot 24 小时不掉线

你 Mac 关机 bot 就停了。生产建议:

### 方案 A · PM2 常驻 (Mac / Linux 都行)

```bash
npm install -g pm2  # 装 pm2
pm2 start bot.py --interpreter python3 --name xiaocai-bot
pm2 save
pm2 startup   # 按提示做一次, 之后开机自启
```

### 方案 B · 部署到云服务器

买一台便宜的云服务器 (腾讯云轻量应用服务器 60 元/年那种就够), scp 代码上去, systemd 常驻。详见 [DEPLOY.md](../DEPLOY.md)。

---

## 💥 常见问题

**Q: 机器人没回复**
A: 检查 bot 启动日志有没有 `bot_open_id: 已获取`, 没获取到就是 App Secret 填错或权限没开全。

**Q: 说 "限流"**
A: 用了演示服务, 每 IP 每天 20 次。换自部署 (Step 6 方式 B) 或减少提问频率。

**Q: 群里 @小财 没反应, 但看得到"已加入"**
A: 应用版本没发布, 回 Step 2 最后一步"申请发布"。

**Q: 报 `lark_oapi 无法导入`**
A: `pip install lark-oapi` 单独装一次, 或者用 `pip3`。

**Q: 我不想每次都 @, 追问能直接问吗**
A: 15 分钟内直接 @小财 接着问就行 (bot 有会话记忆)。想追更早的对话, 点 "回复引用" 小财某条消息再 @。

---

## 用起来之后

- 别把机器人放太多群, 会烧额度
- 群消息安全: bot 不会主动读群历史消息, 只处理明确 @ 它的消息
- 想改 ACK 话术 / 免责尾注: 编辑 `config.json` 里的 `ACK_REPLY` 和 `DISCLAIMER`
- 想改人设 (直男/温和/正式等): 编辑 `~/xiaocai/core/persona.py` (先备份原文件)

有问题 → [提 Issue](https://github.com/Fisher0012/xiaocai-stock-ai/issues) 或 [加飞书群](../../README.md#-一起玩)
