"""get_stock_basic_info tool"""

from typing import Any

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


def get_stock_basic_info(stock_code: str) -> dict[str, Any]:
    """获取 A 股个股的基础信息。

    包括：公司全称、英文名、所属申万一级/二级/三级行业、上市日期、
    总股本、流通股本、注册地、主营业务简介。

    stock_code 支持 "600519"（自动识别）或 "600519.SH" 格式。

    典型场景：用户要求介绍某只股票、了解公司概况时调用。
    """
    try:
        code = normalize_stock_code(stock_code)
    except ValueError as e:
        return handle_tool_error(
            InvalidParamError(str(e), hint="请使用 6 位代码（如 600519）或带后缀格式（如 600519.SH）"),
        )

    try:
        source = _get_source()
        cache_key = _cache.make_key(source.name, "basic_info", code)
        cached = _cache.get(cache_key)
        if cached is not None:
            return ok_response(data=cached, source=source.name, cache_hit=True)

        result = source.get_basic_info(code)
        _cache.set(cache_key, result, ttl_category="basic_info")
        return ok_response(data=result, source=source.name)

    except FinMCPError as e:
        return handle_tool_error(e, source=_get_source().name if _source else "unknown")
    except Exception as e:
        return handle_tool_error(e)
