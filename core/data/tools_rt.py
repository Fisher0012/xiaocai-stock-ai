"""东财盘中实时数据层 (SPEC §4.1)

四个能力: 个股实时资金流 / 分时均价线 / 大盘快照(含涨跌家数) / 板块资金排行。
全部走东财公开行情接口, 直连不走代理; push2 被风控时用 push2delay 兜底。
金额统一转亿元(保留3位), 百分比保持原始百分数值。
"""

import json
import time
import urllib.request as _u
from urllib.error import URLError

_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36",
    "Referer": "https://quote.eastmoney.com/",
    "Accept": "application/json, text/plain, */*",
}
# push2(实时)与 push2his(历史/分时)均有 push2delay 等价兜底(延迟约1-2分钟, 可接受)
_HOST_FALLBACK = {
    "push2.eastmoney.com": ["push2.eastmoney.com", "push2delay.eastmoney.com"],
    "push2his.eastmoney.com": ["push2his.eastmoney.com", "push2delay.eastmoney.com"],
}
_opener = _u.build_opener(_u.ProxyHandler({}))  # 强制直连, 忽略系统代理


def _get_json(url: str, tries_per_host: int = 2) -> dict:
    host = url.split("/")[2]
    last = None
    last_empty = None  # 风控偶发返回 data=null, 视为失败重试; 全部为空时兜底返回最后一次
    for h in _HOST_FALLBACK.get(host, [host]):
        u2 = url.replace(host, h, 1)
        for _ in range(tries_per_host):
            try:
                raw = _opener.open(_u.Request(u2, headers=_HEADERS), timeout=12).read()
                j = json.loads(raw.decode("utf-8", "replace"))
                if j.get("data"):
                    return j
                last_empty = j
            except (URLError, OSError, json.JSONDecodeError, Exception) as e:
                last = e
            time.sleep(0.6)
    if last_empty is not None:
        return last_empty
    raise RuntimeError(f"东财接口不可达: {url.split('?')[0]} ({last})")


def _secid(stock_code: str) -> str:
    """601958 / 601958.SH / 000001.SZ → 东财 secid (沪=1. 深京=0.)"""
    code = stock_code.split(".")[0].strip()
    if not (len(code) == 6 and code.isdigit()):
        raise ValueError(f"无效股票代码: {stock_code}")
    market = "1" if code[0] in ("5", "6", "9") else "0"
    return f"{market}.{code}"


def _yi(v) -> float | None:
    """元 → 亿元"""
    if not isinstance(v, (int, float)):
        return None
    return round(v / 1e8, 3)


def _num(v):
    return v if isinstance(v, (int, float)) else None


def _err(msg: str) -> dict:
    return {"ok": False, "error": {"message": msg}}


# ── 1. 个股实时资金流 ──────────────────────────────────────────

