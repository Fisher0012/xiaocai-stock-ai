# Claude Code 用小财 · 30 秒

## Step 1 · 先拿两把 key(免费)

- **DeepSeek key**: 打开 https://platform.deepseek.com → 用手机号注册 → 左侧 API Keys → 点"创建 API Key" → 复制那串 `sk-xxxx...`(先记事本存着, 新用户送 10 元额度)
- **Tushare token**: 打开 https://tushare.pro → 手机号注册 → 右上角头像点进个人主页 → 页面上的 "接口 TOKEN" 一长串 → 复制

两把 key 都拿到, 继续下一步。

## Step 2 · 下载小财到 Claude Code 的 skills 目录

打开终端(Mac: Launchpad 搜"终端"; Windows: 开始菜单搜"PowerShell"), 一次复制下面 4 行, 粘贴回车:

```bash
git clone https://github.com/Fisher0012/xiaocai-stock-ai ~/.claude/skills/xiaocai-stock-ai
cd ~/.claude/skills/xiaocai-stock-ai
pip install -r requirements.txt
cp .env.example .env
```

看到最后一行输出 `Successfully installed ...` 就是装好了。

## Step 3 · 把 key 填进配置文件

刚才那一步生成了一个 `.env` 文件, 需要用文本编辑器打开填 key。

**最省事的方法**: 终端里继续粘贴这行, 用 Mac 自带的 TextEdit 打开:

```bash
open -e .env    # Mac
# Windows 用: notepad .env
```

文件里会看到很多 `# 开头的说明行`(不用管)和这两行:

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

## Step 4 · 回到 Claude Code 会话, 问它一句

在 Claude Code 里输入:

> 帮我看看茅台

15 秒左右应该会返回一段带 BIAS、主力资金、操作建议的完整分析。**看到这个就成功了 🎉**

---

## 从此可以问什么

- 个股: `中际旭创能上吗`
- 板块: `光通信板块怎么样`
- 选股: `从半导体设备里选 3 只`
- 选板块: `给我 3 个明天可以买的细分板块`
- 对比: `中际旭创和新易盛哪个强`
- 追问: 15 分钟内直接接着问就行, 不用重复股票名

<details>
<summary>💥 遇到问题?</summary>

- **Claude 没主动用 skill** → 说 "用 xiaocai skill 帮我看茅台" 强制触发
- **命令行报 `command not found: git`** → 先装 git: Mac 粘贴 `xcode-select --install`; Windows 装 [git-scm.com](https://git-scm.com/download/win)
- **报 `ModuleNotFoundError`** → 依赖没装全, 回 Step 2 重跑 `pip install -r requirements.txt`(或用 `pip3`)
- **报 `missing DEEPSEEK_API_KEY`** → `.env` 文件的 key 前后有空格, 或者没保存, 回 Step 3 检查
- **首次响应慢(30 秒+)** → 正常, 之后 10-15 秒
- **Tushare 部分分析说"数据不足"** → 完善你的 Tushare 个人资料页会自动加积分, 到 2000+ 就够用

</details>

有问题 → [Issue](https://github.com/Fisher0012/xiaocai-stock-ai/issues) 或 [飞书群](../../README.md#-一起玩)
