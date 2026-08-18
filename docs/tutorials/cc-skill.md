# Claude Code 用小财 · 30 秒

## 一次搞定

```bash
git clone https://github.com/Fisher0012/xiaocai-stock-ai ~/.claude/skills/xiaocai-stock-ai
cd ~/.claude/skills/xiaocai-stock-ai
pip install -r requirements.txt
cp .env.example .env
```

编辑 `.env`, 填两把 key:

```
DEEPSEEK_API_KEY=sk-xxx
TUSHARE_TOKEN=tsxxx
```

回到 Claude Code 会话, 问 "帮我看看茅台" 即可。

## 从哪拿 key

- **DeepSeek**: https://platform.deepseek.com — 新用户送 10 元
- **Tushare**: https://tushare.pro — 免费注册

<details>
<summary>💥 遇到问题?</summary>

- Claude 没主动用 skill → 加前缀 "用 xiaocai skill 帮我看茅台" 强制触发
- `ModuleNotFoundError` → 依赖没装全, 重跑 `pip install -r requirements.txt`
- 报 `missing DEEPSEEK_API_KEY` → `.env` 位置或 key 前后空格问题

</details>

小财能问什么: 个股 / 板块 / 选股 / 选板块 / 对比 — 详见 [主 README](../../README.md)

有问题 → [Issue](https://github.com/Fisher0012/xiaocai-stock-ai/issues) 或 [飞书群](../../README.md#-一起玩)
