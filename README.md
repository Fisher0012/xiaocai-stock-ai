<div align="center">

<img src="docs/img/cover.png" alt="xiaocai-stock-ai" width="720"/>

# xiaocai-stock-ai

**一套开源的 A 股问答引擎 · 用真数据说话 · 敢下判断**

数据取证 + 分析策略 + 硬底线 · 让任何人 30 分钟搭出自己的股票分析机器人

[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.10+-green.svg)](https://www.python.org/)
[![Docker](https://img.shields.io/badge/Docker-Ready-2496ED.svg)](Dockerfile)
[![MCP](https://img.shields.io/badge/MCP-Server-orange.svg)](serve_mcp.py)

⭐ 觉得有用请给个 Star · 👉 加入讨论群一起玩(见下方)

</div>

---

## 它长这样

问一只股票, 它这么答:

<img src="docs/img/screenshots/05-stock-1.png" alt="个股研判" width="360"/>

问一个板块, 它这么答:

<img src="docs/img/screenshots/03-concept-1.png" alt="板块诊断" width="360"/>

让它选 3 个板块, 它这么答:

<img src="docs/img/screenshots/07-board-pick-1.png" alt="选板块" width="360"/>

追问不用点引用, 15 分钟内直接接着问, 它记得上一轮:

<img src="docs/img/screenshots/01-follow-up-1.png" alt="追问" width="360"/>

---

## 它凭什么这么答

三件事让它跟"再问一次通用 AI"不一样。

**① 拿真数据不是从记忆里翻** — 数据来自新浪 / 东财 / Tushare 等公开市场接口, 盘中问就是当天当分钟的资金流、技术面、行情、公告, 不是"根据我的训练数据"。

**② 分析框架是代码算好的, 不是模型即兴发挥** — BIAS20 是否在甜区、60 日位置多少、主力资金净流入几个亿、动态 PE vs TTM 反映业绩趋势——这些**判断标准是量化引擎的确定值**, 交给 LLM 只负责组织成话。所以换 LLM 供应商不影响判断质量。

**③ 有硬底线** — 放量出货结构不接、20cm 涨停不追、ST 股必带警示。**严禁"买入/卖出/目标价"字眼**(合规底线)。

<img src="docs/img/capabilities.png" alt="能力全景" width="720"/>

---

## 30 秒试试 · 免部署

```bash
curl -X POST https://xiaocai.sque.site/api/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "中际旭创能上吗"}'
```

演示服务限流: 每 IP 每天 20 次、每分钟 3 次。生产用请自部署(见下)。

## 5 分钟自部署

```bash
git clone https://github.com/Fisher0012/xiaocai-stock-ai
cd xiaocai-stock-ai
cp .env.example .env
# 编辑 .env: 填 DEEPSEEK_API_KEY 和 TUSHARE_TOKEN
docker-compose up -d
curl http://localhost:8080/api/ask -X POST \
  -H "Content-Type: application/json" \
  -d '{"question":"半导体设备板块怎么样"}'
```

必须的两个 key:
- [DeepSeek API Key](https://platform.deepseek.com) — 或用 OpenAI 兼容协议(Kimi/通义/豆包 都行)
- [Tushare Token](https://tushare.pro) — 免费注册

---

## 三种接入形态

### 1. HTTP API(推荐 · 所有平台通用)

```python
import requests
r = requests.post("http://localhost:8080/api/ask",
                  json={"question": "光通信板块怎么样"})
print(r.json()["answer"])
```

完整 API 文档: [`docs/API.md`](docs/API.md) · OpenAPI: [`examples/openapi.yaml`](examples/openapi.yaml)

### 2. MCP Server(Claude Desktop / Claude Code / Cursor / Continue)

`~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "xiaocai-stock-ai": {
      "command": "python3",
      "args": ["/path/to/xiaocai-stock-ai/serve_mcp.py"],
      "env": {
        "DEEPSEEK_API_KEY": "sk-xxx",
        "TUSHARE_TOKEN": "xxx"
      }
    }
  }
}
```

重启 Claude, 就能直接问 "帮我看看茅台"、"给我 3 个明天可以买的板块"。

### 3. Claude Code Skill

```bash
git clone https://github.com/Fisher0012/xiaocai-stock-ai ~/.claude/skills/xiaocai-stock-ai
cd ~/.claude/skills/xiaocai-stock-ai && pip install -r requirements.txt
cp .env.example .env  # 编辑填 key
# 重启 Claude Code, 直接问股票问题即可
```

---

## 接进你的平台

### 飞书群机器人

30 分钟接入, 群友 @机器人 就能用: [`examples/feishu-bot/`](examples/feishu-bot/)

### Coze / 扣子

作为自定义插件: [`examples/coze-plugin/`](examples/coze-plugin/)

### Kimi 智能体

作为函数调用工具: [`examples/kimi-agent/`](examples/kimi-agent/)

### 微信机器人

wxauto Windows 方案 + 公众号客服消息 API: [`examples/wechat-bot/`](examples/wechat-bot/)

---

## 项目结构

```
xiaocai-stock-ai/
├── core/                    引擎(数据+策略+人设默认版, 单一实现)
├── serve_http.py            HTTP API 服务
├── serve_mcp.py             MCP Server
├── skill/                   Claude Code Skill 包
├── examples/                4 种接入示例
│   ├── feishu-bot/
│   ├── coze-plugin/
│   ├── kimi-agent/
│   ├── wechat-bot/
│   └── openapi.yaml
├── docker-compose.yml       一键起服务
└── docs/                    部署/API/架构文档
```

---

## 一起玩

**飞书讨论群**(项目问题反馈 + 用户交流):

<img src="docs/img/feishu-group-qr.png" alt="飞书群二维码" width="180"/>

群链接: https://applink.feishu.cn/client/chat/chatter/add_by_link?link_token=276q038c-b6db-44c1-8eec-b1600458dc58

进群方式: 群名不可搜索, 只能通过二维码或链接进。

---

## 硬底线与免责

**引擎自带的硬约束**(不可关闭):
- 严禁"买入/卖出/目标价"字眼(合规底线, 自动改写)
- 出货结构 → 不接飞刀
- 20cm 涨停 → 不追(接盘概率高)
- ST 股 → 强制警示
- 境外主题(英伟达业绩类) → 友好拒绝, 但概念股 A 股受益方向可以答

**免责声明**: 本项目仅提供研究参考, 不构成投资建议。所有分析结论基于公开市场数据和量化模型, 数据源可能存在延迟或错误。投资决策与风险由使用者自行承担。

---

## 维护承诺范围

- **承诺**: 严重 bug 修复(数据错误、安全问题、无法运行)
- **尽力而为**: 一般 bug、feature request、性能优化
- **不承诺**: 用户环境问题(自己 API key / 网络 / 依赖)、平台适配定制、投资建议、每日推荐

## 贡献

欢迎 PR 和 Issue: [贡献指南](CONTRIBUTING.md) · [Issue 模板](.github/ISSUE_TEMPLATE)

---

## 协议

Apache License 2.0 — 允许商用, 需要保留署名, 详见 [LICENSE](LICENSE)。

## 致谢

- 数据源: [Tushare](https://tushare.pro) / 新浪财经 / 东方财富
- LLM: [DeepSeek](https://www.deepseek.com) / OpenAI 兼容协议
- MCP: [Anthropic Model Context Protocol](https://modelcontextprotocol.io)
