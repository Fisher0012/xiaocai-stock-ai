"""get_index_price tool"""

from typing import Any

from ._common.date_utils import date_range_or_default, format_date
from ._common.errors import FinMCPError, InvalidParamError
from ._common.responses import ok_response

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


def get_index_price(
    index_code: str,
    start_date: str | None = None,
    end_date: str | None = None,
    period: str = "daily",
) -> dict[str, Any]:
    """获取主要 A 股指数的历史行情。

    支持常见指数：
    - 000001.SH (上证指数)
    - 399001.SZ (深证成指)
    - 399006.SZ (创业板指)
    - 000300.SH (沪深300)
    - 000905.SH (中证500)
    - 000852.SH (中证1000)
    等约 30 个主流指数。

    index_code 必须带交易所后缀（如 000001.SH），因为 000001 同时是上证指数和平安银行。
    period: daily / weekly / monthly。
    start_date / end_date 格式 YYYY-MM-DD；都为 None 时返回最近 60 个交易日。

    典型场景：分析大盘走势、计算个股相对收益时调用。
    """
    if not index_code or "." not in index_code:
        return handle_tool_error(
            InvalidParamError(
                f"指数代码必须带交易所后缀，如 000001.SH，收到: {index_code}",
                hint="上证指数用 000001.SH，沪深300 用 000300.SH",
            )
        )

    if period not in ("daily", "weekly", "monthly"):
        return handle_tool_error(
            InvalidParamError(f"period 必须是 daily/weekly/monthly，收到: {period}")
        )

    try:
        start, end = date_range_or_default(start_date, end_date, default_days=120)
    except ValueError as e:
        return handle_tool_error(InvalidParamError(str(e)))

    ts_start = format_date(start).replace("-", "")
    ts_end = format_date(end).replace("-", "")

    try:
        source = _get_source()
        cache_key = _cache.make_key(
            source.name, "index", index_code, ts_start, ts_end, period,
        )
        cached = _cache.get(cache_key)
        if cached is not None:
            return ok_response(data=cached, source=source.name, cache_hit=True)

        results = source.get_index_price(index_code, ts_start, ts_end, period)
        _cache.set(cache_key, results, ttl_category="daily")
        return ok_response(data=results, source=source.name)

    except FinMCPError as e:
        return handle_tool_error(e, source=_get_source().name if _source else "unknown")
    except Exception as e:
        return handle_tool_error(e)
