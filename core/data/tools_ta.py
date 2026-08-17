"""技术指标计算层 (SPEC §4.2)

入口 get_technical_analysis(stock_code): tushare 日线(qfq) + 盘中实时价合成当日 bar,
本地 pandas 计算全部指标后返回结构化 JSON。LLM 只解读, 不计算——数据准确的硬保障。
指标覆盖: MA/排列/金叉死叉、MACD(含背离)、KDJ、RSI、BIAS、BOLL、量比/量价背离、
60/250日位置分位、支撑压力位、形态信号(突破/缺口/连阳阴/涨停次数)。
"""

import datetime as _dt
import os

import pandas as pd


def _ensure_env():
    os.environ.setdefault("FINMCP_DATA_SOURCE", "tushare")
    if not os.environ.get("TUSHARE_TOKEN"):
        try:
            import tushare as ts
            token = ts.pro_api()._DataApi__token
            if token:
                os.environ["TUSHARE_TOKEN"] = token
        except Exception:
            pass


def _r(v, n=2):
    """round 且容忍 None/NaN"""
    try:
        if v is None or (isinstance(v, float) and (v != v)):
            return None
        return round(float(v), n)
    except (TypeError, ValueError):
        return None


# ── 数据装配 ─────────────────────────────────────────────────

def _load_daily(stock_code: str) -> pd.DataFrame:
    """近550自然日日线(qfq), 时间正序; 盘中用实时行情合成当日 bar。"""
    _ensure_env()
    from finmcp_a_stock_data.tools.price import get_stock_price
    from finmcp_a_stock_data.tools.quote import get_latest_quote

    start = (_dt.date.today() - _dt.timedelta(days=550)).strftime("%Y-%m-%d")
    r = get_stock_price(stock_code, start_date=start, period="daily", adjust="qfq")
    if not r.get("ok") or not r.get("data"):
        raise RuntimeError(f"日线获取失败: {r.get('error', '空数据')}")
    df = pd.DataFrame(r["data"]).sort_values("date").reset_index(drop=True)

    q = get_latest_quote(stock_code)
    if q.get("ok"):
        d = q["data"]
        today = _dt.date.today().strftime("%Y-%m-%d")
        # 日线未含当日(盘中/收盘后未更新)时, 用实时行情补当日 bar
        if (str(df["date"].iloc[-1]) < today and d.get("current_price")
                and d.get("open") and d.get("high") and d.get("low")):
            prev_close = d.get("prev_close") or df["close"].iloc[-1]
            df = pd.concat([df, pd.DataFrame([{
                "date": today, "open": d["open"], "high": d["high"], "low": d["low"],
                "close": d["current_price"], "volume": d.get("volume"),
                "amount": d.get("amount"),
                "pct_change": _r((d["current_price"] - prev_close) / prev_close * 100),
            }])], ignore_index=True)
            df.attrs["intraday_bar"] = True
        df.attrs["realtime_quote"] = d
    return df


# ── 指标计算(纯函数, 可用合成数据单测) ─────────────────────────

def _limit_up_threshold(stock_code: str, name: str = "") -> float:
    if "ST" in (name or "").upper():
        return 4.8    # ST 股 5%
    code = stock_code.split(".")[0]
    if code.startswith(("30", "68")):
        return 19.8   # 创业板/科创板 20cm
    if code.startswith(("4", "8", "9")) and not code.startswith(("60", "68")):
        return 29.8   # 北交所 30cm
    return 9.8


