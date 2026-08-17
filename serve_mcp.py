# -*- coding: utf-8 -*-
"""MCP Server (SPEC §5.1)

标准 MCP 协议(stdio 传输), 供 Claude Desktop / Claude Code / Cursor / Continue 等使用。

Claude Desktop 用户配置示例:
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

启动(手动测试用, MCP 客户端会自己启动):
    python3 serve_mcp.py
"""
import asyncio
import json
import logging
import sys

import mcp.types as types
from mcp.server import Server
from mcp.server.stdio import stdio_server

from core.config import _load_dotenv_once
from core.engine import (
    answer,
    answer_board_pick,
    answer_fast,
    answer_ranking,
    answer_sector,
)

_load_dotenv_once()
logger = logging.getLogger("xiaocai.mcp")

app = Server("xiaocai-stock-ai")


@app.list_tools()
async def list_tools() -> list[types.Tool]:
    """暴露给 MCP 客户端的工具清单。"""
    return [
        types.Tool(
            name="xiaocai_ask",
            description=(
                "A 股问答通用入口(推荐)。自动识别问题类型走最合适路径。"
                "示例: '中际旭创能上吗' / '光通信怎么样' / '从半导体设备里选3只' / "
                "'给我3个明天可以买的细分板块' / '旭创和新易盛哪个强'。"
                "输出会带具体价位、BIAS、主力资金和止损建议, 敢下判断。"
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "question": {"type": "string", "description": "用户问题"},
                    "context": {"type": "string", "description": "可选追问上下文", "default": ""},
                },
                "required": ["question"],
            },
        ),
        types.Tool(
            name="xiaocai_stock",
            description="个股研判(强制快速通道)。传股票名/代码/首字母, 返回带止损位的完整研判。",
            inputSchema={
                "type": "object",
                "properties": {
                    "name_or_code": {"type": "string", "description": "股票名/代码/拼音首字母"},
                    "context": {"type": "string", "default": ""},
                },
                "required": ["name_or_code"],
            },
        ),
        types.Tool(
            name="xiaocai_sector",
            description="板块诊断。传板块名, 返回板块整体状态 + 龙头逐只点评 + 事件驱动 vs 资金脉冲归因。",
            inputSchema={
                "type": "object",
                "properties": {
                    "sector_name": {"type": "string", "description": "板块/概念名, 支持模糊匹配"},
                    "context": {"type": "string", "default": ""},
                },
                "required": ["sector_name"],
            },
        ),
        types.Tool(
            name="xiaocai_ranking",
            description=(
                "选股。从板块或全市场热点里按短线买入价值排序。诚实分级, "
                "'够格的只有 N 只', 不硬凑数量。"
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "sector_name": {"type": "string", "description": "板块名(空=全市场热点)", "default": ""},
                    "count": {"type": "integer", "description": "想要几只", "default": 5},
                    "price_max": {"type": "number", "description": "股价上限(元), 可选"},
                    "question": {"type": "string", "description": "原始问题, 供 LLM 复述筛选口径"},
                },
                "required": ["question"],
            },
        ),
        types.Tool(
            name="xiaocai_board_pick",
            description=(
                "选板块(不是选股)。从当日主力资金流入靠前的细分板块里挑几个, 自动过滤电子/半导体等父级大类。"
                "结论前置格式: '我给你的 X 个板块是: A、B、C'。"
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "question": {"type": "string", "description": "原始问题"},
                    "count": {"type": "integer", "description": "想要几个板块", "default": 3},
                },
                "required": ["question"],
            },
        ),
    ]


def _fmt(r: dict) -> str:
    """格式化引擎返回值给 LLM。带 path 标注 + 工具调用统计。"""
    a = r.get("answer", "") or "(无输出)"
    path = r.get("path", "?")
    n = len(r.get("tool_trace") or [])
    footer = f"\n\n---\n[小财引擎 path={path} · 调用 {n} 个数据工具]"
    return a + footer


@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[types.TextContent]:
    """路由到对应引擎函数。所有引擎函数原样返回。"""
    try:
        args = arguments or {}
        ctx = args.get("context", "") or ""

        if name == "xiaocai_ask":
            r = answer_fast(args["question"], context=ctx)
        elif name == "xiaocai_stock":
            r = answer_fast(args["name_or_code"], context=ctx)
        elif name == "xiaocai_sector":
            sn = args["sector_name"]
            r = answer_sector(sn, sn, ctx)
        elif name == "xiaocai_ranking":
            r = answer_ranking(
                args.get("sector_name", "") or "",
                args["question"],
                count=args.get("count", 5),
                context=ctx,
                price_max=args.get("price_max"),
            )
        elif name == "xiaocai_board_pick":
            r = answer_board_pick(args["question"], count=args.get("count", 3), context=ctx)
        else:
            return [types.TextContent(type="text", text=f"未知工具: {name}")]

        return [types.TextContent(type="text", text=_fmt(r))]
    except Exception as e:
        logger.exception("tool call failed")
        return [types.TextContent(type="text", text=f"引擎错误: {str(e)[:300]}")]


async def main():
    async with stdio_server() as (read, write):
        await app.run(read, write, app.create_initialization_options())


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        stream=sys.stderr,  # MCP stdio 走 stdin/stdout, 日志必须走 stderr
    )
    asyncio.run(main())
