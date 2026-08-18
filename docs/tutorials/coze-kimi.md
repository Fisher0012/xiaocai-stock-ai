# 接进 Coze / 扣子 / Kimi 智能体 · 15 分钟教程

Coze (国际版) 或扣子 (国内版) 上, 你搭的 Bot 可以调用外部 API 作为 "插件"。Kimi 智能体的自定义工具原理类似。这份教程演示如何把小财作为一个插件接进去。

---

## 前置

- 你已经有 Coze / 扣子 / Kimi 智能体账号
- 会创建 Bot / 智能体的基础流程

---

## Step 1 · 确认 API 地址 (30 秒)

小财引擎作为一个 HTTP API 暴露, 有两种选择:

**方式 A · 用官方演示服务** (推荐先跑起来)
- 地址: `https://xiaocai.sque.site/api/ask`
- 限流: 每 IP 每天 20 次
- 不用自己部署

**方式 B · 自部署引擎** (推荐生产)
- 先按 [自部署教程](self-deploy.md) 起服务
- 地址: 你自己的域名, 如 `https://xiaocai.yourdomain.com/api/ask`
- 没有限流

---

## Step 2 · Coze / 扣子: 创建插件 (5 分钟)

1. 打开 [扣子](https://www.coze.cn) → 顶部 **资源** → **插件** → **创建插件**
2. 插件名 "xiaocai-stock-ai", 描述随便填
3. 创建方式选 **在 Coze IDE 中创建** → 下一步

4. 添加工具:
   - 工具名: `ask`
   - 工具描述: `A 股问答. 传入 question 字符串, 返回带 BIAS/资金流/操作建议的完整分析。个股/板块/选股/选板块/对比都能答。`
   - **请求方式**: POST
   - **URL**: `https://xiaocai.sque.site/api/ask` (或你自部署的地址)
   - **请求头**: `Content-Type: application/json`

5. **请求参数** (Body, JSON):
   - `question` (string, 必填, 用户问题, 如 "中际旭创能上吗")
   - `context` (string, 选填, 追问上下文)

6. **响应参数**:
   - `answer` (string, 分析结果)
   - `path` (string, 走的路径)
   - `meta` (object, 元信息)

7. **测试**: Coze IDE 里有测试按钮, 输入 `{"question": "半导体设备板块怎么样"}`, 应该 15 秒后返回 500-1500 字分析。

8. **发布插件**: 顶部 **发布**, 等审核 (自建插件通常秒过)。

---

## Step 3 · Kimi 智能体: 注册工具 (5 分钟)

Kimi 智能体广场目前工具调用需要通过 API Gateway 或后端代理, 不能直连外部 HTTP。**替代方案**:

### 方式 A · 用 Kimi API + 自己写 Agent (推荐给开发者)

```python
from openai import OpenAI
import httpx

client = OpenAI(
    api_key="你的Kimi API key",
    base_url="https://api.moonshot.cn/v1"
)

def xiaocai_ask(question: str, context: str = "") -> str:
    r = httpx.post("https://xiaocai.sque.site/api/ask",
                   json={"question": question, "context": context}, timeout=180)
    return r.json().get("answer", "")

tools = [{
    "type": "function",
    "function": {
        "name": "xiaocai_ask",
        "description": "A 股问答. 个股/板块/选股/选板块/对比都能答, 返回带数据支撑的分析",
        "parameters": {
            "type": "object",
            "properties": {
                "question": {"type": "string", "description": "用户问题"},
                "context": {"type": "string", "description": "追问上下文", "default": ""}
            },
            "required": ["question"]
        }
    }
}]

# 后续用 Kimi 的 function calling 循环, 详见 Kimi 官方文档
```

### 方式 B · Kimi 智能体广场 + 你自建的 API 中转

自己搭一个中转服务 (可以就用你自部署的 xiaocai HTTP API), 在 Kimi 智能体广场配置为外部工具。

---

## Step 4 · Bot 提示词模板

不管 Coze 还是 Kimi, 在你的 Bot / 智能体系统提示词里加:

```
你是一个财经助手。当用户问以下类型问题时, 一律调用 xiaocai 插件的 ask 端点:

- 个股: "XX 能上吗" / "XX 怎么样"
- 板块: "XX 板块怎么样"  
- 选股: "从 XX 里选几只"
- 选板块: "给我几个可以买的板块"
- 对比: "X 和 Y 哪个强"

把插件返回的 answer 字段原样展示给用户, 末尾附:
"数据来自公开市场数据 | 仅供参考, 不构成投资建议"
```

---

## Step 5 · 在你的 Bot 里试一下

发一条测试消息:

> 帮我看看中际旭创

**你会看到**: Bot 调用 xiaocai 插件, 15 秒左右返回带 BIAS、主力资金、操作建议的分析。

**看到这个就成功了 🎉**

---

## 💥 常见问题

**Q: 超时**
A: 小财单次分析 10-30s, 选股/选板块可能 30-60s。把 Coze 插件的超时设为 90s+。

**Q: 说 "限流"**
A: 用了演示服务, 每 IP 每天 20 次上限。换自部署 (Step 1 方式 B) 或减少提问频率。

**Q: 想省事直接导入现成的 OpenAPI 描述**
A: 项目里有 `examples/openapi.yaml`, Coze 支持 OpenAPI 导入, 一键搞定。

**Q: Coze 里 Bot 有时候不主动调插件**
A: 提示词里明确 "当用户问股票问题时必须调用 xiaocai_ask", 别让模型自己判断。

---

有问题 → [提 Issue](https://github.com/Fisher0012/xiaocai-stock-ai/issues) 或 [加飞书群](../../README.md#-一起玩)
