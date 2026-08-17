"""股票代码归一化

内部统一使用 {code}.{exchange} 格式（如 600519.SH），
但 tool 接口接受纯 6 位代码（自动识别交易所）。
"""

import re

# 6 位纯数字
_CODE_PATTERN = re.compile(r"^\d{6}$")
# 带交易所后缀
_FULL_PATTERN = re.compile(r"^(\d{6})\.(SH|SZ|BJ)$", re.IGNORECASE)


def normalize_stock_code(code: str) -> str:
    """将股票代码归一化为 {code}.{exchange} 格式

    Args:
        code: 股票代码，支持 "600519" 或 "600519.SH" 两种格式

    Returns:
        归一化后的代码，如 "600519.SH"

    Raises:
        ValueError: 代码格式无法识别
    """
    code = code.strip()

    # 已经是完整格式
    match = _FULL_PATTERN.match(code)
    if match:
        return f"{match.group(1)}.{match.group(2).upper()}"

    # 纯 6 位数字，自动推断交易所
    if _CODE_PATTERN.match(code):
        return f"{code}.{_infer_exchange(code)}"

    raise ValueError(
        f"无法识别的股票代码格式: '{code}'，"
        f"请使用 6 位代码（如 600519）或带后缀格式（如 600519.SH）"
    )


def parse_stock_code(full_code: str) -> tuple[str, str]:
    """将完整代码拆分为 (code, exchange)

    Args:
        full_code: 归一化后的代码，如 "600519.SH"

    Returns:
        (code, exchange) 元组，如 ("600519", "SH")
    """
    match = _FULL_PATTERN.match(full_code)
    if not match:
        raise ValueError(f"无效的完整股票代码格式: '{full_code}'")
    return match.group(1), match.group(2).upper()


def _infer_exchange(code: str) -> str:
    """根据 6 位代码推断交易所

    规则：
    - 6/9 开头 → 上交所 (SH)
    - 0/2/3 开头 → 深交所 (SZ)
    - 4/8 开头 → 北交所 (BJ)
    """
    first = code[0]
    if first in ("6", "9"):
        return "SH"
    if first in ("0", "2", "3"):
        return "SZ"
    if first in ("4", "8"):
        return "BJ"
    raise ValueError(f"无法根据代码 '{code}' 推断交易所，首位 '{first}' 不在已知范围内")
