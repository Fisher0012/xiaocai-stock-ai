"""a-stock-data 包专属错误处理

将 FinMCPError 异常转换为标准 error_response。
"""

from typing import Any

from ._common.errors import FinMCPError
from ._common.responses import error_response


def handle_tool_error(e: Exception, source: str = "unknown") -> dict[str, Any]:
    """将异常转换为标准 error_response

    Args:
        e: 捕获的异常
        source: 数据源名称

    Returns:
        标准 error_response dict
    """
    if isinstance(e, FinMCPError):
        return error_response(
            code=e.code,
            message=str(e),
            hint=e.hint,
            source=source,
        )

    # 未预期的异常
    return error_response(
        code="INTERNAL_ERROR",
        message=f"内部错误: {e}",
        hint="请在 GitHub 提交 issue 报告此问题",
        source=source,
    )
