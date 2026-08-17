"""get_stock_price tool"""

from typing import Any

from ._common.date_utils import date_range_or_default, format_date
from ._common.errors import FinMCPError, InvalidParamError
from ._common.responses import ok_response
from ._common.stock_code import normalize_stock_code

from .cache import CacheManager
from .errors import handle_tool_error
from .utils import get_data_source

_cache = CacheManager()
_source = None


def _get_source():  # noqa: ANN202
    global _source
    if _source is None:
        _source = get_data_source()
    return _source


def get_stock_price(
    stock_code: str,
    start_date: str | None = None,
    end_date: str | None = None,
    period: str = "daily",
    adjust: str = "qfq",
) -> dict[str, Any]:
    """获取 A 股个股的历史行情。

    period: daily（日线）/ weekly（周线）/ monthly（月线）。
    adjust: qfq（前复权）/ hfq（后复权）/ none（不复权）。
    start_date / end_date 格式 YYYY-MM-DD；都为 None 时返回最近 60 个交易日。

    返回字段：date, open, high, low, close, volume, amount, pct_change, turnover_rate。

    典型场景：分析走势、计算涨跌、回测时调用。

    注意：当日数据需在收盘后获取才完整；盘中数据的 close 为最新价而非收盘价。
    """
    try:
        code = normalize_stock_code(stock_code)
    except ValueError as e:
        return handle_tool_error(InvalidParamError(str(e)))

    if period not in ("daily", "weekly", "monthly"):
        return handle_tool_error(
            InvalidParamError(
                f"period 必须是 daily/weekly/monthly，收到: {period}",
                hint="日线用 daily，周线用 weekly，月线用 monthly",
            )
        )

    if adjust not in ("qfq", "hfq", "none"):
        return handle_tool_error(
            InvalidParamError(f"adjust 必须是 qfq/hfq/none，收到: {adjust}")
        )

    try:
        start, end = date_range_or_default(start_date, end_date, default_days=120)
    except ValueError as e:
        return handle_tool_error(InvalidParamError(str(e)))

    # tushare 日期格式 YYYYMMDD
    ts_start = format_date(start).replace("-", "")
    ts_end = format_date(end).replace("-", "")

    try:
        source = _get_source()
        cache_key = _cache.make_key(
            source.name, "price", code, ts_start, ts_end, period, adjust,
        )
        cached = _cache.get(cache_key)
        if cached is not None:
            return ok_response(data=cached, source=source.name, cache_hit=True)

        results = source.get_daily_price(code, ts_start, ts_end, period, adjust)
        _cache.set(cache_key, results, ttl_category="daily")
        return ok_response(data=results, source=source.name)

    except FinMCPError as e:
        return handle_tool_error(e, source=_get_source().name if _source else "unknown")
    except Exception as e:
        return handle_tool_error(e)
