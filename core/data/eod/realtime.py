"""新浪财经实时行情获取

轻量级单股实时行情，不依赖 tushare/akshare。
从日本等海外环境也可正常访问。
"""

import re
from typing import Any

import requests
from finmcp_common.logging import get_logger

logger = get_logger(__name__)

# 新浪财经实时行情 API
_SINA_HQ_URL = "https://hq.sinajs.cn/list="

# 内部代码 (002475.SZ) -> 新浪前缀 (sz002475)
_EXCHANGE_PREFIX = {"SZ": "sz", "SH": "sh", "BJ": "bj"}

# 新浪返回字段索引
_IDX_NAME = 0
_IDX_OPEN = 1
_IDX_PREV_CLOSE = 2
_IDX_CURRENT = 3
_IDX_HIGH = 4
_IDX_LOW = 5
_IDX_VOLUME = 8   # 成交量（股）
_IDX_AMOUNT = 9   # 成交额（元）
_IDX_DATE = 30
_IDX_TIME = 31


def _to_sina_symbol(stock_code: str) -> str:
    """将内部代码格式转为新浪格式: 002475.SZ -> sz002475"""
    code, exchange = stock_code.split(".")
    prefix = _EXCHANGE_PREFIX.get(exchange)
    if not prefix:
        raise ValueError(f"不支持的交易所后缀: {exchange}")
    return f"{prefix}{code}"


def _safe_float(val: str) -> float | None:
    """安全转换浮点数，空字符串或无效值返回 None"""
    try:
        v = float(val)
        return v if v == v else None  # NaN check
    except (ValueError, TypeError):
        return None


def fetch_sina_realtime(stock_code: str, timeout: int = 5) -> dict[str, Any] | None:
    """从新浪财经获取单股实时行情

    Args:
        stock_code: 内部格式股票代码（如 002475.SZ）
        timeout: 请求超时秒数

    Returns:
        行情字典（与 get_latest_quote 返回格式一致），失败返回 None
    """
    try:
        symbol = _to_sina_symbol(stock_code)
    except ValueError:
        logger.warning("无法转换股票代码 %s 为新浪格式", stock_code)
        return None

    try:
        resp = requests.get(
            f"{_SINA_HQ_URL}{symbol}",
            headers={"Referer": "https://finance.sina.com.cn"},
            timeout=timeout,
        )
        resp.raise_for_status()
    except Exception as e:
        logger.warning("新浪实时行情请求失败: %s", e)
        return None

    # 解析响应: var hq_str_sz002475="字段1,字段2,...";
    match = re.search(r'"(.+)"', resp.text)
    if not match:
        logger.warning("新浪实时行情响应格式异常: %s", resp.text[:200])
        return None

    parts = match.group(1).split(",")
    if len(parts) < 32:
        logger.warning("新浪实时行情字段不足: 期望>=32, 实际=%d", len(parts))
        return None

    # 停牌或无数据时，当前价为 0
    current_price = _safe_float(parts[_IDX_CURRENT])
    if not current_price:
        logger.info("股票 %s 当前价为 0，可能停牌", stock_code)
        return None

    prev_close = _safe_float(parts[_IDX_PREV_CLOSE]) or 0
    change = round(current_price - prev_close, 4) if prev_close else 0
    pct_change = round(change / prev_close * 100, 2) if prev_close else 0

    # 成交量：新浪返回的是股数，转为手（/100）保持与 tushare vol 单位一致
    volume_raw = _safe_float(parts[_IDX_VOLUME])
    volume = round(volume_raw / 100, 2) if volume_raw else None

    # 成交额：新浪返回元，转为千元保持与 tushare amount 单位一致
    amount_raw = _safe_float(parts[_IDX_AMOUNT])
    amount = round(amount_raw / 1000, 2) if amount_raw else None

    return {
        "stock_code": stock_code,
        "name": parts[_IDX_NAME],
        "current_price": current_price,
        "change": round(change, 2),
        "pct_change": pct_change,
        "open": _safe_float(parts[_IDX_OPEN]),
        "high": _safe_float(parts[_IDX_HIGH]),
        "low": _safe_float(parts[_IDX_LOW]),
        "prev_close": prev_close,
        "volume": volume,
        "amount": amount,
        # 估值指标新浪不提供，由调用方补充
        "market_cap_yi": None,
        "pe_ttm": None,
        "pb": None,
    }
