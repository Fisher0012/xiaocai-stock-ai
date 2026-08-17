"""工具函数"""

import os

from ._common.logging import get_logger

from .data_sources.base import StockDataSource

logger = get_logger(__name__)


def get_data_source() -> StockDataSource:
    """根据环境变量获取数据源实例

    优先级：
    1. FINMCP_DATA_SOURCE 环境变量指定
    2. 有 TUSHARE_TOKEN 则用 tushare
    3. 默认 akshare
    """
    source_name = os.getenv("FINMCP_DATA_SOURCE", "auto")
    tushare_token = os.getenv("TUSHARE_TOKEN", "")

    if source_name == "tushare" or (source_name == "auto" and tushare_token):
        from .data_sources.tushare_src import TushareSource
        logger.info("使用数据源: tushare")
        return TushareSource(token=tushare_token)

    if source_name in ("akshare", "auto"):
        from .data_sources.akshare_src import AkshareSource
        logger.info("使用数据源: akshare")
        return AkshareSource()

    logger.warning("未知数据源 '%s'，回退到 akshare", source_name)
    from .data_sources.akshare_src import AkshareSource
    return AkshareSource()
