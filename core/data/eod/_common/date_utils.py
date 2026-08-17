"""日期工具

提供交易日判断、日期格式化等辅助函数。
MVP 阶段使用简单的周末判断，Stage 2 可接入真实交易日历。
"""

from datetime import date, datetime, timedelta


def parse_date(date_str: str) -> date:
    """解析 YYYY-MM-DD 格式的日期字符串

    Args:
        date_str: 日期字符串，格式 YYYY-MM-DD

    Returns:
        date 对象

    Raises:
        ValueError: 格式不正确
    """
    try:
        return datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError as e:
        raise ValueError(
            f"日期格式错误: '{date_str}'，请使用 YYYY-MM-DD 格式（如 2026-05-14）"
        ) from e


def format_date(d: date) -> str:
    """将 date 对象格式化为 YYYY-MM-DD 字符串"""
    return d.strftime("%Y-%m-%d")


def is_weekend(d: date) -> bool:
    """判断是否为周末"""
    return d.weekday() >= 5


def is_likely_trading_day(d: date) -> bool:
    """简易交易日判断（仅排除周末）

    注意：不处理节假日，Stage 2 会接入真实交易日历。
    """
    return not is_weekend(d)


def get_recent_trading_date(d: date | None = None) -> date:
    """获取最近的可能交易日（往前推到非周末）

    Args:
        d: 基准日期，默认为今天
    """
    if d is None:
        d = date.today()
    while is_weekend(d):
        d = d - timedelta(days=1)
    return d


def date_range_or_default(
    start_date: str | None,
    end_date: str | None,
    default_days: int = 60,
) -> tuple[date, date]:
    """解析日期范围，未指定时使用默认范围

    Args:
        start_date: 起始日期（YYYY-MM-DD），可为 None
        end_date: 结束日期（YYYY-MM-DD），可为 None
        default_days: 未指定日期时的默认天数

    Returns:
        (start, end) 日期元组
    """
    end = parse_date(end_date) if end_date else date.today()
    start = parse_date(start_date) if start_date else end - timedelta(days=default_days)
    return start, end
