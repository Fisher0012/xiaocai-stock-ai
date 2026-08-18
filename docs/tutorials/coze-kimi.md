# Coze / 扣子 / Kimi 智能体接入 · 15 分钟

小财是标准 HTTP API, Coze 和 Kimi 都能作为"自定义工具"接入。

## Coze / 扣子 接入 · 10 分钟

### Step 1 · 打开 Coze 后台创建插件

1. 打开 [扣子](https://www.coze.cn), 用手机号登录
2. 顶部导航 **资源** → **插件** → 右上角 **创建插件**
3. 插件名填 `xiaocai-stock-ai`, 描述随便填(比如"A 股问答引擎")
4. 创建方式选 **在 Coze IDE 中创建** → 下一步

### Step 2 · 添加工具(核心步骤)

**推荐用一键导入 OpenAPI**:
在插件 IDE 里找 **导入 OpenAPI** 按钮 → 上传项目里的 [`examples/openapi.yaml`](../../examples/openapi.yaml) → 一键完成所有工具配置。

**如果没有这个按钮或不想用导入**, 手动配一个:

- 点 **添加工具**, 名字填 `ask`, 描述填:
  > A 股问答. 传入 question 字符串, 返回带 BIAS/资金流/操作建议的完整分析。个股/板块/选股/选板块/对比都能答。
- **请求方式**: POST
- **URL**: `https://xiaocai.sque.site/api/ask` (或[自部署地址](self-deploy.md))
- **请求头**: 加一条 `Content-Type: application/json`
- **请求参数**(在 Body 里加两个字段):
  - `question` (string, 必填, 描述"用户问题")
  - `context` (string, 选填, 描述"追问上下文")
- **响应参数**:
  - `answer` (string, "分析结果")
  - `path` (string, "走的路径")

### Step 3 · 测试插件

Coze IDE 里有个 **测试** 按钮, 点它, 输入:

```json
{"question": "半导体设备板块怎么样"}
```

15 秒左右应该返回一大段 JSON, `answer` 字段就是分析。**看到返回就是通了**。

### Step 4 · 发布插件

顶部 **发布** 按钮 → 自建插件通常秒过审。

### Step 5 · 把插件加到你的 Bot

回到 Bot 编辑页 → 左侧 **插件** → **添加插件** → 找到刚发布的 `xiaocai-stock-ai` → **添加**

在 Bot 的**系统提示词**里加这段:

```
当用户问 A 股相关问题(个股/板块/选股/选板块/对比)时,
一律调用 xiaocai-stock-ai 插件的 ask 工具,
把返回的 answer 原样展示给用户,
末尾附一句"仅供参考, 不构成投资建议"。
```

在 Bot 调试面板里发一条 "帮我看看茅台" 试试, 看到分析就成功了 🎉

---

## Kimi 智能体接入 · 5 分钟(需要编程)

Kimi 智能体广场目前**不支持直连外部 HTTP 工具**。推荐用 **Kimi API + 自己写 Python agent**(需要一点编程基础):

先拿一个 Kimi API key: [platform.moonshot.cn](https://platform.moonshot.cn) → 注册 → 创建 API key。

然后新建一个 Python 文件, 粘贴:

```python
from openai import OpenAI
import requests

client = OpenAI(api_key="你的Kimi API key", base_url="https://api.moonshot.cn/v1")

def xiaocai_ask(question: str, context: str = "") -> str:
    r = requests.post(
        "https://xiaocai.sque.site/api/ask",
        json={"question": question, "context": context},
        timeout=180
    )
    return r.json().get("answer", "")

tools = [{
    "type": "function",
    "function": {
        "name": "xiaocai_ask",
        "description": "A 股问答. 个股/板块/选股/选板块/对比都能答。",
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

# 后续用 Kimi function calling 循环处理, 详见 Kimi 官方文档
```

跑起来就是一个能调用小财的 Kimi agent。

<details>
<summary>💥 遇到问题?</summary>

- **Coze 插件超时** → 把插件超时设为 90s+, 小财单次分析 10-30s, 选股/选板块 30-60s
- **Coze 说限流** → 演示服务每 IP 每天 20 次, 换 [自部署](self-deploy.md) 或减少提问频率
- **Bot 不主动调 xiaocai** → 提示词写死"**必须**调用 xiaocai_ask", 别让模型自己判断
- **测试返回 401 或 429** → 401 说明认证错(演示服务不需要 key, 别加); 429 是限流
- **想省事直接用 OpenAPI** → 项目里 [`examples/openapi.yaml`](../../examples/openapi.yaml) 就是, Coze/Kimi 都支持导入

</details>

有问题 → [Issue](https://github.com/Fisher0012/xiaocai-stock-ai/issues) 或 [飞书群](../../README.md#-一起玩)
