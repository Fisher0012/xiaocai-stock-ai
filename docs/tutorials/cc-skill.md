# 让 Claude Code 用小财 · 30 秒教程

Claude Code 是 Anthropic 官方的命令行 Claude, 支持 Skill (能力包) 机制。装完之后, 你在任何 CC 会话里说 "帮我看看茅台"、"给我 3 个可以买的板块", Claude 会自动激活小财并给出分析。

---

## 前置

你已经在用 Claude Code (还没装? [官方安装](https://docs.claude.com/en/docs/claude-code/quickstart))

需要的东西:
- Python 3.10+
- git
- DeepSeek API key 和 Tushare token (下面 Step 2 说明怎么拿)

---

## Step 1 · 装小财到 CC skills 目录 (10 秒)

在终端里粘贴:

```bash
git clone https://github.com/Fisher0012/xiaocai-stock-ai ~/.claude/skills/xiaocai-stock-ai
cd ~/.claude/skills/xiaocai-stock-ai
pip install -r requirements.txt
```

**你会看到**: 终端输出 `Cloning...done.` 然后 pip 装依赖, 最后 `Successfully installed ...`

---

## Step 2 · 配置 key (2 分钟)

小财需要两把 key (**都免费**):

- **DeepSeek key**: 打开 https://platform.deepseek.com → 注册 → API Keys → 创建 → 复制 (新用户送 10 元额度)
- **Tushare token**: 打开 https://tushare.pro → 注册 → 个人主页 → 复制 "接口 TOKEN"

在小财目录里创建 `.env` 文件:

```bash
cd ~/.claude/skills/xiaocai-stock-ai
cp .env.example .env
```

用文本编辑器打开 `.env`, 填上刚才复制的两把 key:

```bash
DEEPSEEK_API_KEY=sk-你的DeepSeek key
TUSHARE_TOKEN=你的Tushare token
```

保存。

---

## Step 3 · 在 CC 里问一句

打开一个新的 Claude Code 会话, 直接输入:

> 帮我看看中际旭创

**你会看到**: Claude 说 "I'll use the xiaocai-stock-ai skill to analyze...", 然后跑 `python3 scripts/ask.py`, 15 秒后返回带 BIAS、主力资金、操作建议的完整分析。

**看到这个就成功了 🎉**

---

## 💥 常见问题

**Q: Claude Code 没自动激活小财**
A: skill 的激活靠 `SKILL.md` 里的 description 匹配你的提问。试试更明确一点, 比如 "用 xiaocai skill 帮我分析茅台"。

**Q: 报 `ModuleNotFoundError`**
A: 依赖没装全, 重新跑 `pip install -r requirements.txt`

**Q: 报 `missing DEEPSEEK_API_KEY`**
A: `.env` 文件没在小财目录里 (`~/.claude/skills/xiaocai-stock-ai/.env`), 或者 key 前后有空格。

**Q: Claude 有时候不主动用小财**
A: 你可以强制用: 在提问前加 "用 xiaocai skill:"

---

## 用起来之后

小财能问:
- **个股**: `中际旭创能上吗`
- **板块**: `光通信板块怎么样`
- **选股**: `从半导体设备里选 3 只`
- **选板块**: `给我 3 个明天可以买的细分板块`
- **对比**: `中际旭创和新易盛哪个强`
- **追问**: 15 分钟内直接接着问

有问题 → [提 Issue](https://github.com/Fisher0012/xiaocai-stock-ai/issues) 或 [加飞书群](../../README.md#-一起玩)
