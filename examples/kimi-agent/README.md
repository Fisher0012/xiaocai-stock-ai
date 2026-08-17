# Kimi 智能体接入 xiaocai-stock-ai

在 Kimi 智能体广场创建一个财经助手, 用 xiaocai 引擎回答 A 股问题。

## 步骤

1. **准备 xiaocai HTTP API 地址**
   - 用官方演示服务: `https://xiaocai.sque.site/api/ask` (免部署)
   - 或自部署到你的服务器

2. **Kimi 智能体广场创建智能体**
   - 访问 [Kimi 智能体](https://platform.moonshot.cn/) → 创建
   - 选择"函数调用"或"自定义工具"能力

3. **注册工具**
   ```json
   {
     "name": "xiaocai_ask",
     "description": "A 股问答引擎。传入问题字符串, 返回带数据支撑和操作建议的分析。支持个股/板块/选股/选板块/对比。",
     "parameters": {
       "type": "object",
       "properties": {
         "question": {"type": "string", "description": "用户问题"},
         "context": {"type": "string", "description": "追问上下文", "default": ""}
       },
       "required": ["question"]
     }
   }
   ```

4. **工具的执行逻辑**(需要一个后端中转, Kimi 直接调用外部 API 需要 API Gateway):
   ```python
   import httpx
   def xiaocai_ask(question: str, context: str = "") -> str:
       r = httpx.post("https://xiaocai.sque.site/api/ask",
                      json={"question": question, "context": context}, timeout=120)
       return r.json().get("answer", "")
   ```

5. **智能体系统提示词**
   ```
   你是一个 A 股财经助手。当用户问股票、板块、选股相关问题时, 一律调用 xiaocai_ask 工具。
   把工具返回的 answer 原样展示, 结尾附"仅供参考, 不构成投资建议"。
   ```

## 常见问题

- **Kimi 智能体广场是否直接支持外部 HTTP tool**: 目前 Kimi 官方需要通过 API Gateway 或后端代理, 直连不支持
- **替代方案**: 也可以用 Kimi API + LangChain/OpenAI Function Calling 自己搭一个 agent, 集成 xiaocai_ask 函数
- **成本**: xiaocai 官方演示服务免费(有限流); Kimi API 按用量计费
