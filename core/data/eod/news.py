"""个股新闻与公告 tool

数据来源：
- tushare anns_d: 公司公告（最权威）
- 东财公告 API: 补充覆盖
- 东财 7x24 快讯: 市场实时动态（按关键词过滤）
"""

from typing import Any

from ._common.errors import FinMCPError
from ._common.responses import error_response, ok_response

from .errors import handle_tool_error
from .utils import get_data_source

_source = None


def _get_source():  # noqa: ANN202
    global _source
    if _source is None:
        _source = get_data_source()
    return _source


def get_stock_news(stock_code: str, days: int = 30) -> dict[str, Any]:
    """获取个股相关的公告和市场新闻。

    整合公司公告（业绩预告、股权变动、重大合同等）和市场快讯，
    帮助分析近期可能影响股价的事件和信息。

    Args:
        stock_code: 股票代码（如 688256.SH）
        days: 查询天数（默认 30 天）
    """
    if not stock_code or not stock_code.strip():
        return error_response(
            code="INVALID_PARAM",
            message="stock_code 不能为空",
        )

    days = min(max(1, days), 90)

    try:
        source = _get_source()
        results = source.get_stock_news(stock_code, days)
        return ok_response(data=results, source=source.name)
    except FinMCPError as e:
        return handle_tool_error(e, source=_get_source().name if _source else "unknown")
    except Exception as e:
        return handle_tool_error(e)


def get_market_signals(stock_code: str, days: int = 5) -> dict[str, Any]:
    """获取个股近期市场异动信号。

    检测涨跌停、龙虎榜上榜等异常交易信号，
    帮助判断市场对该股票的关注度和资金动向。

    Args:
        stock_code: 股票代码（如 688256.SH）
        days: 查询天数（默认 5 个交易日）
    """
    if not stock_code or not stock_code.strip():
        return error_response(
            code="INVALID_PARAM",
            message="stock_code 不能为空",
        )

    days = min(max(1, days), 30)

    try:
        source = _get_source()
        results = source.get_market_signals(stock_code, days)
        return ok_response(data=results, source=source.name)
    except FinMCPError as e:
        return handle_tool_error(e, source=_get_source().name if _source else "unknown")
    except Exception as e:
        return handle_tool_error(e)
