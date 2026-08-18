# 接进飞书群 · 30 分钟

装完之后, 你飞书群里的人 @机器人, 它就返回小财的分析。

## Step 1 · 创建飞书自建应用

小财机器人的身份是"你自己创建的飞书自建应用"。

1. 打开 https://open.feishu.cn/app
2. 用飞书账号登录, 点 **创建企业自建应用**
3. 应用名填"小财"(或你想要的名字), Logo 可以随便传一张
4. 创建后进入应用详情页, 你会看到:
   - **App ID** (`cli_xxx` 一串)
   - **App Secret** (点"查看"按钮才显示, 复制它)

**这两个先记事本存着**, 后面 Step 6 要用。

## Step 2 · 开启机器人 + 配权限

在同一个应用后台:

1. 左侧菜单 **添加应用能力** → 找到 **机器人** → 点 **添加**
2. 左侧 **权限管理** → 上方搜索框, 逐个搜索并勾选这 4 个权限:
   - `im:message`
   - `im:message.group_at_msg`
   - `im:message:send_as_bot`
   - `im:chat`
3. 左侧 **事件订阅** → 上方 **添加事件** → 搜 `im.message.receive_v1` 勾选
4. **事件订阅** 页面顶部, 选 **长连接** 模式(选这个就不用公网服务器, 你自己电脑上跑就行)
5. 顶部导航 **版本管理与发布** → **创建版本** → 简单填一下说明 → **申请发布** → 自建应用通常秒过

## Step 3 · 把机器人加到你的群

打开你要用的飞书群 → 右上角 **⋯** → **群机器人** → **添加机器人** → 找到你刚建的应用 → **添加**

群里会显示"小财已加入群聊"。

## Step 4 · 先拿两把 key(免费)

- **DeepSeek key**: 打开 https://platform.deepseek.com → 手机号注册 → 左侧 API Keys → 创建 → 复制 `sk-xxxx...`
- **Tushare token**: 打开 https://tushare.pro → 手机号注册 → 右上角头像 → 个人主页复制 "接口 TOKEN"

## Step 5 · 下载 bot 代码 + 装依赖

打开终端(Mac: Launchpad 搜"终端"; Windows: 开始菜单搜"PowerShell"), 一次复制这 3 行粘贴回车:

```bash
git clone https://github.com/Fisher0012/xiaocai-stock-ai ~/xiaocai
cd ~/xiaocai/examples/feishu-bot
pip install lark-oapi httpx
```

看到 `Successfully installed ...` 就是装好了。

## Step 6 · 填配置文件

继续在同一个终端粘:

```bash
cp config.example.json config.json
open -e config.json    # Mac 用 TextEdit 打开
# Windows 用: notepad config.json
```

文件会显示一段 JSON, 找到这 3 行, 把值改成你自己的:

```json
"APP_ID": "把 Step 1 复制的 App ID 填这",
"APP_SECRET": "把 Step 1 复制的 App Secret 填这",
"XIAOCAI_API_ENDPOINT": "https://xiaocai.sque.site/api/ask"
```

**第 3 行说明**: 保持默认(用官方演示服务)每 IP 每天 20 次限流, 适合小群试玩; 要没限流请看 Step 8。

⌘S 保存(Windows Ctrl+S), 关闭编辑器。

## Step 7 · 启动 bot 并在群里试一下

终端里粘:

```bash
python3 bot.py
```

**你会看到**:
```
[feishu-bot] 启动, 引擎: https://xiaocai.sque.site/api/ask, bot_open_id: 已获取
```

然后 bot 就在等消息。**这个终端窗口别关**, 关了 bot 就停。

打开你的飞书群, 发一条:

> @小财 中际旭创能上吗

**你会看到**:
1. bot 秒回 "好的，马上分析"
2. 15 秒后回一段带 BIAS、主力资金、操作建议、止损位的完整分析

**看到这个就成功了 🎉**

## Step 8(可选) · 想去掉演示服务的限流 → 自部署引擎

如果你觉得 20 次/天不够用, 参考 [自部署教程](self-deploy.md) 起一个自己的引擎(docker-compose up -d, 5 分钟)。然后回 Step 6 把 `config.json` 的 `XIAOCAI_API_ENDPOINT` 改成 `http://localhost:8080/api/ask`, 重启 bot 即可(在 bot 终端按 Ctrl+C 停, 再跑 `python3 bot.py`)。

## Step 9(可选) · 让 bot 24 小时不掉线

Step 7 的方式关电脑或关终端 bot 就停了。生产建议用 pm2:

```bash
npm install -g pm2
cd ~/xiaocai/examples/feishu-bot
pm2 start bot.py --interpreter python3 --name xiaocai-bot
pm2 save && pm2 startup
# 最后一行按提示做一次就行, 之后开机自启
```

或者部署到云服务器, systemd 常驻, 见 [DEPLOY.md](../DEPLOY.md)。

<details>
<summary>💥 遇到问题?</summary>

- **bot 启动日志说 `bot_open_id: 获取失败`** → App Secret 填错, 或 Step 2 的权限没开全
- **群里 @小财 没反应, 群里看得到"已加入"** → 应用没发布, 回 Step 2 最后一步"申请发布"
- **说 "限流"** → 演示服务每 IP 每天 20 次, 换自部署(Step 8)
- **报 `lark_oapi 无法导入`** → 单独跑 `pip install lark-oapi`(或 pip3)
- **追问不用 @ 也能问?** → 15 分钟内直接 @小财 接着问就行, bot 记得上一轮
- **想改 ACK 话术("好的，马上分析")** → 编辑 `config.json` 里的 `ACK_REPLY`
- **想改人设(直男/温和/正式)** → 编辑 `~/xiaocai/core/persona.py`(先备份)

</details>

有问题 → [Issue](https://github.com/Fisher0012/xiaocai-stock-ai/issues) 或 [飞书群](../../README.md#-一起玩)
