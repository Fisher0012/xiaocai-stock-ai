# Docker 自部署 · 5 分钟

自部署的好处: **没有限流**、数据不经过第三方。5 分钟一次搞定。

## Step 0 · 先装 Docker(如果还没装)

Docker 是一个"一键起服务"的工具。装完之后, 一行命令就能起小财。

- **Mac**: 下载 [Docker Desktop for Mac](https://docs.docker.com/desktop/install/mac-install/) → 双击安装 → 启动 → 状态栏出现 🐳 图标就是装好了
- **Windows**: 下载 [Docker Desktop for Windows](https://docs.docker.com/desktop/install/windows-install/) → 双击安装 → 启动 → 系统托盘出现 🐳 图标
- **Linux**: [官方安装](https://docs.docker.com/engine/install/)

装好后, 终端跑 `docker --version` 能看到版本号就算成功。

## Step 1 · 先拿两把 key(免费)

- **DeepSeek key**: 打开 https://platform.deepseek.com → 用手机号注册 → 左侧 API Keys → 点"创建 API Key" → 复制那串 `sk-xxxx...`(新用户送 10 元额度, 够用很久)
- **Tushare token**: 打开 https://tushare.pro → 手机号注册 → 右上角头像点进个人主页 → 页面上的 "接口 TOKEN" 一长串 → 复制

两把 key 都拿到, 继续下一步。

## Step 2 · 下载小财代码

打开终端(Mac: Launchpad 搜"终端"; Windows: 开始菜单搜"PowerShell"), 一次复制下面 3 行, 粘贴回车:

```bash
git clone https://github.com/Fisher0012/xiaocai-stock-ai
cd xiaocai-stock-ai
cp .env.example .env
```

看到没报错就是拉下来了, 会在当前目录出现 `xiaocai-stock-ai` 文件夹。

## Step 3 · 把 key 填进配置文件

刚才那一步生成了一个 `.env` 文件, 需要用文本编辑器打开填 key。

**最省事的方法**: 终端里继续粘贴这行, 用 Mac 自带的 TextEdit 打开:

```bash
open -e .env    # Mac
# Windows 用: notepad .env
```

文件里能看到这两行(可能夹在注释中间):

```
DEEPSEEK_API_KEY=
TUSHARE_TOKEN=
```

把 Step 1 复制的两把 key 粘到等号后面, 变成:

```
DEEPSEEK_API_KEY=sk-你刚才复制的那串
TUSHARE_TOKEN=你刚才复制的那串token
```

⌘S 保存(Windows Ctrl+S), 关闭编辑器。

## Step 4 · 一行命令起服务

终端里(确认还在 xiaocai-stock-ai 目录, 如果不是先 `cd xiaocai-stock-ai`), 粘贴回车:

```bash
docker-compose up -d
```

**首次启动 2-3 分钟**(要下载镜像+装 pandas 等大包), 之后重启秒起。最后看到 `Container xiaocai-stock-ai Started` 就是起好了。

## Step 5 · 验证服务真的活着

在同一个终端继续跑:

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

15 秒后返回一大段 JSON, `answer` 字段里就是完整分析。**看到这个就成功了 🎉**

---

## 常用管理命令

```bash
docker-compose logs -f          # 看实时日志(Ctrl+C 退出查看, 不影响服务)
docker-compose restart          # 重启服务
docker-compose down             # 停服务
docker-compose up -d --build    # 更新代码后重新构建
```

## 想在公网跑(HTTPS 域名)

nginx 反代示例见 [DEPLOY.md](../DEPLOY.md), 需要一个域名 + Let's Encrypt 证书。

<details>
<summary>💥 遇到问题?</summary>

- **`docker: command not found`** → 回 Step 0 装 Docker Desktop, 装完启动它(状态栏有 🐳 图标才算启动)
- **端口 8080 被占** → 编辑 `.env` 加一行 `HTTP_PORT=8081`, 重新 `docker-compose up -d`
- **报 `TUSHARE_TOKEN not set`** → 改完 .env 要 `docker-compose down` 然后 `docker-compose up -d`(不重启读不到新变量)
- **`docker-compose` 命令找不到** → 新版 Docker 是 `docker compose`(中间空格), 换一下试
- **首次启动很慢** → 装 pandas/tushare 等大包要几分钟, 只有第一次, 正常
- **部分财务分析说"数据不足"** → Tushare 免费账号高级接口需要积分, 完善个人资料自动加到 2000+ 就够用

</details>

有问题 → [Issue](https://github.com/Fisher0012/xiaocai-stock-ai/issues) 或 [飞书群](../../README.md#-一起玩)
