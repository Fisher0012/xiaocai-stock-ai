# 自写 Python Agent 用小财 · 5 分钟

小财是纯 HTTP API, 你 Python 代码里 requests 一下就能用。适合已经在写 agent(LangChain/AutoGen/OpenAI SDK/自定义)的开发者。

## Step 1 · 装 requests(如果还没有)

```bash
pip install requests
```

## Step 2 · 复制这段代码到你的 py 文件里

```python
import requests

def ask_xiaocai(question: str, context: str = "") -> str:
    """问小财一句话, 返回完整分析(500-1500 字)。"""
    r = requests.post(
        "https://xiaocai.sque.site/api/ask",
        json={"question": question, "context": context},
        timeout=180
    )
    return r.json().get("answer", "")

# 试试
print(ask_xiaocai("中际旭创能上吗"))
```

**你会看到**: 15 秒左右打印出一段带 BIAS、主力资金、操作建议的分析。

## Step 3(可选) · 需要更精确控制时用完整参数

```python
r = requests.post(
    "https://xiaocai.sque.site/api/ask",
    json={
        "question": "从半导体设备里选3只",
        "context": "",              # 追问时把上一轮 Q+A 传进来
        "options": {
            "path_hint": None,      # 强制路径: stock/sector/ranking/board_pick
            "count": 3,             # 选股/选板块数量
            "price_max": 20         # 股价上限(元)
        }
    },
    timeout=180
)
data = r.json()
print("答案:", data["answer"])
print("走的路径:", data["path"])           # fast / sector / ranking / board_pick
print("工具调用:", len(data["meta"]["tool_trace"]))
print("耗时:", data["meta"]["duration_s"], "s")
```

---

## 集成到 LangChain

```python
from langchain.tools import tool
import requests

@tool
def xiaocai_ask(question: str) -> str:
    """A 股问答. 传入问题字符串, 返回带 BIAS/资金流/操作建议的完整分析。
    支持个股/板块/选股/选板块/对比."""
    r = requests.post("https://xiaocai.sque.site/api/ask",
                      json={"question": question}, timeout=180)
    return r.json().get("answer", "")

# 然后把 xiaocai_ask 加到你的 agent tools 列表里就行
```

## 集成到 OpenAI Function Calling

```python
tools = [{
    "type": "function",
    "function": {
        "name": "xiaocai_ask",
        "description": "A 股问答. 个股/板块/选股/选板块/对比都能答, 返回带数据支撑的分析。",
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

# 按 OpenAI function calling 标准处理即可
```

## 指定路径的端点(更精确)

除了通用 `/api/ask`, 还有:

- `POST /api/stock` — 强制走个股快速通道
- `POST /api/sector` — 强制走板块诊断
- `POST /api/ranking` — 强制走选股, options 支持 `count` 和 `price_max`
- `POST /api/board_pick` — 强制走选板块, options 支持 `count`

请求体格式跟 `/api/ask` 一样。适合你已经知道用户想干什么, 强制走对应路径能更快更准。

---

## 演示服务限流

免部署用 `xiaocai.sque.site`: 每 IP 每天 20 次、每分钟 3 次。

要更多请 [自部署](self-deploy.md), 5 分钟起服务, 没有限流。自部署后把上面代码里的 `xiaocai.sque.site` 换成你自己的地址(如 `http://localhost:8080`)。

## 完整 API 文档

- OpenAPI 描述: [`examples/openapi.yaml`](../../examples/openapi.yaml) (可用 [Swagger Editor](https://editor.swagger.io) 打开可视化查看)
- 错误码/所有字段详解: 见 openapi.yaml

<details>
<summary>💥 遇到问题?</summary>

- **`requests.exceptions.Timeout`** → 增加 `timeout` 到 300+, 或问题太复杂拆小
- **返回 `{"detail":"429..."}`** → 触发限流, 换 [自部署](self-deploy.md) 或减少频率
- **返回 `answer` 为空** → 检查你的 question 是不是空字符串或纯特殊字符
- **要不要传 API key?** → 演示服务不需要; 自部署除非你自己套了鉴权, 否则也不需要

</details>

有问题 → [Issue](https://github.com/Fisher0012/xiaocai-stock-ai/issues) 或 [飞书群](../../README.md#-一起玩)
