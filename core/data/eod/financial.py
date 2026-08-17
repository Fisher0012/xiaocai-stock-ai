"""get_financial_indicator 和 get_financial_report_summary tools"""

from typing import Any

from ._common.errors import FinMCPError, InvalidParamError
from ._common.responses import error_response, ok_response
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


# 合法的 indicator 名称
VALID_INDICATORS = {
    "roe", "roa", "gross_margin", "net_margin",
    "revenue_yoy", "net_profit_yoy",
    "debt_to_asset", "current_ratio",
    "asset_turnover", "inventory_turnover",
    "pe_ttm", "pb", "ps_ttm",
    "eps", "bvps", "ocf_per_share",
}


def get_financial_indicator(
    stock_code: str,
    indicators: list[str] | None = None,
    years: int = 5,
) -> dict[str, Any]:
    """获取个股的核心财务指标，按报告期返回。

    indicators 支持：
    - 盈利能力：roe, roa, gross_margin, net_margin
    - 成长性：revenue_yoy, net_profit_yoy
    - 偿债能力：debt_to_asset, current_ratio
    - 运营效率：asset_turnover, inventory_turnover
    - 估值：pe_ttm, pb, ps_ttm
    - 其他：eps, bvps, ocf_per_share

    indicators=None 返回全部指标。years 控制返回多少年数据（默认 5 年，最大 20 年）。
    返回数据按报告期降序排列。

    典型场景：财务分析、ROE/利润趋势分析、估值对比时调用。
    """
    try:
        code = normalize_stock_code(stock_code)
    except ValueError as e:
        return handle_tool_error(InvalidParamError(str(e)))

    # 校验 indicators
    if indicators:
        invalid = [i for i in indicators if i not in VALID_INDICATORS]
        if invalid:
            return error_response(
                code="INVALID_PARAM",
                message=f"不支持的指标: {invalid}",
                hint=f"支持的指标: {sorted(VALID_INDICATORS)}",
            )

    years = min(max(1, years), 20)

    try:
        source = _get_source()
        ind_key = ",".join(sorted(indicators)) if indicators else "all"
        cache_key = _cache.make_key(
            source.name, "fina_indicator", code, ind_key, str(years),
        )
        cached = _cache.get(cache_key)
        if cached is not None:
            return ok_response(data=cached, source=source.name, cache_hit=True)

        results = source.get_financial_indicator(code, indicators, years)
        _cache.set(cache_key, results, ttl_category="financial")
        return ok_response(data=results, source=source.name)

    except FinMCPError as e:
        return handle_tool_error(e, source=_get_source().name if _source else "unknown")
    except Exception as e:
        return handle_tool_error(e)


def get_financial_report_summary(
    stock_code: str,
    report_period: str | None = None,
) -> dict[str, Any]:
    """获取个股指定报告期的财报关键科目摘要。

    report_period 格式 "YYYY-MM-DD"，必须是季度末日期（03-31/06-30/09-30/12-31）。
    为 None 时返回最新一期。

    返回三大表关键科目：
    - 利润表：营收、毛利、营业利润、净利润、扣非净利润、研发费用、销售费用
    - 资产负债表：总资产、总负债、股东权益、货币资金、应收账款、存货、商誉
    - 现金流量表：经营性现金流、投资性现金流、筹资性现金流、自由现金流

    金额单位：元（人民币）。

    典型场景：财报分析、深度研究、不同公司财报对比时调用。
    """
    try:
        code = normalize_stock_code(stock_code)
    except ValueError as e:
        return handle_tool_error(InvalidParamError(str(e)))

    # 校验 report_period 格式
    ts_period = None
    if report_period:
        valid_endings = ("03-31", "06-30", "09-30", "12-31")
        if report_period[5:] not in valid_endings:
            return error_response(
                code="INVALID_PARAM",
                message=f"report_period 必须是季度末日期，收到: {report_period}",
                hint="有效值示例：2024-12-31, 2024-09-30, 2024-06-30, 2024-03-31",
            )
        ts_period = report_period.replace("-", "")

    try:
        source = _get_source()
        cache_key = _cache.make_key(
            source.name, "fina_report", code, ts_period or "latest",
        )
        cached = _cache.get(cache_key)
        if cached is not None:
            return ok_response(data=cached, source=source.name, cache_hit=True)

        result = source.get_financial_report(code, ts_period)
        _cache.set(cache_key, result, ttl_category="financial")
        return ok_response(data=result, source=source.name)

    except FinMCPError as e:
        return handle_tool_error(e, source=_get_source().name if _source else "unknown")
    except Exception as e:
        return handle_tool_error(e)


def get_earnings_forecast(stock_code: str) -> dict:
    """业绩预告 (tushare forecast): 预增/预减/扭亏 + 净利润区间 + 变动原因。
    业绩超预期是大涨核心驱动, 业绩雷是大跌核心驱动。"""
    try:
        import tushare as ts
        pro = ts.pro_api()
        df = pro.forecast(ts_code=stock_code,
                          fields="ann_date,end_date,type,p_change_min,p_change_max,net_profit_min,net_profit_max,change_reason,summary")
        if df is None or df.empty:
            return {"ok": True, "data": {"forecasts": [], "note": "近期无业绩预告"}}
        df = df.head(5).fillna("")
        rows = []
        for _, r in df.iterrows():
            rows.append({
                "ann_date": str(r.get("ann_date", "")),
                "end_date": str(r.get("end_date", "")),
                "type": r.get("type", ""),
                "p_change_min": float(r.get("p_change_min") or 0),
                "p_change_max": float(r.get("p_change_max") or 0),
                "net_profit_min_yi": round(float(r.get("net_profit_min") or 0) / 1e8, 2),
                "net_profit_max_yi": round(float(r.get("net_profit_max") or 0) / 1e8, 2),
                "change_reason": (r.get("change_reason") or "")[:200],
                "summary": (r.get("summary") or "")[:200],
            })
        return {"ok": True, "data": {"forecasts": rows}}
    except Exception as e:
        return {"ok": False, "error": str(e)[:200]}
