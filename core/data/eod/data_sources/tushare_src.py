"""Tushare Pro 数据源适配

需要环境变量 TUSHARE_TOKEN。
tushare 使用 {code}.{exchange} 格式，如 600519.SH，与内部格式一致。
"""

from typing import Any

import tushare as ts
from .._common.errors import (
    AuthRequiredError,
    DataNotFoundError,
    UpstreamError,
)
from .._common.logging import get_logger
from pandas import DataFrame

from .base import StockDataSource

logger = get_logger(__name__)


def _df_to_records(df: DataFrame) -> list[dict[str, Any]]:
    """将 DataFrame 转为 list[dict]，NaN 转为 None"""
    return [{k: (None if v != v else v) for k, v in row.items()} for _, row in df.iterrows()]


class TushareSource(StockDataSource):
    """Tushare Pro 数据源（付费，需要 token）"""

    def __init__(self, token: str) -> None:
        if not token:
            raise AuthRequiredError(
                "Tushare 数据源需要 TUSHARE_TOKEN 环境变量，"
                "请到 https://tushare.pro 注册并获取 token"
            )
        self._token = token
        ts.set_token(token)
        self._pro = ts.pro_api()
        logger.info("Tushare Pro 数据源初始化完成")

    @property
    def name(self) -> str:
        return "tushare"

    def search_stocks(self, query: str, limit: int = 10) -> list[dict[str, Any]]:
        """搜索股票 — 基于 stock_basic 全量列表做本地过滤

        匹配优先级：精确汉字包含 > 拼音全拼匹配（支持同音字）> 拼音首字母 > 代码前缀
        """
        try:
            df = self._pro.stock_basic(
                exchange="",
                list_status="L",
                fields="ts_code,name,industry,market,list_date",
            )
        except Exception as e:
            raise UpstreamError(f"tushare stock_basic 调用失败: {e}") from e

        if df is None or df.empty:
            return []

        query_lower = query.lower()

        # 第一层：精确汉字包含
        mask = df["name"].str.contains(query, na=False)

        # 第二层：拼音匹配（支持同音字、混合中英输入）
        if not mask.any():
            import re

            from pypinyin import Style, lazy_pinyin

            def _to_pinyin(text: str) -> str:
                """将中文文本转成全拼序列（纯小写字母）"""
                return "".join(lazy_pinyin(text, style=Style.NORMAL)).lower()

            def _build_char_pattern(text: str) -> str:
                """逐字符构建匹配模式
                中文字 → 全拼（匹配同音字），如"韩"→"han"
                ASCII字母 → 拼音首字母通配，如"J"→"j[a-z]*"
                支持：韩武J→寒武纪, BYD→比亚迪, 柠德S代→宁德时代
                """
                parts = []
                for ch in text:
                    if ch.isascii() and ch.isalpha():
                        parts.append(ch.lower() + "[a-z]*")
                    else:
                        py = "".join(lazy_pinyin(ch, style=Style.NORMAL)).lower()
                        parts.append(re.escape(py))
                return "".join(parts)

            # 是否包含 ASCII 字母（混合输入）
            has_ascii = any(ch.isascii() and ch.isalpha() for ch in query)

            query_py = _to_pinyin(query)
            df["_pinyin_full"] = df["name"].apply(_to_pinyin)

            # 先尝试全拼精确包含（同音字匹配）
            mask = df["_pinyin_full"].str.contains(query_py, na=False)

            # 如果有混合输入（中英混合或纯字母），再用逐字符模式匹配
            if not mask.any() and has_ascii:
                char_pattern = _build_char_pattern(query)
                mask = df["_pinyin_full"].str.contains(char_pattern, na=False, regex=True)

        # 第三层：拼音首字母匹配
        if not mask.any():
            from pypinyin import Style, lazy_pinyin

            def _get_initials(name: str) -> str:
                return "".join(lazy_pinyin(name, style=Style.FIRST_LETTER))

            if "_pinyin_initials" not in df.columns:
                df["_pinyin_initials"] = df["name"].apply(_get_initials)
            mask = df["_pinyin_initials"].str.lower().str.contains(query_lower, na=False)

        # 第四层：代码匹配（用户可能直接输代码前缀）
        mask = mask | df["ts_code"].str.startswith(query)

        matched = df[mask].head(limit)

        results = []
        for _, row in matched.iterrows():
            results.append({
                "stock_code": row["ts_code"],
                "name": row["name"],
                "industry": row.get("industry", ""),
                "market_cap_yi": None,  # stock_basic 不含市值，需要 daily_basic
            })
        return results

    def get_basic_info(self, stock_code: str) -> dict[str, Any]:
        """获取个股基础信息"""
        try:
            df = self._pro.stock_basic(
                ts_code=stock_code,
                fields="ts_code,name,fullname,enname,industry,area,"
                       "list_date,market,exchange,is_hs",
            )
        except Exception as e:
            raise UpstreamError(f"tushare stock_basic 调用失败: {e}") from e

        if df is None or df.empty:
            raise DataNotFoundError(
                f"未找到股票 {stock_code} 的基础信息",
                hint="请检查代码是否正确，或该股票是否已退市",
            )

        row = df.iloc[0]

        # 尝试获取申万行业分类（可能需要更高积分）
        industry_l1 = row.get("industry", "")
        industry_l2 = ""
        industry_l3 = ""

        # 获取股本信息
        total_share = None
        float_share = None
        try:
            df_share = self._pro.daily_basic(
                ts_code=stock_code,
                fields="ts_code,total_share,float_share",
            )
            if df_share is not None and not df_share.empty:
                share_row = df_share.iloc[0]
                total_share = share_row.get("total_share")
                float_share = share_row.get("float_share")
        except Exception:
            logger.debug("获取 %s 股本信息失败，跳过", stock_code)

        return {
            "stock_code": row["ts_code"],
            "name": row["name"],
            "full_name": row.get("fullname", ""),
            "english_name": row.get("enname", ""),
            "industry_l1": industry_l1,
            "industry_l2": industry_l2,
            "industry_l3": industry_l3,
            "list_date": row.get("list_date", ""),
            "total_share": total_share,
            "float_share": float_share,
            "area": row.get("area", ""),
            "business_scope": "",  # tushare stock_basic 不含此字段
        }

    def get_daily_price(
        self,
        stock_code: str,
        start_date: str,
        end_date: str,
        period: str = "daily",
        adjust: str = "qfq",
    ) -> list[dict[str, Any]]:
        """获取个股历史行情

        使用 ts.pro_bar 获取复权行情。
        tushare 日期格式为 YYYYMMDD。
        """
        # 映射复权参数
        adj_map = {"qfq": "qfq", "hfq": "hfq", "none": None}
        adj = adj_map.get(adjust, "qfq")

        # 映射周期
        freq_map = {"daily": "D", "weekly": "W", "monthly": "M"}
        freq = freq_map.get(period, "D")

        try:
            df = ts.pro_bar(
                ts_code=stock_code,
                start_date=start_date,
                end_date=end_date,
                freq=freq,
                adj=adj,
            )
        except Exception as e:
            raise UpstreamError(f"tushare pro_bar 调用失败: {e}") from e

        if df is None or df.empty:
            raise DataNotFoundError(
                f"未找到 {stock_code} 在 {start_date}~{end_date} 的行情数据",
                hint="可能原因：日期范围内无交易数据，或代码错误",
            )

        # tushare pro_bar 返回按日期降序，我们保持降序（最新在前）
        results = []
        for _, row in df.iterrows():
            trade_date = str(row["trade_date"])
            formatted_date = f"{trade_date[:4]}-{trade_date[4:6]}-{trade_date[6:8]}"
            results.append({
                "date": formatted_date,
                "open": row.get("open"),
                "high": row.get("high"),
                "low": row.get("low"),
                "close": row.get("close"),
                "volume": row.get("vol"),
                "amount": row.get("amount"),
                "pct_change": row.get("pct_chg"),
                "turnover_rate": None,  # pro_bar 不含换手率
            })
        return results

    def get_latest_quote(self, stock_code: str) -> dict[str, Any]:
        """获取实时/最新报价

        使用 daily_basic + daily 获取最新一天数据。
        """
        try:
            # 最新日线行情
            df_daily = ts.pro_bar(
                ts_code=stock_code,
                freq="D",
                adj="qfq",
            )
        except Exception as e:
            raise UpstreamError(f"tushare pro_bar 调用失败: {e}") from e

        if df_daily is None or df_daily.empty:
            raise DataNotFoundError(f"未找到 {stock_code} 的最新行情数据")

        latest = df_daily.iloc[0]
        prev = df_daily.iloc[1] if len(df_daily) > 1 else latest

        current_price = latest.get("close", 0)
        prev_close = prev.get("close", current_price)
        change = current_price - prev_close if prev_close else 0
        pct_change = latest.get("pct_chg", 0)

        # 获取估值指标
        pe_ttm = None
        pb = None
        market_cap_yi = None
        try:
            df_basic = self._pro.daily_basic(
                ts_code=stock_code,
                fields="ts_code,pe_ttm,pb,total_mv",
            )
            if df_basic is not None and not df_basic.empty:
                basic_row = df_basic.iloc[0]
                pe_ttm = basic_row.get("pe_ttm")
                pb = basic_row.get("pb")
                total_mv = basic_row.get("total_mv")
                if total_mv is not None:
                    market_cap_yi = round(total_mv / 10000, 2)
        except Exception:
            logger.debug("获取 %s 估值指标失败，跳过", stock_code)

        # 获取股票名称
        name = ""
        try:
            df_name = self._pro.stock_basic(
                ts_code=stock_code, fields="ts_code,name"
            )
            if df_name is not None and not df_name.empty:
                name = df_name.iloc[0]["name"]
        except Exception:
            pass

        return {
            "stock_code": stock_code,
            "name": name,
            "current_price": current_price,
            "change": round(change, 2) if change else 0,
            "pct_change": pct_change,
            "open": latest.get("open"),
            "high": latest.get("high"),
            "low": latest.get("low"),
            "prev_close": prev_close,
            "volume": latest.get("vol"),
            "amount": latest.get("amount"),
            "market_cap_yi": market_cap_yi,
            "pe_ttm": pe_ttm,
            "pb": pb,
        }

    def get_index_price(
        self,
        index_code: str,
        start_date: str,
        end_date: str,
        period: str = "daily",
    ) -> list[dict[str, Any]]:
        """获取指数历史行情"""
        try:
            df = self._pro.index_daily(
                ts_code=index_code,
                start_date=start_date,
                end_date=end_date,
            )
        except Exception as e:
            raise UpstreamError(f"tushare index_daily 调用失败: {e}") from e

        if df is None or df.empty:
            raise DataNotFoundError(
                f"未找到指数 {index_code} 在 {start_date}~{end_date} 的数据",
                hint="请检查指数代码是否正确（需带交易所后缀如 000001.SH）",
            )

        results = []
        for _, row in df.iterrows():
            trade_date = str(row["trade_date"])
            formatted_date = f"{trade_date[:4]}-{trade_date[4:6]}-{trade_date[6:8]}"
            results.append({
                "date": formatted_date,
                "open": row.get("open"),
                "high": row.get("high"),
                "low": row.get("low"),
                "close": row.get("close"),
                "volume": row.get("vol"),
                "amount": row.get("amount"),
                "pct_change": row.get("pct_chg"),
            })
        return results

    def get_industry_constituents(
        self,
        industry_code: str | None = None,
        industry_name: str | None = None,
        level: int = 1,
    ) -> list[dict[str, Any]]:
        """获取申万行业成份股

        tushare 使用 index_classify (行业列表) + index_member (成份股)。
        """
        # 在指定级别及所有级别中搜索行业
        # 申万行业名称带罗马数字后缀（如"白酒Ⅱ"），需模糊匹配
        level_map = {1: "L1", 2: "L2", 3: "L3"}
        search_levels = [level_map.get(level, "L1")]
        # 如果指定级别找不到，自动扩展到其他级别
        for lv in ["L1", "L2", "L3"]:
            if lv not in search_levels:
                search_levels.append(lv)

        target_index = None
        target_name = ""

        for ts_level in search_levels:
            try:
                df_classify = self._pro.index_classify(
                    level=ts_level, src="SW2021"
                )
            except Exception as e:
                raise UpstreamError(f"tushare index_classify 调用失败: {e}") from e

            if df_classify is None or df_classify.empty:
                continue

            if industry_code:
                mask = df_classify["index_code"] == industry_code
            elif industry_name:
                mask = df_classify["industry_name"].str.contains(industry_name, na=False)
            else:
                continue

            if mask.any():
                target_index = df_classify[mask].iloc[0]["index_code"]
                target_name = df_classify[mask].iloc[0]["industry_name"]
                break

        if not target_index:
            raise DataNotFoundError(
                f"未找到行业: code={industry_code}, name={industry_name}",
                hint="申万行业名称可能带级别后缀（如'白酒Ⅱ'），建议用关键词搜索",
            )

        # 获取成份股
        try:
            df_members = self._pro.index_member(index_code=target_index)
        except Exception as e:
            raise UpstreamError(f"tushare index_member 调用失败: {e}") from e

        if df_members is None or df_members.empty:
            return []

        # 过滤在列的成份股（is_new == 'Y' 或无 out_date）
        if "is_new" in df_members.columns:
            current = df_members[df_members["is_new"] == "Y"]
        else:
            current = df_members[df_members["out_date"].isna()]

        results = []
        for _, row in current.iterrows():
            results.append({
                "stock_code": row.get("con_code", ""),
                "name": row.get("con_name", ""),
                "industry": target_name,
            })
        return results

    def get_financial_indicator(
        self,
        stock_code: str,
        indicators: list[str] | None = None,
        years: int = 5,
    ) -> list[dict[str, Any]]:
        """获取核心财务指标

        使用 tushare fina_indicator 接口。
        """
        try:
            df = self._pro.fina_indicator(
                ts_code=stock_code,
                fields="ts_code,ann_date,end_date,"
                       "roe,roa,grossprofit_margin,netprofit_margin,"
                       "revenue_yoy,net_profit_yoy,"
                       "debt_to_assets,current_ratio,"
                       "assets_turn,inventory_turn,"
                       "eps,bvps,ocfps",
            )
        except Exception as e:
            raise UpstreamError(f"tushare fina_indicator 调用失败: {e}") from e

        if df is None or df.empty:
            raise DataNotFoundError(
                f"未找到 {stock_code} 的财务指标数据",
                hint="请确认股票代码正确",
            )

        # 只保留年报（end_date 以 1231 结尾）和最近 years 年
        df["end_date"] = df["end_date"].astype(str)
        annual = df[df["end_date"].str.endswith("1231")].head(years)

        # 如果年报不够，也取半年报/季报
        if len(annual) < years:
            annual = df.head(years * 4)  # 取足够多的季报
            # 去重：每年只保留最新一期
            annual = annual.drop_duplicates(subset=["end_date"], keep="first")
            annual = annual.head(years * 4)

        # 获取估值指标（pe_ttm, pb, ps_ttm）需要从 daily_basic
        pe_map: dict[str, dict[str, float | None]] = {}
        try:
            df_valuation = self._pro.daily_basic(
                ts_code=stock_code,
                fields="ts_code,trade_date,pe_ttm,pb,ps_ttm",
            )
            if df_valuation is not None and not df_valuation.empty:
                # 取每年末最接近的估值
                for _, vrow in df_valuation.iterrows():
                    td = str(vrow.get("trade_date", ""))
                    if td:
                        pe_map[td] = {
                            "pe_ttm": vrow.get("pe_ttm"),
                            "pb": vrow.get("pb"),
                            "ps_ttm": vrow.get("ps_ttm"),
                        }
        except Exception:
            logger.debug("获取 %s 估值指标失败，跳过", stock_code)

        # 字段映射：tushare -> FinMCP
        field_map = {
            "roe": "roe",
            "roa": "roa",
            "grossprofit_margin": "gross_margin",
            "netprofit_margin": "net_margin",
            "revenue_yoy": "revenue_yoy",
            "net_profit_yoy": "net_profit_yoy",
            "debt_to_assets": "debt_to_asset",
            "current_ratio": "current_ratio",
            "assets_turn": "asset_turnover",
            "inventory_turn": "inventory_turnover",
            "eps": "eps",
            "bvps": "bvps",
            "ocfps": "ocf_per_share",
        }

        results = []
        for _, row in annual.iterrows():
            end_date = row["end_date"]
            formatted = f"{end_date[:4]}-{end_date[4:6]}-{end_date[6:8]}"

            record: dict[str, Any] = {"report_period": formatted}

            for ts_field, our_field in field_map.items():
                val = row.get(ts_field)
                record[our_field] = None if (val is None or val != val) else val

            # 附加估值指标
            valuation = pe_map.get(end_date, {})
            record["pe_ttm"] = valuation.get("pe_ttm")
            record["pb"] = valuation.get("pb")
            record["ps_ttm"] = valuation.get("ps_ttm")

            # 如果指定了 indicators，过滤
            if indicators:
                record = {
                    "report_period": formatted,
                    **{k: record.get(k) for k in indicators if k in record},
                }

            results.append(record)

        return results

    def get_financial_report(
        self,
        stock_code: str,
        report_period: str | None = None,
    ) -> dict[str, Any]:
        """获取财报关键科目摘要

        分别从 income（利润表）、balancesheet（资产负债表）、cashflow（现金流量表）获取。
        """
        # 构造查询参数
        kwargs: dict[str, str] = {"ts_code": stock_code}
        if report_period:
            # report_period 格式 YYYYMMDD
            kwargs["period"] = report_period

        # 利润表
        income_data: dict[str, Any] = {}
        try:
            df_income = self._pro.income(**kwargs)
            if df_income is not None and not df_income.empty:
                row = df_income.iloc[0]
                income_data = {
                    "revenue": row.get("revenue"),
                    "gross_profit": None,  # tushare income 不直接提供毛利
                    "operating_profit": row.get("operate_profit"),
                    "net_profit": row.get("n_income"),
                    "net_profit_deducted": row.get("n_income_attr_p"),
                    "rd_expense": row.get("rd_exp"),
                    "selling_expense": row.get("sell_exp"),
                    "report_period_raw": str(row.get("end_date", "")),
                }
                # 计算毛利 = 营收 - 营业成本
                revenue = row.get("revenue")
                oper_cost = row.get("oper_cost")
                if (
                    revenue is not None
                    and oper_cost is not None
                    and revenue == revenue  # NaN check
                    and oper_cost == oper_cost  # NaN check
                ):
                    income_data["gross_profit"] = revenue - oper_cost
        except Exception as e:
            logger.warning("获取 %s 利润表失败: %s", stock_code, e)

        # 资产负债表
        balance_data: dict[str, Any] = {}
        try:
            df_balance = self._pro.balancesheet(**kwargs)
            if df_balance is not None and not df_balance.empty:
                row = df_balance.iloc[0]
                balance_data = {
                    "total_assets": row.get("total_assets"),
                    "total_liabilities": row.get("total_liab"),
                    "equity": row.get("total_hldr_eqy_inc_min"),
                    "cash": row.get("money_cap"),
                    "accounts_receivable": row.get("accounts_receiv"),
                    "inventory": row.get("inventories"),
                    "goodwill": row.get("goodwill"),
                }
        except Exception as e:
            logger.warning("获取 %s 资产负债表失败: %s", stock_code, e)

        # 现金流量表
        cashflow_data: dict[str, Any] = {}
        try:
            df_cashflow = self._pro.cashflow(**kwargs)
            if df_cashflow is not None and not df_cashflow.empty:
                row = df_cashflow.iloc[0]
                operating_cf = row.get("n_cashflow_act")
                investing_cf = row.get("n_cashflow_inv_act")
                # 自由现金流 = 经营性现金流 - 资本支出（近似用投资活动现金流）
                free_cf = None
                if operating_cf is not None and operating_cf == operating_cf:
                    capex = row.get("c_pay_acq_const_fiolta")
                    if capex is not None and capex == capex:
                        free_cf = operating_cf - capex

                cashflow_data = {
                    "operating_cashflow": operating_cf,
                    "investing_cashflow": investing_cf,
                    "financing_cashflow": row.get("n_cash_flows_fnc_act"),
                    "free_cashflow": free_cf,
                }
        except Exception as e:
            logger.warning("获取 %s 现金流量表失败: %s", stock_code, e)

        if not income_data and not balance_data and not cashflow_data:
            raise DataNotFoundError(
                f"未找到 {stock_code} 的财报数据",
                hint="请确认代码正确，且该公司已披露财报",
            )

        # 确定 report_period
        raw_period = income_data.pop("report_period_raw", report_period or "")
        if raw_period and len(raw_period) == 8:
            formatted_period = f"{raw_period[:4]}-{raw_period[4:6]}-{raw_period[6:8]}"
        else:
            formatted_period = raw_period or ""

        # 清理 NaN
        def _clean(d: dict[str, Any]) -> dict[str, Any]:
            return {k: (None if v is not None and v != v else v) for k, v in d.items()}

        return {
            "stock_code": stock_code,
            "report_period": formatted_period,
            **_clean(income_data),
            **_clean(balance_data),
            **_clean(cashflow_data),
        }

    # ── 行业总览 ──

    def get_industry_overview(
        self,
        industry_name: str,
        level: int = 2,
        sort_by: str = "total_mv",
        limit: int = 50,
    ) -> dict[str, Any]:
        """获取行业全景：成份股 + 批量市场数据（市值/PE/PB），一次调用返回完整排名

        使用 daily_basic 批量接口获取全市场当日数据，与行业成份股做 join，
        避免逐只查询的性能瓶颈。
        """
        # 1. 获取行业成份股列表
        constituents = self.get_industry_constituents(
            industry_name=industry_name, level=level,
        )
        if not constituents:
            raise DataNotFoundError(
                f"未找到行业 '{industry_name}' 的成份股",
                hint="请检查行业名称是否正确，或尝试不同的 level（1/2/3）",
            )

        member_codes = {item["stock_code"] for item in constituents}
        industry_label = constituents[0].get("industry", industry_name) if constituents else industry_name

        # 用 stock_basic 补充名称（index_member 的 con_name 可能为空）
        name_map = {}
        try:
            df_names = self._pro.stock_basic(
                exchange="", list_status="L", fields="ts_code,name",
            )
            if df_names is not None and not df_names.empty:
                name_map = dict(zip(df_names["ts_code"], df_names["name"]))
        except Exception:
            # fallback: 用成份股列表里的 name
            name_map = {item["stock_code"]: item.get("name", "") for item in constituents}

        # 2. 获取最近交易日的 daily_basic 批量数据
        from datetime import datetime, timedelta

        df_basic = None
        # 尝试最近 5 个自然日（跳过非交易日）
        for offset in range(5):
            trade_date = (datetime.now() - timedelta(days=offset)).strftime("%Y%m%d")
            try:
                df_basic = self._pro.daily_basic(
                    trade_date=trade_date,
                    fields="ts_code,close,pe_ttm,pb,total_mv,circ_mv,turnover_rate",
                )
                if df_basic is not None and not df_basic.empty:
                    break
            except Exception:
                continue

        if df_basic is None or df_basic.empty:
            raise UpstreamError("daily_basic 批量数据获取失败，可能非交易时段")

        # 3. 筛选行业成份股
        df_industry = df_basic[df_basic["ts_code"].isin(member_codes)].copy()

        if df_industry.empty:
            # fallback: 仅返回成份股列表（无市场数据）
            return {
                "industry": industry_label,
                "level": level,
                "trade_date": trade_date,
                "total_count": len(constituents),
                "stocks": [{"stock_code": c["stock_code"], "name": c.get("name", "")} for c in constituents],
            }

        # 4. 排序
        sort_col = sort_by if sort_by in df_industry.columns else "total_mv"
        df_industry = df_industry.sort_values(sort_col, ascending=False, na_position="last")

        # 5. 组装结果
        stocks = []
        for _, row in df_industry.head(limit).iterrows():
            code = row["ts_code"]
            total_mv = row.get("total_mv")
            stocks.append({
                "stock_code": code,
                "name": name_map.get(code, ""),
                "close": row.get("close"),
                "pe_ttm": row.get("pe_ttm"),
                "pb": row.get("pb"),
                "market_cap_yi": round(total_mv / 10000, 2) if total_mv and total_mv == total_mv else None,
                "circ_mv_yi": round(row.get("circ_mv", 0) / 10000, 2) if row.get("circ_mv") and row.get("circ_mv") == row.get("circ_mv") else None,
                "turnover_rate": row.get("turnover_rate"),
            })

        # 行业汇总统计
        valid_mv = df_industry["total_mv"].dropna()
        valid_pe = df_industry["pe_ttm"].dropna()
        valid_pe = valid_pe[(valid_pe > 0) & (valid_pe < 1000)]  # 过滤异常值

        summary = {
            "total_market_cap_yi": round(valid_mv.sum() / 10000, 2) if not valid_mv.empty else None,
            "avg_pe_ttm": round(valid_pe.median(), 2) if not valid_pe.empty else None,
            "stock_count": len(df_industry),
        }

        return {
            "industry": industry_label,
            "level": level,
            "trade_date": trade_date,
            "summary": summary,
            "total_count": len(df_industry),
            "stocks": stocks,
        }

    # ── 新闻与公告 ──

    def get_stock_news(self, stock_code: str, days: int = 30) -> dict[str, Any]:
        """获取个股公告 + 东财快讯（多源聚合）"""
        from datetime import datetime, timedelta

        end_date = datetime.now().strftime("%Y%m%d")
        start_date = (datetime.now() - timedelta(days=days)).strftime("%Y%m%d")

        announcements = self._fetch_announcements(stock_code, start_date, end_date)
        eastmoney_news = self._fetch_eastmoney_news(stock_code)

        return {
            "stock_code": stock_code,
            "period": f"{start_date}-{end_date}",
            "announcements": announcements,
            "market_news": eastmoney_news,
        }

    def _fetch_announcements(self, stock_code: str, start_date: str, end_date: str) -> list[dict]:
        """从 tushare 获取公司公告"""
        try:
            df = self._pro.anns_d(
                ts_code=stock_code,
                start_date=start_date,
                end_date=end_date,
            )
            if df is None or df.empty:
                return []
            results = []
            for _, row in df.iterrows():
                title = row.get("title", "")
                # 过滤掉中介机构的冗长公告标题，保留核心公告
                if any(skip in title for skip in ["律师事务所", "会计师事务所", "核查意见"]):
                    continue
                results.append({
                    "date": row.get("ann_date", ""),
                    "title": title,
                    "source": "公司公告",
                })
            return results[:15]
        except Exception as e:
            logger.warning("tushare anns_d 调用失败: %s", e)
            return []

    def _fetch_eastmoney_news(self, stock_code: str) -> list[dict]:
        """从东方财富获取个股相关快讯"""
        import json
        import ssl
        import urllib.request

        # 从 ts_code 提取纯数字代码
        code = stock_code.split(".")[0]

        # 东财公告 API
        url = (
            f"https://np-anotice-stock.eastmoney.com/api/security/ann?"
            f"sr=-1&page_size=10&page_index=1&ann_type=A&client_source=web"
            f"&stock_list={code}&f_node=0&s_node=0"
        )

        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE

        results = []
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=10, context=ctx) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            items = data.get("data", {}).get("list", []) if data.get("data") else []
            for item in items[:10]:
                title = item.get("title", "")
                # 过滤中介机构公告
                if any(skip in title for skip in ["律师事务所", "会计师事务所", "核查意见"]):
                    continue
                date = (item.get("notice_date") or "")[:10].replace("-", "")
                results.append({
                    "date": date,
                    "title": title,
                    "source": "东财公告",
                })
        except Exception as e:
            logger.warning("东财公告 API 调用失败: %s", e)

        return results[:10]

    def get_market_signals(self, stock_code: str, days: int = 5) -> dict[str, Any]:
        """获取个股近期市场异动信号（涨跌停 + 龙虎榜）"""
        from datetime import datetime, timedelta

        end_date = datetime.now().strftime("%Y%m%d")
        start_date = (datetime.now() - timedelta(days=days + 5)).strftime("%Y%m%d")

        limit_events = self._fetch_limit_events(stock_code, start_date, end_date)
        toplist_events = self._fetch_toplist_events(stock_code, start_date, end_date)

        return {
            "stock_code": stock_code,
            "period": f"{start_date}-{end_date}",
            "limit_events": limit_events,
            "toplist_events": toplist_events,
            "has_signals": bool(limit_events or toplist_events),
        }

    def _fetch_limit_events(self, stock_code: str, start_date: str, end_date: str) -> list[dict]:
        """涨跌停记录"""
        try:
            # 逐日查询，因为 limit_list_d 只支持按 trade_date 查
            from datetime import datetime, timedelta

            start = datetime.strptime(start_date, "%Y%m%d")
            end = datetime.strptime(end_date, "%Y%m%d")
            results = []
            d = end
            while d >= start and len(results) < 5:
                try:
                    df = self._pro.limit_list_d(trade_date=d.strftime("%Y%m%d"))
                    if df is not None and not df.empty:
                        matched = df[df["ts_code"] == stock_code]
                        for _, row in matched.iterrows():
                            results.append({
                                "date": row.get("trade_date", ""),
                                "close": row.get("close"),
                                "pct_chg": row.get("pct_chg"),
                                "limit_type": "涨停" if row.get("limit") == "U" else "跌停",
                                "open_times": row.get("open_times"),
                                "first_time": row.get("first_time"),
                            })
                except Exception:
                    pass
                d -= timedelta(days=1)
            return results
        except Exception as e:
            logger.warning("limit_list_d 调用失败: %s", e)
            return []

    def _fetch_toplist_events(self, stock_code: str, start_date: str, end_date: str) -> list[dict]:
        """龙虎榜记录"""
        try:
            from datetime import datetime, timedelta

            start = datetime.strptime(start_date, "%Y%m%d")
            end = datetime.strptime(end_date, "%Y%m%d")
            results = []
            d = end
            while d >= start and len(results) < 5:
                try:
                    df = self._pro.top_list(trade_date=d.strftime("%Y%m%d"))
                    if df is not None and not df.empty:
                        matched = df[df["ts_code"] == stock_code]
                        for _, row in matched.iterrows():
                            results.append({
                                "date": row.get("trade_date", ""),
                                "close": row.get("close"),
                                "pct_change": row.get("pct_change"),
                                "net_amount": row.get("net_amount"),
                                "buy_amount": row.get("l_buy"),
                                "sell_amount": row.get("l_sell"),
                                "reason": row.get("reason", ""),
                            })
                except Exception:
                    pass
                d -= timedelta(days=1)
            return results
        except Exception as e:
            logger.warning("top_list 调用失败: %s", e)
            return []