def get_realtime_moneyflow(stock_code: str, days: int = 10) -> dict:
    """个股资金流: 当日盘中实时(主力/超大单/大单/中单/小单净额与占比)
    + 近 N 日主力净流入序列(含当日, 复刻"5日资金持续吸筹今天在加速"证据链)。
    """
    try:
        sid = _secid(stock_code)
    except ValueError as e:
        return _err(str(e))
    try:
        # 当日盘中实时
        j = _get_json(
            "https://push2.eastmoney.com/api/qt/ulist.np/get?fltt=2"
            f"&secids={sid}"
            "&fields=f2,f3,f9,f12,f14,f18,f23,f62,f66,f69,f72,f75,f78,f81,f84,f87,f100,f114,f115,f124,f184"
        )
        diff = (j.get("data") or {}).get("diff") or []
        if not diff:
            return _err(f"未查到 {stock_code} 的实时资金流")
        d = diff[0]
        today = {
            "name": d.get("f14"),
            "price": _num(d.get("f2")),
            "pct_change": _num(d.get("f3")),
            "prev_close": _num(d.get("f18")),
            "main_net_yi": _yi(d.get("f62")),          # 主力净流入(亿)
            "main_net_pct": _num(d.get("f184")),        # 主力净占比%
            "xlarge_net_yi": _yi(d.get("f66")),         # 超大单净流入(亿)
            "xlarge_net_pct": _num(d.get("f69")),       # 超大单净占比%
            "large_net_yi": _yi(d.get("f72")),
            "large_net_pct": _num(d.get("f75")),
            "medium_net_yi": _yi(d.get("f78")),
            "medium_net_pct": _num(d.get("f81")),
            "small_net_yi": _yi(d.get("f84")),
            "small_net_pct": _num(d.get("f87")),
            # 三口径市盈率(东财实时): 动态=当年业绩年化, TTM=滚动四季, 静态=上年年报
            "pe_dynamic": _num(d.get("f9")),
            "pe_ttm": _num(d.get("f115")),
            "pe_static": _num(d.get("f114")),
            "pb": _num(d.get("f23")),
            "industry_board": d.get("f100"),  # 所属行业板块(与大盘档位的风口板块对照)
            "quote_time": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(d["f124"]))
            if isinstance(d.get("f124"), (int, float)) else None,
        }
        # 历史日度序列: 东财 daykline 优先(含占比), 被风控/为空时降级 tushare EOD
        series = _history_series_em(sid, days)
        source = "eastmoney_realtime"
        # 盘中东财 daykline 常只返回当日 1 条(2026-08-12 实测), 会丢失近 N 日趋势;
        # 序列过短(<3)即回退 tushare EOD 拿完整历史, 当日实时值仍由下方 append 补上
        if len(series) < 3:
            series = _history_series_tushare(stock_code, days)
            source = "eastmoney_realtime(当日) + tushare_eod(历史)"
        today_date = time.strftime("%Y-%m-%d")
        # daykline 未含当日时, 用实时值补当日行
        if today["main_net_yi"] is not None and (not series or series[-1]["date"] != today_date):
            series.append({
                "date": today_date,
                "main_net_yi": today["main_net_yi"],
                "main_net_pct": today["main_net_pct"],
                "xlarge_net_yi": today["xlarge_net_yi"],
                "xlarge_net_pct": today["xlarge_net_pct"],
                "large_net_yi": today["large_net_yi"],
                "close": today["price"],
                "pct_change": today["pct_change"],
                "intraday": True,
            })
        series = series[-days:]
        # 派生: 连续净流入/流出天数(含当日)
        streak = 0
        for s in reversed(series):
            v = s["main_net_yi"] or 0
            if streak == 0:
                streak = 1 if v > 0 else -1 if v < 0 else 0
            elif (streak > 0 and v > 0) or (streak < 0 and v < 0):
                streak += 1 if streak > 0 else -1
            else:
                break
        return {"ok": True, "data": {
            "stock_code": stock_code,
            "today_realtime": today,
            "daily_series": series,
            "main_inflow_streak_days": streak,  # 正=连续吸筹天数, 负=连续流出天数
            "note": "金额单位亿元; intraday=true 表示当日盘中值仍在变动",
        }, "source": source}
    except Exception as e:
        return _err(f"资金流获取失败: {e}")


def _history_series_em(sid: str, days: int) -> list[dict]:
    """东财 fflow daykline 历史序列 (fields2 顺序: 日期,主力,小单,中单,大单,超大单,
    主力%,小单%,中单%,大单%,超大单%,收盘,涨跌幅,...)。被风控时返回空列表。"""
    try:
        j = _get_json(
            "https://push2his.eastmoney.com/api/qt/stock/fflow/daykline/get"
            f"?lmt={days}&klt=101&secid={sid}"
            "&fields1=f1,f2,f3,f7"
            "&fields2=f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61,f62,f63,f64,f65"
        )
    except Exception:
        return []
    today_date = time.strftime("%Y-%m-%d")
    series = []
    for row in ((j.get("data") or {}).get("klines") or []):
        p = row.split(",")
        if len(p) < 13:
            continue
        series.append({
            "date": p[0],
            "main_net_yi": _yi(float(p[1])),
            "main_net_pct": round(float(p[6]), 2),
            "xlarge_net_yi": _yi(float(p[5])),
            "xlarge_net_pct": round(float(p[10]), 2),
            "large_net_yi": _yi(float(p[4])),
            "close": float(p[11]),
            "pct_change": float(p[12]),
            "intraday": p[0] == today_date,
        })
    return series


