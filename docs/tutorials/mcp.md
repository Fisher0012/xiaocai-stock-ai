# Claude Desktop / Cursor 用小财 · 3 分钟

## 一次搞定

```bash
git clone https://github.com/Fisher0012/xiaocai-stock-ai ~/xiaocai
cd ~/xiaocai && pip install -r requirements.txt
```

打开配置文件, 把下面这段粘进去 (替换两个 key + 你的用户名):

- **Mac**: `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`

```json
{
  "mcpServers": {
    "xiaocai-stock-ai": {
      "command": "python3",
      "args": ["/Users/你的用户名/xiaocai/serve_mcp.py"],
      "env": {
        "DEEPSEEK_API_KEY": "sk-xxx",
        "TUSHARE_TOKEN": "tsxxx"
      }
    }
  }
}
```

⌘Q 完全退出 Claude Desktop, 重新打开, 问 "帮我看看茅台"。

## 从哪拿 key

- **DeepSeek** (LLM): https://platform.deepseek.com — 新用户送 10 元额度
- **Tushare** (数据): https://tushare.pro — 免费, 注册即可

<details>
<summary>💥 遇到问题?</summary>

- `command not found: git` → Mac 装 `xcode-select --install`; Windows 装 [git-scm.com](https://git-scm.com/download/win)
- `command not found: pip` → 用 `pip3` 代替
- Claude 里没反应 → JSON 语法错(缺逗号/引号没配对), 对照上面示例检查
- 报 `missing DEEPSEEK_API_KEY` → key 前后有空格; 或 Claude 没完全 ⌘Q 退出(要退出应用, 不是关窗口)
- 首次响应慢(30 秒+) → 正常, 预热完之后 10-15 秒
- 报 `command not found: python3` (Windows) → JSON 里 `"command": "python3"` 改成 `"python"`

Cursor / Continue / Cline / Windsurf 用户: 配置文件位置不同, 结构一样, 加到对应 mcpServers 配置里即可。

</details>

有问题 → [Issue](https://github.com/Fisher0012/xiaocai-stock-ai/issues) 或 [飞书群](../../README.md#-一起玩)
