"""akshare 数据源适配

免费数据源，无需 API key。
"""

from typing import Any

from .base import StockDataSource


class AkshareSource(StockDataSource):
    """akshare 数据源（免费，零配置）"""

    @property
    def name(self) -> str:
        return "akshare"

    def search_stocks(self, query: str, limit: int = 10) -> list[dict[str, Any]]:
        raise NotImplementedError("Stage 2 实现（tushare 之后）")

    def get_basic_info(self, stock_code: str) -> dict[str, Any]:
        raise NotImplementedError("Stage 2 实现（tushare 之后）")

    def get_daily_price(
        self,
        stock_code: str,
        start_date: str,
        end_date: str,
        period: str = "daily",
        adjust: str = "qfq",
    ) -> list[dict[str, Any]]:
        raise NotImplementedError("Stage 2 实现（tushare 之后）")

    def get_latest_quote(self, stock_code: str) -> dict[str, Any]:
        raise NotImplementedError("Stage 2 实现（tushare 之后）")

    def get_index_price(
        self,
        index_code: str,
        start_date: str,
        end_date: str,
        period: str = "daily",
    ) -> list[dict[str, Any]]:
        raise NotImplementedError("Stage 2 实现（tushare 之后）")

    def get_industry_constituents(
        self,
        industry_code: str | None = None,
        industry_name: str | None = None,
        level: int = 1,
    ) -> list[dict[str, Any]]:
        raise NotImplementedError("Stage 2 实现（tushare 之后）")

    def get_financial_indicator(
        self,
        stock_code: str,
        indicators: list[str] | None = None,
        years: int = 5,
    ) -> list[dict[str, Any]]:
        raise NotImplementedError("Stage 2 实现（tushare 之后）")

    def get_financial_report(
        self,
        stock_code: str,
        report_period: str | None = None,
    ) -> dict[str, Any]:
        raise NotImplementedError("Stage 2 实现（tushare 之后）")