def _history_series_tushare(stock_code: str, days: int) -> list[dict]:
    """tushare moneyflow 兜底 (EOD, 万元)。主力=大单+超大单买卖净额, 无占比字段。"""
    try:
        import tushare as ts
        code = stock_code.split(".")[0]
        ts_code = f"{code}.{'SH' if code[0] in ('5', '6', '9') else 'SZ'}"
        df = ts.pro_api().moneyflow(ts_code=ts_code, limit=days)
        if df is None or df.empty:
            return []
        series = []
        for _, r in df.iterrows():
            lg = float(r.get("buy_lg_amount") or 0) - float(r.get("sell_lg_amount") or 0)
            elg = float(r.get("buy_elg_amount") or 0) - float(r.get("sell_elg_amount") or 0)
            d = str(r.get("trade_date", ""))
            series.append({
                "date": f"{d[:4]}-{d[4:6]}-{d[6:]}" if len(d) == 8 else d,
                "main_net_yi": round((lg + elg) / 10000, 3),
                "main_net_pct": None,
                "xlarge_net_yi": round(elg / 10000, 3),
                "xlarge_net_pct": None,
                "large_net_yi": round(lg / 10000, 3),
                "close": None,
                "pct_change": None,
                "intraday": False,
            })
        series.reverse()  # tushare 按日期倒序返回, 转为时间正序
        return series
    except Exception:
        return []


# ── 2. 分时均价线 ─────────────────────────────────────────────

def get_intraday_trend(stock_code: str) -> dict:
    """当日分时: 现价与分时均价线(黄线)关系、日内位置、近30分钟方向。
    复刻"等分时回踩均价线不破再小仓位试探"的盘口判断。
    """
    try:
        sid = _secid(stock_code)
    except ValueError as e:
        return _err(str(e))
    try:
        j = _get_json(
            "https://push2his.eastmoney.com/api/qt/stock/trends2/get"
            f"?secid={sid}&fields1=f1,f2,f3,f8&fields2=f51,f53,f56,f58&iscr=0&ndays=1"
        )
        data = j.get("data") or {}
        bars = []
        for row in (data.get("trends") or []):
            p = row.split(",")
            if len(p) >= 4:
                bars.append({"time": p[0], "price": float(p[1]), "vol": float(p[2]), "avg": float(p[3])})
        if not bars:
            return _err(f"未查到 {stock_code} 的分时数据(可能未开盘)")
        last = bars[-1]
        prices = [b["price"] for b in bars]
        day_high, day_low = max(prices), min(prices)
        gap_pct = round((last["price"] - last["avg"]) / last["avg"] * 100, 2) if last["avg"] else None
        rng = day_high - day_low
        pos = round((last["price"] - day_low) / rng * 100, 1) if rng > 0 else 50.0
        recent = prices[-30:]
        slope_pct = round((recent[-1] - recent[0]) / recent[0] * 100, 2) if len(recent) >= 2 else 0.0
        return {"ok": True, "data": {
            "stock_code": stock_code,
            "time": last["time"],
            "price": last["price"],
            "avg_price_line": last["avg"],                 # 分时均价线(黄线)
            "price_vs_avg_pct": gap_pct,                   # 现价相对均价线%(正=线上方)
            "above_avg_line": last["price"] >= last["avg"],
            "day_open": bars[0]["price"],
            "day_high": day_high,
            "day_low": day_low,
            "position_in_day_range_pct": pos,              # 现价在日内区间的位置%
            "last_30min_change_pct": slope_pct,            # 近30分钟涨跌%
            "bars_count": len(bars),
        }, "source": "eastmoney_realtime"}
    except Exception as e:
        return _err(f"分时数据获取失败: {e}")


# ── 3. 大盘实时快照 ───────────────────────────────────────────

_INDEX_SECIDS = "1.000001,0.399001,0.399006,1.000300,0.399106"
_INDEX_NAMES = {"000001": "上证指数", "399001": "深证成指", "399006": "创业板指",
                "000300": "沪深300", "399106": "深证综指"}


