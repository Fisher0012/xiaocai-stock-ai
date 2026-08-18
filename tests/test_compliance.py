"""compliance 层单元测试: BASE 默认开, STRICT 环境变量触发。"""
import os
import importlib

import core.compliance


def _reload_with_strict(on: bool):
    if on:
        os.environ["XIAOCAI_STRICT_COMPLIANCE"] = "1"
    else:
        os.environ.pop("XIAOCAI_STRICT_COMPLIANCE", None)
    importlib.reload(core.compliance)
    return core.compliance.scrub_compliance


class TestBase:
    """BASE 层永远开: 严禁买入/卖出/目标价, 软化煽动词, 删内部字眼。"""

    def setup_method(self):
        self.scrub = _reload_with_strict(False)

    def test_buy_sell_softened(self):
        out = self.scrub("这只可以买入, 现价卖出")
        assert "买入" not in out
        assert "卖出" not in out
        assert "看好" in out
        assert "看淡" in out

    def test_target_price_rewritten(self):
        out = self.scrub("短期目标价 25 元")
        assert "目标价" not in out
        assert "参考区间" in out

    def test_bull_bear_softened(self):
        out = self.scrub("看涨中际旭创, 看跌宁德")
        assert "看涨" not in out
        assert "看跌" not in out
        assert "偏强" in out
        assert "偏弱" in out

    def test_bull_bear_swap_not_hit(self):
        # 品牌名"看涨跌互换"不能误伤
        out = self.scrub("看涨跌互换合约")
        assert "看涨跌" in out

    def test_extreme_words_softened(self):
        out = self.scrub("中际旭创暴涨 8%, 宁德大跌")
        assert "暴涨" not in out
        assert "大跌" not in out
        assert "上涨" in out
        assert "下跌" in out

    def test_internal_leak_removed(self):
        # 句号级删除: 命中句删掉, 其他保留
        out = self.scrub("BIAS 是 12。调用 get_stock_news 失败。技术面偏强。")
        assert "get_stock_news" not in out
        assert "调用" not in out
        assert "BIAS 是 12" in out
        assert "技术面偏强" in out


class TestStrict:
    """STRICT 层: 金融小程序/公众号场景, 删代码+涨跌幅。"""

    def setup_method(self):
        self.scrub = _reload_with_strict(True)

    def teardown_method(self):
        _reload_with_strict(False)

    def test_code_removed(self):
        out = self.scrub("中际旭创(300308.SZ) 值得关注")
        assert "300308.SZ" not in out

    def test_signed_pct_removed(self):
        out = self.scrub("中际旭创 +3.2% 领涨")
        assert "3.2%" not in out

    def test_dir_pct_softened(self):
        out = self.scrub("宁德时代上涨超8%")
        assert "8%" not in out
        assert "上涨" in out

    def test_price_and_roe_preserved(self):
        # 现价(元)/无向 % 保留
        out = self.scrub("股价 25.3 元, ROE 15%, 毛利率 40%")
        assert "25.3 元" in out
        assert "ROE 15%" in out
        assert "40%" in out
