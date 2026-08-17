"""统一响应构造器

所有 FinMCP tool 的返回值必须通过本模块构造，确保结构一致。
"""

from datetime import datetime, timedelta, timezone
from typing import Any

# 北京时间（UTC+8）
_CST = timezone(timedelta(hours=8))


def _now_cst() -> str:
    """返回当前北京时间的 ISO 8601 字符串"""
    return datetime.now(_CST).isoformat(timespec="seconds")


def ok_response(
    data: Any,
    source: str,
    cache_hit: bool = False,
    note: str | None = None,
) -> dict[str, Any]:
    """构造成功响应

    Args:
        data: 实际数据（dict 或 list）
        source: 数据源标识（如 "akshare", "tushare"）
        cache_hit: 是否命中缓存
        note: 可选的补充说明
    """
    meta: dict[str, Any] = {
        "source": source,
        "fetched_at": _now_cst(),
        "cache_hit": cache_hit,
    }
    if note is not None:
        meta["note"] = note

    return {
        "ok": True,
        "data": data,
        "meta": meta,
    }


def error_response(
    code: str,
    message: str,
    hint: str | None = None,
    source: str = "unknown",
) -> dict[str, Any]:
    """构造失败响应

    Args:
        code: 机读错误码（如 INVALID_PARAM, DATA_NOT_FOUND）
        message: 人读错误描述
        hint: LLM 可读的恢复建议
        source: 数据源标识
    """
    error: dict[str, str] = {
        "code": code,
        "message": message,
    }
    if hint is not None:
        error["hint"] = hint

    return {
        "ok": False,
        "error": error,
        "meta": {
            "source": source,
            "fetched_at": _now_cst(),
        },
    }