def get_market_snapshot() -> dict:
    """大盘实时: 四大指数涨跌 + 全市场涨跌家数 + 两市成交额。
    涨跌家数=上证(沪市)+深证综指(深市); 成交额同口径。
    """
    try:
        j = _get_json(
            "https://push2.eastmoney.com/api/qt/ulist.np/get?fltt=2"
            f"&secids={_INDEX_SECIDS}&fields=f2,f3,f6,f12,f14,f104,f105,f106,f124"
        )
        diff = (j.get("data") or {}).get("diff") or []
        if not diff:
            return _err("未获取到指数行情")
        idx = {}
        for d in diff:
            code = str(d.get("f12"))
            idx[code] = {
                "name": _INDEX_NAMES.get(code, d.get("f14")),
                "point": _num(d.get("f2")),
                "pct_change": _num(d.get("f3")),
                "amount_yi": _yi(d.get("f6")),
                "up_count": _num(d.get("f104")),
                "down_count": _num(d.get("f105")),
                "flat_count": _num(d.get("f106")),
            }
        sh, szz = idx.get("000001", {}), idx.get("399106", {})
        up = (sh.get("up_count") or 0) + (szz.get("up_count") or 0)
        down = (sh.get("down_count") or 0) + (szz.get("down_count") or 0)
        flat = (sh.get("flat_count") or 0) + (szz.get("flat_count") or 0)
        amount = round((sh.get("amount_yi") or 0) + (szz.get("amount_yi") or 0), 1)
        ts = next((d.get("f124") for d in diff if isinstance(d.get("f124"), (int, float))), None)
        return {"ok": True, "data": {
            "indices": [idx[c] for c in ("000001", "399001", "399006", "000300") if c in idx],
            "market_breadth": {"up": up, "down": down, "flat": flat},
            "total_amount_yi": amount,   # 两市成交额(亿)
            "quote_time": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(ts)) if ts else None,
        }, "source": "eastmoney_realtime"}
    except Exception as e:
        return _err(f"大盘快照获取失败: {e}")


# ── 4. 板块资金排行 ───────────────────────────────────────────

def _fetch_boards(board_type: str) -> list[dict]:
    t = {"industry": "2", "concept": "3"}[board_type]
    j = _get_json(
        "https://push2.eastmoney.com/api/qt/clist/get?pn=1&pz=500&po=1&np=1"
        f"&fltt=2&invt=2&fid=f62&fs=m:90+t:{t}&fields=f3,f12,f14,f62,f184"
    )
    rows = []
    for d in ((j.get("data") or {}).get("diff") or []):
        # 2026-08-20 医药事故: 盘前竞价时段 f62(主力净额)全为"-", 原来整行丢弃导致
        # 板块清单为空 → 板块名模糊解析必挂。改为保留行(资金字段置 None), 名字解析
        # 不依赖资金数据; 榜单排序侧自行过滤 None。
        if not d.get("f14"):
            continue
        rows.append({
            "board": d.get("f14"),
            "bk": str(d.get("f12", "")),   # 板块 BK 代码, 供 _sector_bk_code 模糊 fallback
            "pct_change": _num(d.get("f3")),
            "main_net_yi": _yi(d.get("f62")) if isinstance(d.get("f62"), (int, float)) else None,
            "main_net_pct": _num(d.get("f184")),
        })
    return rows


def get_sector_moneyflow_rank(top_n: int = 10, board_type: str = "industry",
                              board_names: str = "") -> dict:
    """当日板块主力资金排行(流入榜+流出榜)。board_type: industry(行业)/concept(概念)。
    board_names: 逗号分隔的板块名点查(如 "银行,电力,贵金属"), 跨行业+概念模糊匹配,
    返回这些板块的当日涨跌+资金——用于避险/防御类问题核对具体板块表现。
    """
    if board_type not in ("industry", "concept"):
        return _err("board_type 仅支持 industry / concept")
    top_n = max(1, min(int(top_n), 30))
    try:
        if board_names:
            queries = [q.strip() for q in str(board_names).replace("，", ",").split(",") if q.strip()]
            all_rows = _fetch_boards("industry") + _fetch_boards("concept")
            matched, seen = [], set()
            for q in queries:
                hits = [r for r in all_rows if q in (r["board"] or "")]
                if not hits:
                    matched.append({"board": q, "note": "未找到同名板块"})
                    continue
                for r in sorted(hits, key=lambda x: abs(x["main_net_yi"] or 0), reverse=True)[:3]:
                    if r["board"] not in seen:
                        seen.add(r["board"])
                        matched.append(r)
            return {"ok": True, "data": {
                "queried": queries, "boards": matched,
                "note": "金额单位亿元, 当日盘中实时",
            }, "source": "eastmoney_realtime"}
        rows = _fetch_boards(board_type)
        # 资金榜只用有资金数据的行(盘前竞价时段 f62 全空 → funded 为空, 如实返回空榜,
        # 由引擎层给"盘前资金流未生成"的诚实文案, 不再混入 None 排序)
        funded = [r for r in rows if r.get("main_net_yi") is not None]
        if not funded:
            return _err("板块资金数据尚未生成(盘前竞价时段主力资金流从 9:30 开盘后才开始累计)"
                        if rows else "未获取到板块资金数据")
        funded.sort(key=lambda r: r["main_net_yi"], reverse=True)
        return {"ok": True, "data": {
            "board_type": board_type,
            "top_inflow": funded[:top_n],
            "top_outflow": funded[-top_n:][::-1],
            "note": "金额单位亿元, 当日盘中实时",
        }, "source": "eastmoney_realtime"}
    except Exception as e:
        return _err(f"板块资金排行获取失败: {e}")


