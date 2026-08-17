"""大盘环境快照 (方案B, 2026-08-11 Donnie 拍板)

只提供原始市场事实, 不做任何档位判定——此前的规则引擎(防守/中性/进攻档、
结构两态、家数比1.1/板块20亿阈值、风口通道)已整体删除。
市场环境降级为背景数据, 由 LLM 连续权衡; 个股结论由个股数据决定(见 persona 原则)。
结果缓存 10 分钟, 注入每次回答的"当日市场环境"。
"""

import datetime as _dt
import time

from . import tools_rt
from .tools_ta import _ensure_env

_CACHE: dict = {"ts": 0.0, "result": None}
_TTL_S = 600


def get_market_context() -> dict:
    """当日市场环境原始事实(指数/涨跌家数/成交额/板块资金/HS300与60日线位置)。"""
    now = time.time()
    if _CACHE["result"] and now - _CACHE["ts"] < _TTL_S:
        return _CACHE["result"]
    try:
        snap = tools_rt.get_market_snapshot()
        if not snap.get("ok"):
            return snap
        s = snap["data"]
        idx = {i["name"]: i for i in s["indices"]}
        hs300 = idx.get("沪深300", {})

        # HS300 与 60 日线的位置(事实, 不下判断)
        _ensure_env()
        from finmcp_a_stock_data.tools.index import get_index_price
        start = (_dt.date.today() - _dt.timedelta(days=150)).strftime("%Y-%m-%d")
        r = get_index_price("000300.SH", start_date=start, period="daily")
        closes = [row["close"] for row in sorted(r.get("data") or [], key=lambda x: x["date"])]
        ma60 = round(sum(closes[-60:]) / 60, 2) if len(closes) >= 60 else None
        point = hs300.get("point")
        pct_vs_ma60 = (round((point - ma60) / ma60 * 100, 2)
                       if (ma60 and point) else None)

        # 当日板块资金(流入/流出两端, 供个股对照)
        hot_sectors, outflow_sectors = [], []
        try:
            rank = tools_rt.get_sector_moneyflow_rank(top_n=5, board_type="industry")
            if rank.get("ok"):
                hot_sectors = rank["data"]["top_inflow"]
                outflow_sectors = rank["data"]["top_outflow"][:3]
        except Exception:
            pass

        result = {"ok": True, "data": {
            "indices": s["indices"],
            "market_breadth": s["market_breadth"],
            "total_amount_yi": s["total_amount_yi"],
            "hot_sectors": hot_sectors,
            "outflow_sectors": outflow_sectors,
            "hs300_vs_ma60": {"point": point, "ma60": ma60, "pct_vs_ma60": pct_vs_ma60},
            "quote_time": s.get("quote_time"),
            "note": "以上为原始市场事实; 环境影响仓位与节奏, 不否决个股机会",
        }, "source": "eastmoney_realtime + tushare_index"}
        _CACHE.update(ts=now, result=result)
        return result
    except Exception as e:
        return {"ok": False, "error": {"message": f"市场环境获取失败: {str(e)[:200]}"}}
