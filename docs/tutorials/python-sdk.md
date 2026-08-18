# 自写 Python Agent 用小财 · 5 分钟

小财是纯 HTTP API, 直接调即可。

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

## 完整参数

```python
r = requests.post(
    "https://xiaocai.sque.site/api/ask",
    json={
        "question": "从半导体设备里选3只",
        "context": "",              # 追问上下文
        "options": {
            "path_hint": None,      # stock/sector/ranking/board_pick
            "count": 3,             # 选股/选板块数量
            "price_max": 20         # 价格上限(元)
        }
    },
    timeout=180
)
data = r.json()
# data["answer"], data["path"], data["meta"]["tool_trace"]
```

## LangChain 集成

```python
from langchain.tools import tool
import requests

@tool
def xiaocai_ask(question: str) -> str:
    """A 股问答. 个股/板块/选股/选板块/对比都能答。"""
    r = requests.post("https://xiaocai.sque.site/api/ask",
                      json={"question": question}, timeout=180)
    return r.json().get("answer", "")
```

## OpenAI Function Calling

```python
tools = [{
    "type": "function",
    "function": {
        "name": "xiaocai_ask",
        "description": "A 股问答. 个股/板块/选股/选板块/对比。",
        "parameters": {
            "type": "object",
            "properties": {
                "question": {"type": "string"},
                "context": {"type": "string", "default": ""}
            },
            "required": ["question"]
        }
    }
}]
```

## 指定路径端点 (更精确)

- `POST /api/stock` — 个股
- `POST /api/sector` — 板块
- `POST /api/ranking` — 选股, options 支持 `count`/`price_max`
- `POST /api/board_pick` — 选板块, options 支持 `count`

## 演示服务限流

`xiaocai.sque.site`: 每 IP 每天 20 次。要更多请 [自部署](self-deploy.md), 没有限流。

完整 API: [openapi.yaml](../../examples/openapi.yaml)

有问题 → [Issue](https://github.com/Fisher0012/xiaocai-stock-ai/issues) 或 [飞书群](../../README.md#-一起玩)