# ── 5. 涨停池/连板数据(妖股·打板框架数据源, 2026-08-13) ─────────

def get_limit_up_pool(stock_code: str = "") -> dict:
    """当日涨停池: 全市场情绪概览(涨停家数/最高连板/连板分布) + 连板梯队前列。
    传 stock_code 时额外返回该股在池状态(连板数/封单/炸板/首封时间)。
    数据源: 东财涨停池(盘中实时)。用于连板/妖股类问题的打板框架分析。
    """
    try:
        d = time.strftime("%Y%m%d")
        j = _get_json(
            "https://push2ex.eastmoney.com/getTopicZTPool?ut=7eea3edcaed734bea9cbfc24409ed989"
            f"&dpt=wz.ztzt&Pageindex=0&pagesize=300&sort=fbt%3Aasc&date={d}"
        )
        pool = (j.get("data") or {}).get("pool") or []
        if not pool:
            return {"ok": True, "data": {"market": {"limit_up_count": 0},
                    "note": "当前无涨停(可能未开盘或全市场无涨停)"}, "source": "eastmoney_ztpool"}

        def _row(p):
            return {
                "code": str(p.get("c", "")).zfill(6), "name": p.get("n"),
                "streak": p.get("lbc"),                       # 连板数
                "seal_yi": _yi(p.get("fund")),                # 封单额(亿)
                "break_times": p.get("zbc"),                  # 炸板次数
                "turnover_pct": _num(p.get("hs")),            # 换手率%
                "first_seal": f"{str(p.get('fbt')).zfill(6)[:2]}:{str(p.get('fbt')).zfill(6)[2:4]}"
                if p.get("fbt") is not None else None,        # 首次封板时间
                "industry": p.get("hybk"),
            }
        rows = sorted((_row(p) for p in pool), key=lambda x: (x["streak"] or 0), reverse=True)
        dist: dict = {}
        for r in rows:
            dist[r["streak"]] = dist.get(r["streak"], 0) + 1
        out = {
            "market": {
                "limit_up_count": len(rows),
                "max_streak": rows[0]["streak"] if rows else 0,
                "streak_dist": {f"{k}板": v for k, v in sorted(dist.items(), reverse=True)},
                "total_break_times": sum(r["break_times"] or 0 for r in rows),  # 全场炸板次数(情绪温度)
            },
            "top_ladder": rows[:8],   # 连板梯队前列(最高辨识度标的)
            "note": "打板参考: 晋级率随连板高度升(历史1板17%→5板+55%)但次日跌超5%概率同步升到28%, 赔率游戏严守纪律",
        }
        if stock_code:
            code6 = stock_code.split(".")[0]
            hit = next((r for r in rows if r["code"] == code6), None)
            out["queried_stock"] = hit or {"code": code6, "in_pool": False, "note": "该股当前不在涨停池"}
        return {"ok": True, "data": out, "source": "eastmoney_ztpool"}
    except Exception as e:
        return _err(f"涨停池获取失败: {e}")


# ── 6. 板块确定性选票(供板块问答, 不让模型随机挑) ──────────────

_SECTOR_ALIAS = {
    "光模块": "CPO", "光通信": "CPO", "存储芯片": "存储", "算力": "算力概念",
    "AI芯片": "人工智能", "智能驾驶": "无人驾驶", "自动驾驶": "无人驾驶",
    "机器人": "机器人概念", "锂电": "锂电池", "储能概念": "储能",
    # 2026-08-17 Donnie: 用户口语板块名, 东财常查不到, 加模糊别名
    "气体": "工业气体", "气体概念": "工业气体", "封测": "集成电路封测",
    "封装": "先进封装", "存储": "存储芯片", "军品": "军工",
    "创新药械": "创新药", "AI应用": "人工智能",
    # 2026-08-20 医药事故: 大类词 suggest 只回个股不回板块, fuzzy 又依赖网络,
    # 高频大类词直接钉死到东财大类行业板块, 不走不稳定的两级解析
    "医药": "医药生物", "医药股": "医药生物", "医疗": "医药生物",
    "药": "医药生物", "大医药": "医药生物",
    "券商": "证券", "保险股": "保险", "银行股": "银行",
    "地产": "房地产", "白酒股": "白酒", "军工股": "军工",
}
_sector_code_cache: dict = {}


