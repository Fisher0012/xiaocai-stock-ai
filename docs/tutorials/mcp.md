# 让 Claude Desktop / Cursor / Continue 用小财 · 3 分钟教程

MCP (Model Context Protocol) 是 Anthropic 定义的标准协议, 一次配置, **Claude Desktop / Cursor / Continue / Cline / Windsurf 等**都能用。

配置好之后, 你只要在对话里说 "帮我看看茅台"、"给我 3 个可以买的板块", Claude 会自动调用小财, 返回带数据支撑的分析。

---

## 前置

你需要有以下之一(选你日常在用的):
- Claude Desktop (最推荐, [下载](https://claude.ai/download))
- Cursor / Continue / Cline / Windsurf 等其他 MCP 客户端

还需要:
- Python 3.10 或以上 (Mac 系统自带 python3; Windows 用户 [下载](https://www.python.org/downloads/))
- git (Mac 用户在终端粘贴 `xcode-select --install`; Windows [下载](https://git-scm.com/download/win))

---

## Step 1 · 下载代码到你电脑 (30 秒)

在终端里粘贴一行:

```bash
git clone https://github.com/Fisher0012/xiaocai-stock-ai ~/xiaocai-stock-ai
```

**你会看到**: 终端输出 `Cloning into '~/xiaocai-stock-ai'...` 然后是 `done.`

**如果报错 `command not found: git`**: 你需要先装 git, 按上面前置说明装。

---

## Step 2 · 装依赖 (1 分钟)

```bash
cd ~/xiaocai-stock-ai
pip install -r requirements.txt
```

**你会看到**: 终端滚一屏 pip 装包信息, 最后是 `Successfully installed ...`

**如果报错 `command not found: pip`**: 换成 `pip3 install -r requirements.txt`

---

## Step 3 · 拿两把 key (各 3 分钟, 都免费)

### DeepSeek Key (LLM 用)

1. 打开 https://platform.deepseek.com
2. 注册账号 (手机号即可)
3. 左侧菜单 → **API Keys** → 点 **创建 API Key**
4. 复制那串 `sk-xxx...`, 先记事本存着

新用户免费送 10 元额度, 够小财用很久 (每次问答约 0.01 元)。

### Tushare Token (A 股数据用)

1. 打开 https://tushare.pro
2. 注册账号 (手机号即可)
3. 右上角头像 → **个人主页** → 找到 **接口 TOKEN**
4. 复制那串长字符串, 记事本存着

完全免费, 但部分高级财务数据需要积分 (2000+, 完善资料就能拿到)。基础问答不需要高级数据。

---

## Step 4 · 让 Claude Desktop 认识小财 (2 分钟)

### 找到配置文件

打开这个文件 (不存在就新建):

- **Mac**: `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`

Mac 快捷方式: 打开 Finder → 菜单栏 `前往` → `前往文件夹` → 粘贴上面的路径回车。

### 粘贴配置

把下面的内容整个粘贴到那个文件里 (**如果文件里已经有其他 `mcpServers`, 就把 `xiaocai-stock-ai` 这段合并进去, 不要覆盖别的**):

```json
{
  "mcpServers": {
    "xiaocai-stock-ai": {
      "command": "python3",
      "args": ["/Users/你的用户名/xiaocai-stock-ai/serve_mcp.py"],
      "env": {
        "DEEPSEEK_API_KEY": "sk-你的DeepSeek key",
        "TUSHARE_TOKEN": "你的Tushare token"
      }
    }
  }
}
```

**必须改的 3 处**:
1. `/Users/你的用户名/` 改成你 Mac 用户的实际路径 (在终端跑 `echo $HOME` 能看到)
2. `sk-你的DeepSeek key` 换成 Step 3 复制的 DeepSeek key
3. `你的Tushare token` 换成 Step 3 复制的 Tushare token

保存文件。

---

## Step 5 · 重启 Claude Desktop, 开问

**Mac**: `⌘Q` 完全退出 Claude (**不是关窗口, 是退出应用**), 重新打开。
**Windows**: 系统托盘右键退出, 重新打开。

在 Claude 对话框里输入:

> 帮我看看中际旭创

**你会看到**: Claude 会主动说 "我调用一下 xiaocai_ask 工具", 然后 15 秒左右, 返回一段带 BIAS、主力资金、操作建议、止损位的分析。

**看到这个就成功了 🎉**

---

## 💥 常见问题

**Q: Claude Desktop 里没反应, 也没提工具**
A: 大概率是 `claude_desktop_config.json` 语法错误 (少了逗号 / 引号没配对)。用在线 JSON 校验器检查一下, 或者对照上面的示例逐字看。

**Q: 报 `missing DEEPSEEK_API_KEY`**
A: env 那节的 key 没写对, 或者 Claude Desktop 没完全重启 (要 ⌘Q 退出而不是关窗口)。

**Q: 报 `command not found: python3`**
A: Windows 用户可能装的是 `python` 而不是 `python3`, 把 config.json 里的 `"command": "python3"` 改成 `"command": "python"`。

**Q: 第一次分析很慢 (30 秒+)**
A: 首次调用会预热 tushare + 拉数据, 之后 10-15 秒。正常。

**Q: 分析里说"数据不足"**
A: Tushare 免费账号有些接口需要积分, 完善你的个人资料页可以自动加积分, 到 2000+ 就够用大部分接口。

---

## Cursor / Continue 用户

配置文件位置不同, 但结构一样。参考各自官方文档的 MCP 配置章节, 把上面 Step 4 的 JSON 内容加到对应位置即可。

---

## 用起来之后

- 追问不用重复股票名, 15 分钟内直接接着问就行
- 除了个股, 还能问板块、选股、选板块、多股对比 — [看能力全景](../../README.md#它凭什么这么答)
- 有问题 → [提 Issue](https://github.com/Fisher0012/xiaocai-stock-ai/issues) 或 [加飞书群](../../README.md#-一起玩)
