# 自己写 Python Agent 用小财 · 5 分钟教程

如果你在自己写 agent (LangChain / AutoGen / 自定义), 小财是一个纯 HTTP API, 直接调就行。

---

## 最简用法

```python
import requests

r = requests.post(
    "https://xiaocai.sque.site/api/ask",
    json={"question": "中际旭创能上吗"},
    timeout=180
)
print(r.json()["answer"])
```

**你会看到**: 15 秒左右返回一段 500-1500 字的分析。

---

## 完整参数

```python
import requests

r = requests.post(
    "https://xiaocai.sque.site/api/ask",
    json={
        "question": "从半导体设备里选3只",
        "context": "",              # 追问时把上一轮问答摘要传进来
        "persona": "default",       # 目前只有 default
        "options": {
            "path_hint": None,      # 强制路径 stock/sector/ranking/board_pick
            "count": 3,             # 选股/选板块数量
            "price_max": 20         # 价格上限 (元)
        }
    },
    timeout=180
)

data = r.json()
print("答案:", data["answer"])
print("走的路径:", data["path"])           # fast / sector / ranking / board_pick
print("工具调用:", data["meta"]["tool_trace"])  # 数据采集轨迹, 可追溯
print("耗时:", data["meta"]["duration_s"], "s")
```

---

## 集成到 LangChain

```python
from langchain.tools import tool
import requests

@tool
def xiaocai_ask(question: str) -> str:
    """A 股问答. 传入问题字符串, 返回带 BIAS/资金流/操作建议的完整分析.
    支持个股/板块/选股/选板块/对比."""
    r = requests.post(
        "https://xiaocai.sque.site/api/ask",
        json={"question": question}, timeout=180
    )
    return r.json().get("answer", "")

# 然后把 xiaocai_ask 加到你的 agent tools 里
```

---

## 集成到 OpenAI Function Calling

```python
tools = [{
    "type": "function",
    "function": {
        "name": "xiaocai_ask",
        "description": "A 股问答. 个股/板块/选股/选板块/对比都能答, 返回带数据支撑的分析.",
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

def call_xiaocai(question, context=""):
    r = requests.post("https://xiaocai.sque.site/api/ask",
                      json={"question": question, "context": context}, timeout=180)
    return r.json().get("answer", "")

# 按 OpenAI function calling 标准循环处理即可
```

---

## 指定路径的端点 (更精确)

除了通用 `/api/ask`, 还有:

- `POST /api/stock` — 强制走个股快速通道
- `POST /api/sector` — 强制走板块诊断
- `POST /api/ranking` — 强制走选股, `options.count` 和 `options.price_max` 有效
- `POST /api/board_pick` — 强制走选板块, `options.count` 有效

请求体格式跟 `/api/ask` 一样。用途: 你已经知道用户想干什么, 强制走对应路径能更准。

---

## 演示服务限流

免部署用 `xiaocai.sque.site`: 每 IP 每天 20 次, 每分钟 3 次。

要更多请自部署: [自部署教程](self-deploy.md), 5 分钟起服务, 没有限流。

---

## 完整 API 文档

- OpenAPI 描述: [`examples/openapi.yaml`](../../examples/openapi.yaml)
- 错误码/字段详解: 见 OpenAPI 内容 (可用 [Swagger Editor](https://editor.swagger.io) 打开)

---

有问题 → [提 Issue](https://github.com/Fisher0012/xiaocai-stock-ai/issues) 或 [加飞书群](../../README.md#-一起玩)
