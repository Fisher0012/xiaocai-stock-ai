# -*- coding: utf-8 -*-
"""工具注册表 (SPEC §2.1 引擎层)
汇集 core/data/ 下所有工具, 供 engine 通过工具名查找调用。
"""
from .data.tools_rt import (
    get_realtime_moneyflow,
    get_intraday_trend,
    get_sector_top_stocks,
    get_sector_moneyflow_rank,
    get_limit_up_pool,
    get_market_snapshot,
)
from .data.tools_ta import get_technical_analysis
from .data.market_regime import get_market_context

# EOD 工具(Tushare 封装, 来自 finmcp-a-stock-data MIT)
from .data.eod.quote import get_latest_quote
from .data.eod.search import search_stocks_by_name
from .data.eod.news import get_stock_news
from .data.eod.financial import (
    get_financial_indicator,
    get_earnings_forecast,
    get_financial_report_summary,
)
from .data.eod.basic import get_stock_basic_info
from .data.eod.index import get_index_price
from .data.eod.price import get_stock_price


TOOL_REGISTRY = {
    # 实时 (东财)
    "get_realtime_moneyflow": get_realtime_moneyflow,
    "get_intraday_trend": get_intraday_trend,
    "get_sector_top_stocks": get_sector_top_stocks,
    "get_sector_moneyflow_rank": get_sector_moneyflow_rank,
    "get_limit_up_pool": get_limit_up_pool,
    "get_market_snapshot": get_market_snapshot,
    "get_market_context": get_market_context,
    # 技术指标 (自研)
    "get_technical_analysis": get_technical_analysis,
    # EOD (Tushare)
    "get_latest_quote": get_latest_quote,
    "search_stocks_by_name": search_stocks_by_name,
    "get_stock_news": get_stock_news,
    "get_financial_indicator": get_financial_indicator,
    "get_earnings_forecast": get_earnings_forecast,
    "get_financial_report_summary": get_financial_report_summary,
    "get_stock_basic_info": get_stock_basic_info,
    "get_index_price": get_index_price,
    "get_stock_price": get_stock_price,
}
