# Claude Desktop / Cursor 用小财 · 3 分钟

配置好之后, 你在 Claude 里说"帮我看看茅台", 它会自动调小财返回带数据支撑的分析。

## Step 1 · 先拿两把 key(免费)

- **DeepSeek key**: 打开 https://platform.deepseek.com → 用手机号注册 → 左侧 API Keys → 点"创建 API Key" → 复制那串 `sk-xxxx...`(先记事本存着, 新用户送 10 元额度)
- **Tushare token**: 打开 https://tushare.pro → 手机号注册 → 右上角头像点进个人主页 → 页面上的 "接口 TOKEN" 一长串 → 复制

两把 key 都拿到, 继续下一步。

## Step 2 · 下载小财到你电脑

打开终端(Mac: Launchpad 搜"终端"; Windows: 开始菜单搜"PowerShell"), 一次复制下面 2 行, 粘贴回车:

```bash
git clone https://github.com/Fisher0012/xiaocai-stock-ai ~/xiaocai
cd ~/xiaocai && pip install -r requirements.txt
```

看到最后一行输出 `Successfully installed ...` 就是装好了。

## Step 3 · 让 Claude Desktop 认识小财

需要编辑 Claude Desktop 的配置文件, 位置:

- **Mac**: `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`

**最省事的方法**(Mac): 终端里粘贴这行, 用系统自带 TextEdit 打开:

```bash
open -e ~/Library/Application\ Support/Claude/claude_desktop_config.json
```

Windows 用记事本: 开始菜单搜"运行" → 输入 `notepad %APPDATA%\Claude\claude_desktop_config.json` → 回车。

**如果文件是空的或第一次打开**, 把下面这一整段粘进去:

```json
{
  "mcpServers": {
    "xiaocai-stock-ai": {
      "command": "python3",
      "args": ["/Users/你的用户名/xiaocai/serve_mcp.py"],
      "env": {
        "DEEPSEEK_API_KEY": "sk-你刚才复制的DeepSeek key",
        "TUSHARE_TOKEN": "你刚才复制的Tushare token"
      }
    }
  }
}
```

**必须改的 3 处**:
1. `你的用户名` 换成你 Mac 的实际用户名(终端跑 `whoami` 能看到)。Windows 用户把整个 `/Users/你的用户名/xiaocai/serve_mcp.py` 换成 `C:\Users\你的用户名\xiaocai\serve_mcp.py`
2. `sk-你刚才复制的...` 换成 Step 1 的 DeepSeek key
3. `你刚才复制的Tushare token` 换成 Step 1 的 Tushare token

**如果文件里已经有其他 mcpServers 配置**, 把 `xiaocai-stock-ai` 这段合并进去别覆盖别的。

⌘S 保存(Windows Ctrl+S), 关闭编辑器。

## Step 4 · 重启 Claude Desktop 问一句

**Mac**: 按 ⌘Q **完全退出** Claude(注意: 不是点关闭窗口, 是退出整个应用), 从 Launchpad 重新打开。
**Windows**: 系统托盘图标右键退出, 重新打开。

在 Claude 对话框输入:

> 帮我看看茅台

Claude 应该会主动说"我调用一下 xiaocai_ask 工具", 15 秒左右返回带 BIAS、主力资金、操作建议、止损位的完整分析。**看到这个就成功了 🎉**

---

## 从此可以问什么

- 个股: `中际旭创能上吗`
- 板块: `光通信板块怎么样`
- 选股: `从半导体设备里选 3 只`
- 选板块: `给我 3 个明天可以买的细分板块`
- 对比: `中际旭创和新易盛哪个强`
- 追问: 15 分钟内直接接着问, 不用重复股票名

<details>
<summary>💥 遇到问题?</summary>

- **命令行报 `command not found: git`** → 先装 git: Mac 粘贴 `xcode-select --install`; Windows 装 [git-scm.com](https://git-scm.com/download/win)
- **`command not found: pip`** → 用 `pip3` 代替
- **Claude 里没反应, 也没提工具** → 大概率 JSON 语法错(缺逗号/引号没配对), 复制文件内容到 [jsonlint.com](https://jsonlint.com) 校验一下
- **报 `missing DEEPSEEK_API_KEY`** → env 里 key 前后有空格, 或者 Claude Desktop 没完全 ⌘Q 退出(必须是退出应用, 不是关窗口)
- **报 `command not found: python3`**(Windows) → JSON 里 `"command": "python3"` 改成 `"command": "python"`
- **首次响应慢(30 秒+)** → 正常, 预热完之后 10-15 秒

**Cursor / Continue / Cline / Windsurf** 用户: 配置文件位置不同(各自官方文档能查), 但 JSON 结构一样, 把上面这段 `xiaocai-stock-ai` 加到对应 mcpServers 配置里即可。

</details>

有问题 → [Issue](https://github.com/Fisher0012/xiaocai-stock-ai/issues) 或 [飞书群](../../README.md#-一起玩)
