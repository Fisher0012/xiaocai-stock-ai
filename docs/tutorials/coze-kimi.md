# Coze / 扣子 / Kimi 智能体接入 · 15 分钟

小财是标准 HTTP API, 各平台按各自"自定义工具"或"插件"流程接入即可。

## Coze / 扣子

**创建插件** ([扣子](https://www.coze.cn) → 资源 → 插件 → 创建):

- 请求方式: **POST**
- URL: `https://xiaocai.sque.site/api/ask` (或[自部署地址](self-deploy.md))
- Content-Type: `application/json`
- **参数**: `question`(string, 必填), `context`(string, 选填)
- **响应**: `answer`(string), `path`(string), `meta`(object)

**或者省事一键导入** OpenAPI: 上传 [`examples/openapi.yaml`](../../examples/openapi.yaml)

**测试**: 输入 `{"question": "半导体设备板块怎么样"}`, 15 秒后返回 500-1500 字分析。

**Bot 提示词**:
```
当用户问股票/板块/选股相关问题时, 调用 xiaocai 插件的 ask 端点,
把返回的 answer 原样展示, 末尾附"仅供参考, 不构成投资建议"。
```

## Kimi 智能体

Kimi 智能体广场不支持直连外部 HTTP, 用 **Kimi API + 自建 agent** 更方便:

```python
from openai import OpenAI
import requests

client = OpenAI(api_key="你的Kimi API key", base_url="https://api.moonshot.cn/v1")

def xiaocai_ask(question: str, context: str = "") -> str:
    r = requests.post("https://xiaocai.sque.site/api/ask",
                      json={"question": question, "context": context}, timeout=180)
    return r.json().get("answer", "")

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
# 用 Kimi function calling 循环处理即可
```

<details>
<summary>💥 遇到问题?</summary>

- Coze 插件超时 → 把超时设为 90s+, 小财单次分析 10-30s, 选股/选板块 30-60s
- Coze 说限流 → 演示服务每 IP 每天 20 次, 换[自部署](self-deploy.md)或减少提问
- Bot 不主动调 xiaocai → 提示词写死 "**必须**调用 xiaocai_ask", 别让模型判断

</details>

有问题 → [Issue](https://github.com/Fisher0012/xiaocai-stock-ai/issues) 或 [飞书群](../../README.md#-一起玩)
