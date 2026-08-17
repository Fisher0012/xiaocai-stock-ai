#!/usr/bin/env python3
"""CC Skill 命令行入口: 一行命令用引擎答问题。

用法:
    python3 scripts/ask.py "中际旭创怎么样"
    python3 scripts/ask.py "那现在能上吗" --context "刚问了中际旭创..."
    python3 scripts/ask.py "光通信板块怎么样" --path sector
    python3 scripts/ask.py "从半导体设备里选3只" --path ranking --count 3

输出走 stdout, 供 Claude Code 直接读取。
"""
import argparse
import os
import sys

# 支持从 skill 目录内调用: skill/scripts/ask.py → 上级 (skill/) → 再上级 (项目根)
_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(os.path.dirname(_HERE))
sys.path.insert(0, _ROOT)


def main():
    parser = argparse.ArgumentParser(description="xiaocai-stock-ai CLI")
    parser.add_argument("question", help="问题")
    parser.add_argument("--context", default="", help="追问上下文")
    parser.add_argument("--path", choices=["auto", "stock", "sector", "ranking", "board_pick"],
                        default="auto", help="强制路径")
    parser.add_argument("--count", type=int, default=None, help="选股/选板块数量")
    parser.add_argument("--price-max", type=float, default=None, help="价格上限(元)")
    args = parser.parse_args()

    from core.engine import (
        answer_board_pick,
        answer_fast,
        answer_ranking,
        answer_sector,
    )

    if args.path == "auto" or args.path == "stock":
        r = answer_fast(args.question, context=args.context)
    elif args.path == "sector":
        r = answer_sector(args.question, args.question, args.context)
    elif args.path == "ranking":
        r = answer_ranking("", args.question, count=args.count or 5,
                           context=args.context, price_max=args.price_max)
    elif args.path == "board_pick":
        r = answer_board_pick(args.question, count=args.count or 3, context=args.context)

    print(r.get("answer", "(无输出)"))


if __name__ == "__main__":
    main()