def _sector_bk_code(name: str):
    """板块名 → 东财 BK 代码(带缓存)。用东财 suggest 接口。
    2026-08-17 Donnie: 加模糊匹配 —— 用户口语板块名(如"气体"→"工业气体")东财搜不到时,
    fallback 到全板块列表(_fetch_boards)按子串匹配, 返回最优候选。"""
    import urllib.parse as _up
    name = (name or "").strip()
    # 剥"板块"后缀("医药板块"→"医药"), 东财板块名没有以"板块"结尾的, 剥了才能命中 alias
    if len(name) > 2 and name.endswith("板块"):
        name = name[:-2]
    name = _SECTOR_ALIAS.get(name, name)
    if name in _sector_code_cache:
        return _sector_code_cache[name]
    best = None
    try:
        url = f"https://searchapi.eastmoney.com/api/suggest/get?input={_up.quote(name)}&type=14&count=8"
        raw = _opener.open(_u.Request(url, headers=_HEADERS), timeout=12).read()
        j = json.loads(raw.decode("utf-8", "replace"))
        for it in (j.get("QuotationCodeTable") or {}).get("Data") or []:
            code = str(it.get("Code", ""))
            if code.startswith("BK"):
                if it.get("Name") == name:
                    best = (code, it.get("Name")); break
                if not best:
                    best = (code, it.get("Name"))
    except Exception:
        pass
    # Fallback 模糊匹配: suggest 没结果(如"气体")→ 遍历全板块清单按子串, 选名字最短的
    # (最短通常最贴近母题, "工业气体" > "气体设备与检测")
    if not best:
        try:
            all_boards = _fetch_boards("industry") + _fetch_boards("concept")
            hits = [(r["bk"], r["board"]) for r in all_boards
                    if r.get("board") and r.get("bk") and (name in r["board"] or r["board"] in name)]
            if hits:
                hits.sort(key=lambda x: len(x[1]))
                best = hits[0]
        except Exception:
            pass
    # 2026-08-20 医药事故: 解析失败不缓存(负缓存 bug)——suggest/清单接口一次网络抖动,
    # None 被永久缓存, 该板块名直到进程重启都解析不出。只缓存成功结果。
    if best:
        _sector_code_cache[name] = best
    return best


def get_sector_top_stocks(sector_name: str, top_n: int = 3, sort_by: str = "flow") -> dict:
    """板块成分股取前 N 只。sort_by: flow(当日主力净流入降序)/mv(总市值降序取龙头)。
    返回代码/名/涨跌/主力净额/市值, 供板块问答对这几只再跑个股级完整分析。
    """
    bk = _sector_bk_code(sector_name)
    if not bk:
        return _err(f"未找到板块「{sector_name}」对应代码")
    top_n = max(1, min(int(top_n), 30))
    fid = "f20" if sort_by == "mv" else "f62"
    try:
        j = _get_json(
            f"https://push2.eastmoney.com/api/qt/clist/get?pn=1&pz=60&fs=b:{bk[0]}"
            f"&fltt=2&invt=2&fid={fid}&po=1&fields=f12,f14,f2,f3,f20,f62,f184"
        )
        diff = (j.get("data") or {}).get("diff") or []
        if isinstance(diff, dict):   # 东财 clist 板块成分常返回 dict, 需转 list(否则遍历到 key 字符串)
            diff = list(diff.values())
        rows = []
        for d in diff:
            if not isinstance(d, dict):
                continue
            code6 = str(d.get("f12", ""))
            if not (len(code6) == 6 and code6.isdigit()):
                continue
            rows.append({
                "stock_code": code6,
                "name": d.get("f14"),
                "price": _num(d.get("f2")),
                "pct_change": _num(d.get("f3")),
                "total_mv_yi": _yi(d.get("f20")),
                "main_net_yi": _yi(d.get("f62")),
                "main_net_pct": _num(d.get("f184")),
            })
        if not rows:
            return _err(f"板块「{sector_name}」无成分资金数据")
        return {"ok": True, "data": {
            "sector": bk[1],
            "top_stocks": rows[:top_n],
            "note": "按当日主力净流入降序; 金额亿元",
        }, "source": "eastmoney_realtime"}
    except Exception as e:
        return _err(f"板块选票失败: {e}")
