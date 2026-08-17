"""数据源抽象基类

所有数据源（akshare、tushare 等）都必须实现此接口。
"""

from abc import ABC, abstractmethod
from typing import Any


class StockDataSource(ABC):
    """A 股数据源抽象基类"""

    @property
    @abstractmethod
    def name(self) -> str:
        """数据源名称，用于 meta.source 字段"""
        ...

    @abstractmethod
    def search_stocks(self, query: str, limit: int = 10) -> list[dict[str, Any]]:
        """按名称模糊搜索股票

        Args:
            query: 搜索关键词（公司名、简称、拼音首字母）
            limit: 返回数量上限

        Returns:
            匹配的股票列表，每项包含 stock_code, name, industry 等
        """
        ...

    @abstractmethod
    def get_basic_info(self, stock_code: str) -> dict[str, Any]:
        """获取个股基础信息

        Args:
            stock_code: 归一化后的股票代码（如 600519.SH）
        """
        ...

    @abstractmethod
    def get_daily_price(
        self,
        stock_code: str,
        start_date: str,
        end_date: str,
        period: str = "daily",
        adjust: str = "qfq",
    ) -> list[dict[str, Any]]:
        """获取个股历史行情

        Args:
            stock_code: 归一化后的股票代码
            start_date: 起始日期 YYYYMMDD
            end_date: 结束日期 YYYYMMDD
            period: daily / weekly / monthly
            adjust: qfq / hfq / none
        """
        ...

    @abstractmethod
    def get_latest_quote(self, stock_code: str) -> dict[str, Any]:
        """获取实时报价快照

        Args:
            stock_code: 归一化后的股票代码
        """
        ...

    @abstractmethod
    def get_index_price(
        self,
        index_code: str,
        start_date: str,
        end_date: str,
        period: str = "daily",
    ) -> list[dict[str, Any]]:
        """获取指数历史行情

        Args:
            index_code: 指数代码（如 000001.SH）
            start_date: 起始日期 YYYYMMDD
            end_date: 结束日期 YYYYMMDD
            period: daily / weekly / monthly
        """
        ...

    @abstractmethod
    def get_industry_constituents(
        self,
        industry_code: str | None = None,
        industry_name: str | None = None,
        level: int = 1,
    ) -> list[dict[str, Any]]:
        """获取行业成份股

        Args:
            industry_code: 申万行业代码
            industry_name: 申万行业名称
            level: 行业分类级别 1/2/3
        """
        ...

    @abstractmethod
    def get_financial_indicator(
        self,
        stock_code: str,
        indicators: list[str] | None = None,
        years: int = 5,
    ) -> list[dict[str, Any]]:
        """获取核心财务指标

        Args:
            stock_code: 归一化后的股票代码
            indicators: 指标列表，None 返回全部
            years: 返回多少年数据
        """
        ...

    @abstractmethod
    def get_financial_report(
        self,
        stock_code: str,
        report_period: str | None = None,
    ) -> dict[str, Any]:
        """获取财报关键科目摘要

        Args:
            stock_code: 归一化后的股票代码
            report_period: 报告期 YYYYMMDD（0331/0630/0930/1231），None 返回最新一期
        """
        ...
