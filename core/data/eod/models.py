"""Pydantic 数据模型

定义所有 tool 返回数据的结构，用于数据规整和类型校验。
"""

from pydantic import BaseModel


class StockSearchResult(BaseModel):
    """搜索结果条目"""
    stock_code: str
    name: str
    industry: str = ""
    market_cap_yi: float | None = None


class StockBasicInfo(BaseModel):
    """个股基础信息"""
    stock_code: str
    name: str
    full_name: str = ""
    english_name: str = ""
    industry_l1: str = ""
    industry_l2: str = ""
    industry_l3: str = ""
    list_date: str = ""
    total_share: float | None = None
    float_share: float | None = None
    area: str = ""
    business_scope: str = ""


class PriceBar(BaseModel):
    """行情数据条"""
    date: str
    open: float
    high: float
    low: float
    close: float
    volume: float
    amount: float
    pct_change: float | None = None
    turnover_rate: float | None = None


class LatestQuote(BaseModel):
    """实时报价快照"""
    stock_code: str
    name: str = ""
    current_price: float
    change: float
    pct_change: float
    open: float
    high: float
    low: float
    prev_close: float
    volume: float
    amount: float
    market_cap_yi: float | None = None
    pe_ttm: float | None = None
    pb: float | None = None


class IndustryConstituent(BaseModel):
    """行业成份股"""
    stock_code: str
    name: str
    industry: str = ""


class FinancialIndicatorRow(BaseModel):
    """财务指标行"""
    report_period: str
    roe: float | None = None
    roa: float | None = None
    gross_margin: float | None = None
    net_margin: float | None = None
    revenue_yoy: float | None = None
    net_profit_yoy: float | None = None
    debt_to_asset: float | None = None
    current_ratio: float | None = None
    asset_turnover: float | None = None
    inventory_turnover: float | None = None
    pe_ttm: float | None = None
    pb: float | None = None
    ps_ttm: float | None = None
    eps: float | None = None
    bvps: float | None = None
    ocf_per_share: float | None = None


class FinancialReportSummary(BaseModel):
    """财报关键科目摘要"""
    stock_code: str
    report_period: str
    # 利润表
    revenue: float | None = None
    gross_profit: float | None = None
    operating_profit: float | None = None
    net_profit: float | None = None
    net_profit_deducted: float | None = None
    rd_expense: float | None = None
    selling_expense: float | None = None
    # 资产负债表
    total_assets: float | None = None
    total_liabilities: float | None = None
    equity: float | None = None
    cash: float | None = None
    accounts_receivable: float | None = None
    inventory: float | None = None
    goodwill: float | None = None
    # 现金流量表
    operating_cashflow: float | None = None
    investing_cashflow: float | None = None
    financing_cashflow: float | None = None
    free_cashflow: float | None = None
