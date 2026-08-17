# Coze / 扣子 接入 xiaocai-stock-ai

把 xiaocai 引擎作为 Coze bot 的一个自定义插件, 让你在 Coze 上搭的 agent 也能用小财的分析能力。

## 步骤

1. **准备一个可访问的 xiaocai HTTP API**
   - 方式 A: 用官方演示服务 `https://xiaocai.sque.site/api/ask` (免部署, 每 IP 每天 20 次)
   - 方式 B: 自部署到你的服务器(见项目根 README `docker-compose up -d`)

2. **在 Coze 平台创建自定义插件**
   - 访问 [Coze](https://www.coze.cn) → 我的插件 → 创建插件
   - 选择"以自定义 URL 方式"
   - 上传 `openapi.yaml`(在项目 `examples/openapi.yaml`) 或直接手动配置端点

3. **手动配置端点(如果不上传 yaml)**

   - **URL**: `https://xiaocai.sque.site/api/ask` (或你的自部署地址)
   - **Method**: POST
   - **Content-Type**: `application/json`
   - **Body Schema**:
     ```json
     {
       "question": "string, 必填",
       "context": "string, 可选"
     }
     ```
   - **Response Schema**:
     ```json
     {
       "answer": "string, 分析结果",
       "path": "string, 引擎走的路径",
       "meta": "object, 元信息"
     }
     ```

4. **调试**
   - 在插件调试面板输入 `{"question": "中际旭创怎么样"}`
   - 应该返回 800-1500 字的完整研判

5. **加到你的 Bot**
   - 编辑 Bot → 插件 → 添加你刚创建的 xiaocai 插件
   - 在 Bot 提示词里引导使用: "当用户问 A 股相关问题时, 调用 xiaocai 插件"

## 提示词模板

```
你是一个财经助手。当用户问以下类型问题时, 调用 xiaocai 插件的 /api/ask 端点:
- 个股: "XX 能上吗" / "XX 怎么样"
- 板块: "XX 板块怎么样"
- 选股: "从 XX 里选几只"
- 选板块: "给我几个可以买的板块"

把插件返回的 answer 字段原样展示给用户, 后面附上"数据来自公开市场数据 | 仅供参考, 不构成投资建议"。
```

## 常见问题

- **超时**: xiaocai 单次分析 10-30s, Coze 默认超时可能 60s, 通常够用; 复杂问题(选股/选板块)可能到 60s+, 提前说明
- **限流**: 用官方演示服务时, 每 IP 每天 20 次上限; 生产建议自部署
- **成本**: 演示服务免费; 自部署烧的是你的 DeepSeek/Tushare 额度
