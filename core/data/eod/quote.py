"""get_latest_quote tool

优先使用新浪财经实时行情（延迟秒级），失败时回退到数据源的日线数据。
新浪不提供估值指标（PE/PB/市值），由 tushare daily_basic 补充。
"""

from typing import Any

from ._common.errors import FinMCPError, InvalidParamError
from ._common.logging import get_logger
from ._common.responses import ok_response
from ._common.stock_code import normalize_stock_code

from .cache import CacheManager
from .errors import handle_tool_error
from .realtime import fetch_sina_realtime
from .utils import get_data_source

logger = get_logger(__name__)

_cache = CacheManager()
_source = None


def _get_source():  # noqa: ANN202
    global _source
    if _source is None:
        _source = get_data_source()
    return _source


def _enrich_valuation(result: dict[str, Any], stock_code: str) -> None:
    """用 tushare daily_basic 补充估值指标（PE/PB/市值），原地修改 result"""
    try:
        source = _get_source()
        if source.name != "tushare":
            return
        # 直接调用 tushare API 获取估值
        df_basic = source._pro.daily_basic(
            ts_code=stock_code,
            fields="ts_code,pe_ttm,pb,total_mv",
        )
        if df_basic is not None and not df_basic.empty:
            row = df_basic.iloc[0]
            pe_ttm = row.get("pe_ttm")
            pb = row.get("pb")
            total_mv = row.get("total_mv")
            if pe_ttm is not None and pe_ttm == pe_ttm:
                result["pe_ttm"] = pe_ttm
            if pb is not None and pb == pb:
                result["pb"] = pb
            if total_mv is not None and total_mv == total_mv:
                result["market_cap_yi"] = round(total_mv / 10000, 2)
    except Exception:
        logger.debug("补充 %s 估值指标失败，跳过", stock_code)


def get_latest_quote(stock_code: str) -> dict[str, Any]:
    """获取 A 股个股的当前快照（盘中实时，收盘后为收盘数据）。

    返回字段：current_price, change, pct_change, open, high, low,
    prev_close, volume, amount, market_cap_yi, pe_ttm, pb。

    stock_code 支持 "600519"（自动识别）或 "600519.SH" 格式。

    典型场景：用户问"XX 现在多少钱"、"今天涨了多少"时调用。

    数据来源优先级：新浪财经实时 → tushare 日线（回退）。
    注意：缓存 TTL 60 秒，频繁调用同一代码会返回缓存值。
    """
    try:
        code = normalize_stock_code(stock_code)
    except ValueError as e:
        return handle_tool_error(InvalidParamError(str(e)))

    # 检查缓存
    cache_key = _cache.make_key("realtime", "quote", code)
    cached = _cache.get(cache_key)
    if cached is not None:
        return ok_response(data=cached, source=cached.get("_source", "cache"), cache_hit=True)

    # 优先：新浪财经实时行情
    result = fetch_sina_realtime(code)
    if result is not None:
        _enrich_valuation(result, code)
        result["_source"] = "sina_realtime"
        _cache.set(cache_key, result, ttl_category="realtime")
        return ok_response(data=result, source="sina_realtime")

    # 回退：数据源日线数据
    logger.info("新浪实时行情不可用，回退到数据源: %s", code)
    try:
        source = _get_source()
        result = source.get_latest_quote(code)
        result["_source"] = source.name
        _cache.set(cache_key, result, ttl_category="realtime")
        return ok_response(data=result, source=source.name)

    except FinMCPError as e:
        return handle_tool_error(e, source=_get_source().name if _source else "unknown")
    except Exception as e:
        return handle_tool_error(e)
