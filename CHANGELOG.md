# Changelog

## [1.0.0] - 2026-08-18

首次开源版本。

### 引擎(core/)
- 6 条分析路径: stock / sector / ranking / board_pick / compare / agentic
- 17 个数据工具: 实时(东财) + 技术指标(自研) + EOD(Tushare)
- 硬底线: 出货结构 / 20cm 涨停 / ST 警示 / "买入/卖出/目标价"字眼过滤
- 板块名模糊匹配 + A 股映射守门 + 结论前置铁律

### 三种接入形态
- HTTP API(FastAPI)
- MCP Server(标准协议, Claude Desktop/Code/Cursor 通用)
- Claude Code Skill

### 4 种示例
- 飞书群机器人(完整可用)
- Coze / 扣子插件
- Kimi 智能体
- 微信机器人(wxauto)

### 部署
- Docker + docker-compose
- systemd 生产方案
- nginx HTTPS 反代示例

### 演示服务
- xiaocai.sque.site (免部署试用, 每 IP 每天 20 次)