def compute_indicators(df: pd.DataFrame, stock_code: str = "", name: str = "") -> dict:
    """df 需含时间正序的 date/open/high/low/close/volume 列。"""
    c, h, l, v = df["close"], df["high"], df["low"], df["volume"]
    o = df["open"]
    n = len(df)
    if n < 30:
        raise ValueError(f"日线数据不足30根({n}), 无法计算指标")
    if "pct_change" in df.columns:
        pct = pd.to_numeric(df["pct_change"], errors="coerce")
    else:
        pct = c.pct_change() * 100
    out = {}

    # 均线系统
    ma = {p: (c.rolling(p).mean() if n >= p else None) for p in (5, 10, 20, 60, 120, 250)}
    mav = {p: _r(s.iloc[-1]) for p, s in ma.items() if s is not None}
    out["ma"] = {f"ma{p}": val for p, val in mav.items()}
    price = float(c.iloc[-1])
    ordered = [mav.get(p) for p in (5, 10, 20, 60) if mav.get(p) is not None]
    if len(ordered) == 4:
        out["ma_alignment"] = ("多头排列" if ordered == sorted(ordered, reverse=True)
                               else "空头排列" if ordered == sorted(ordered) else "均线交织")
    out["price_vs_ma"] = {f"ma{p}": _r((price - mv) / mv * 100)
                          for p, mv in mav.items() if mv}
    # MA5/MA20 金叉死叉(近3根)
    if ma[5] is not None and ma[20] is not None:
        diff = ma[5] - ma[20]
        cross = None
        for i in range(max(1, n - 3), n):
            a, b = diff.iloc[i - 1], diff.iloc[i]
            if pd.notna(a) and pd.notna(b):
                if a <= 0 < b:
                    cross = f"MA5金叉MA20({df['date'].iloc[i]})"
                elif a >= 0 > b:
                    cross = f"MA5死叉MA20({df['date'].iloc[i]})"
        out["ma_cross_recent"] = cross

    # BIAS
    out["bias"] = {}
    for p in (6, 12, 20):
        if n >= p:
            m = c.rolling(p).mean().iloc[-1]
            out["bias"][f"bias{p}"] = _r((price - m) / m * 100)

    # MACD
    ema12 = c.ewm(span=12, adjust=False).mean()
    ema26 = c.ewm(span=26, adjust=False).mean()
    dif = ema12 - ema26
    dea = dif.ewm(span=9, adjust=False).mean()
    hist = 2 * (dif - dea)
    macd_cross = None
    bar = dif - dea
    for i in range(max(1, n - 3), n):
        if bar.iloc[i - 1] <= 0 < bar.iloc[i]:
            macd_cross = f"MACD金叉({df['date'].iloc[i]})"
        elif bar.iloc[i - 1] >= 0 > bar.iloc[i]:
            macd_cross = f"MACD死叉({df['date'].iloc[i]})"
    divergence = None
    if n >= 60:  # 简化背离判定: 近5日创60日价格新高/低但 DIF 未同步
        if c.iloc[-5:].max() >= c.iloc[-60:].max() and dif.iloc[-5:].max() < dif.iloc[-60:-5].max():
            divergence = "顶背离迹象(价格新高但MACD动能未跟上)"
        elif c.iloc[-5:].min() <= c.iloc[-60:].min() and dif.iloc[-5:].min() > dif.iloc[-60:-5].min():
            divergence = "底背离迹象(价格新低但MACD动能未创新低)"
    out["macd"] = {"dif": _r(dif.iloc[-1], 3), "dea": _r(dea.iloc[-1], 3),
                   "hist": _r(hist.iloc[-1], 3), "cross_recent": macd_cross,
                   "divergence": divergence,
                   "above_zero": bool(dif.iloc[-1] > 0)}

    # KDJ(9,3,3)
    if n >= 9:
        low9 = l.rolling(9).min()
        high9 = h.rolling(9).max()
        rsv = ((c - low9) / (high9 - low9).replace(0, float("nan")) * 100).fillna(50)
        k = rsv.ewm(com=2, adjust=False).mean()
        d = k.ewm(com=2, adjust=False).mean()
        j = 3 * k - 2 * d
        out["kdj"] = {"k": _r(k.iloc[-1]), "d": _r(d.iloc[-1]), "j": _r(j.iloc[-1])}

    # RSI (Wilder)
    delta = c.diff()
    out["rsi"] = {}
    for p in (6, 12, 24):
        if n >= p + 1:
            gain = delta.clip(lower=0).ewm(alpha=1 / p, adjust=False).mean()
            loss = (-delta).clip(lower=0).ewm(alpha=1 / p, adjust=False).mean()
            g, ls = gain.iloc[-1], loss.iloc[-1]
            out["rsi"][f"rsi{p}"] = 100.0 if ls == 0 else _r(100 - 100 / (1 + g / ls))

    # BOLL(20,2)
    if n >= 20:
        mid = c.rolling(20).mean()
        std = c.rolling(20).std()
        upper, lower = mid + 2 * std, mid - 2 * std
        band = float(upper.iloc[-1] - lower.iloc[-1])
        pos = _r((price - lower.iloc[-1]) / band * 100) if band > 0 else 50.0
        widening = None
        if n >= 25 and mid.iloc[-6] == mid.iloc[-6]:
            bw_now = band / mid.iloc[-1]
            bw_prev = float(upper.iloc[-6] - lower.iloc[-6]) / mid.iloc[-6]
            widening = "开口扩大" if bw_now > bw_prev * 1.1 else "开口收窄" if bw_now < bw_prev * 0.9 else "开口平稳"
        out["boll"] = {"upper": _r(upper.iloc[-1]), "mid": _r(mid.iloc[-1]),
                       "lower": _r(lower.iloc[-1]), "position_pct": pos, "bandwidth": widening}

    # 量能
    vol_ok = v.notna().tail(6).all()
    if vol_ok and n >= 6:
        v5 = v.iloc[-6:-1].mean()
        ratio = _r(float(v.iloc[-1]) / v5) if v5 else None
        out["volume"] = {
            "volume_ratio_5d": ratio,  # 量比(对5日均量)
            "level": (None if ratio is None else
                      "显著放量" if ratio >= 2 else "温和放量" if ratio >= 1.3
                      else "缩量" if ratio <= 0.7 else "平量"),
        }
        # 量价背离(近3日)
        c3, v3 = c.iloc[-3:].tolist(), v.iloc[-3:].tolist()
        if c3[2] > c3[1] > c3[0] and v3[2] < v3[1] < v3[0]:
            out["volume"]["price_volume_divergence"] = "价涨量缩(上攻动能减弱)"
        elif c3[2] < c3[1] < c3[0] and v3[2] > v3[1] > v3[0]:
            out["volume"]["price_volume_divergence"] = "价跌量增(出货嫌疑)"

    # 位置分位
    out["position"] = {}
    for p, key in ((60, "pct_in_60d_range"), (250, "pct_in_250d_range")):
        if n >= p:
            lo, hi = float(l.iloc[-p:].min()), float(h.iloc[-p:].max())
            if hi > lo:
                out["position"][key] = _r((price - lo) / (hi - lo) * 100, 1)

    # 支撑压力(静态高低点 + 动态均线)
    def _lvl(val, label):
        return {"level": _r(val), "label": label}
    supports, resistances = [], []
    for p in (10, 20, 60):
        if n >= p:
            lo, hi = float(l.iloc[-p:].min()), float(h.iloc[-p:].max())
            if lo < price:
                supports.append(_lvl(lo, f"近{p}日低点"))
            if hi > price:
                resistances.append(_lvl(hi, f"近{p}日高点"))
    for p in (20, 60):
        mv = mav.get(p)
        if mv and mv < price:
            supports.append(_lvl(mv, f"MA{p}"))
    supports.sort(key=lambda x: -x["level"])
    resistances.sort(key=lambda x: x["level"])
    out["support_levels"] = supports[:3]
    out["resistance_levels"] = resistances[:3]

    # 形态信号
    signals = []
    if n >= 21:
        if price > float(c.iloc[-21:-1].max()):
            signals.append("突破20日新高")
        elif price < float(c.iloc[-21:-1].min()):
            signals.append("跌破20日新低")
    for i in range(max(1, n - 5), n):  # 近5日缺口
        if float(l.iloc[i]) > float(h.iloc[i - 1]):
            signals.append(f"向上跳空缺口({df['date'].iloc[i]}, {_r(h.iloc[i-1])}-{_r(l.iloc[i])})")
        elif float(h.iloc[i]) < float(l.iloc[i - 1]):
            signals.append(f"向下跳空缺口({df['date'].iloc[i]}, {_r(h.iloc[i])}-{_r(l.iloc[i-1])})")
    streak = 0  # 连阳/连阴
    for i in range(n - 1, -1, -1):
        up = float(c.iloc[i]) >= float(o.iloc[i])
        if streak == 0:
            streak = 1 if up else -1
        elif (streak > 0) == up:
            streak += 1 if up else -1
        else:
            break
    if abs(streak) >= 3:
        signals.append(f"{'连阳' if streak > 0 else '连阴'}{abs(streak)}根")
    thr = _limit_up_threshold(stock_code, name)
    limit_ups = int((pct.iloc[-20:] >= thr).sum()) if n >= 20 else 0
    if limit_ups:
        signals.append(f"近20日涨停{limit_ups}次")
    out["pattern_signals"] = signals
    out["limit_up_count_20d"] = limit_ups

    out["price"] = _r(price)
    out["pct_change_today"] = _r(pct.iloc[-1])
    return out


# ── 对外工具入口 ─────────────────────────────────────────────

def get_technical_analysis(stock_code: str) -> dict:
    """个股技术面全景(供 LLM 解读)。数据: tushare 日线 + 盘中实时合成。"""
    try:
        df = _load_daily(stock_code)
        q = df.attrs.get("realtime_quote") or {}
        result = compute_indicators(df, stock_code, name=str(q.get("name") or ""))
        if "ST" in str(q.get("name") or "").upper():
            result["st_warning"] = "ST股: 5%涨跌停限制, 有退市风险, 回答时必须显式警示"
        result["as_of"] = {
            "last_bar_date": str(df["date"].iloc[-1]),
            "intraday_bar": bool(df.attrs.get("intraday_bar")),
            "quote_time": f"{q.get('date', '')} {q.get('time', '')}".strip() or None,
        }
        result["note"] = ("最后一根K线为当日盘中实时合成, 收盘前数值仍在变动"
                         if df.attrs.get("intraday_bar") else "基于最新收盘数据")
        return {"ok": True, "data": result, "source": "tushare_daily + sina_realtime, 指标本地计算"}
    except Exception as e:
        return {"ok": False, "error": {"message": f"技术分析失败: {str(e)[:200]}"}}
