"""search_stocks_by_name tool"""

from typing import Any

from ._common.errors import FinMCPError
from ._common.responses import error_response, ok_response

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


def search_stocks_by_name(query: str, limit: int = 10) -> dict[str, Any]:
    """按公司名称模糊搜索 A 股股票，返回匹配的股票代码列表。

    支持中文全名、简称、拼音首字母（如 "茅台"、"mt"、"贵州茅台"均能命中 600519）。
    返回结果按市值降序排列。limit 默认 10，最大 100。

    典型场景：用户提到公司名但没给代码时，先用此工具解析代码。

    注意：拼音搜索仅匹配首字母缩写，不支持全拼。
    """
    if not query or not query.strip():
        return error_response(
            code="INVALID_PARAM",
            message="搜索关键词不能为空",
            hint="请提供公司名称、简称或拼音首字母",
        )

    limit = min(max(1, limit), 100)

    try:
        source = _get_source()
        # 搜索结果缓存 1 天（基础信息类）
        cache_key = _cache.make_key(source.name, "search", query, str(limit))
        cached = _cache.get(cache_key)
        if cached is not None:
            return ok_response(data=cached, source=source.name, cache_hit=True)

        results = source.search_stocks(query, limit)
        _cache.set(cache_key, results, ttl_category="basic_info")
        return ok_response(data=results, source=source.name)

    except FinMCPError as e:
        return handle_tool_error(e, source=_get_source().name if _source else "unknown")
    except Exception as e:
        return handle_tool_error(e)
