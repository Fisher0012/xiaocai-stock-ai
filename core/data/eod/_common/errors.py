"""FinMCP 错误类型

标准错误码对应的异常类，用于在 tool 实现中抛出，由 server 层统一捕获并转换为 error_response。
"""


class FinMCPError(Exception):
    """FinMCP 基础异常"""

    code: str = "INTERNAL_ERROR"
    hint: str | None = None

    def __init__(self, message: str, hint: str | None = None) -> None:
        super().__init__(message)
        if hint is not None:
            self.hint = hint


class InvalidParamError(FinMCPError):
    """参数格式错误"""

    code = "INVALID_PARAM"


class DataNotFoundError(FinMCPError):
    """数据不存在"""

    code = "DATA_NOT_FOUND"


class RateLimitedError(FinMCPError):
    """上游数据源限流"""

    code = "RATE_LIMITED"

    def __init__(self, message: str = "上游数据源限流，请稍后重试") -> None:
        super().__init__(message, hint="等待 30-60 秒后重试")


class UpstreamError(FinMCPError):
    """上游数据源故障"""

    code = "UPSTREAM_ERROR"


class NotTradingDayError(FinMCPError):
    """非交易日"""

    code = "NOT_TRADING_DAY"

    def __init__(self, date_str: str) -> None:
        super().__init__(
            f"{date_str} 为非交易日",
            hint="建议使用最近的交易日，或不指定日期以获取最新数据",
        )


class AuthRequiredError(FinMCPError):
    """需要 API key"""

    code = "AUTH_REQUIRED"
