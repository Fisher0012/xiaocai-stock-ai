"""DeepSeek agentic 引擎 (SPEC §4.4)

多轮 function calling 循环: LLM 按需调用工具(单轮可并行多个), 数据齐了输出裁决式回答。
挂载 routers/finmcp.py 现有 TOOL_REGISTRY + stockbot 新增实时/技术面工具。
CLI 实测: python3 -m stockbot.engine "这只股票怎么样 601958"
"""

import datetime as _dt
import json
import logging
import re
import time
from concurrent.futures import ThreadPoolExecutor, TimeoutError as _FutTimeout

from .compliance import scrub_compliance
from .data import market_regime, tools_rt, tools_ta
from .persona import PERSONA_PROMPT, TOOL_DOCS

logger = logging.getLogger("stockbot.engine")

MODEL = "deepseek-chat"
MAX_ROUNDS = 12          # 工具循环上限
TOOL_TIMEOUT_S = 25      # 单工具硬超时(含排队等待)
RESULT_MAX_CHARS = 3500  # 单工具结果注入上限(防上下文爆炸)

_registry: dict | None = None


def _get_registry() -> dict:
    """现有 21 工具 + stockbot 新增 5 工具。延迟加载(routers.finmcp 导入较重)。"""
    global _registry
    if _registry is None:
        from .registry import TOOL_REGISTRY
        _registry = {
            **TOOL_REGISTRY,
            "get_technical_analysis": tools_ta.get_technical_analysis,
            "get_realtime_moneyflow": tools_rt.get_realtime_moneyflow,
            "get_intraday_trend": tools_rt.get_intraday_trend,
            "get_sector_moneyflow_rank": tools_rt.get_sector_moneyflow_rank,
            "get_limit_up_pool": tools_rt.get_limit_up_pool,
            "get_market_context": market_regime.get_market_context,
        }
    return _registry


_TOOLS_SCHEMA = [{
    "type": "function",
    "function": {
        "name": "call_tool",
        "description": "调用行情/数据工具获取真实数据。工具清单见 system prompt。",
        "parameters": {
            "type": "object",
            "properties": {
                "tool": {"type": "string", "description": "工具名, 如 get_technical_analysis"},
                "params": {"type": "object", "description": "工具参数对象, 如 {\"stock_code\": \"601958\"}"},
            },
            "required": ["tool"],
        },
    },
}]


def _run_tool(tool: str, params: dict) -> dict:
    """同步执行单工具(超时由外层分发池控制, 底层 HTTP 均自带 ≤12s 超时)。"""
    reg = _get_registry()
    fn = reg.get(tool)
    if fn is None:
        return {"ok": False, "error": {"message": f"未知工具: {tool}"}}
    try:
        return fn(**(params or {}))
    except TypeError as e:
        return {"ok": False, "error": {"message": f"{tool} 参数错误: {str(e)[:120]}"}}
    except Exception as e:
        return {"ok": False, "error": {"message": f"{tool} 失败: {str(e)[:150]}"}}


def _sector_news(topic: str, sector: str = "", days: int = 3, limit: int = 8) -> str:
    """板块/主题近期消息面(自采集新闻库). 2026-08-17: 事件驱动 vs 纯资金脉冲, 持续性差异巨大,
    板块/选股路径必须知道催化在不在。空返回空串(缺一角比编造好)。"""
    import os as _os
    import sqlite3
    db = _os.path.join(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))),
                       "data", "fin_news.db")
    if not _os.path.exists(db):
        return ""
    kws = [k for k in (topic, sector) if k and len(k) >= 2]
    if not kws:
        return ""
    try:
        conn = sqlite3.connect(db)
        conn.row_factory = sqlite3.Row
        since = int(time.time()) - days * 86400
        where = " OR ".join("(title LIKE ? OR content LIKE ?)" for _ in kws)
        params = []
        for k in kws:
            params += [f"%{k}%", f"%{k}%"]
        rows = conn.execute(
            f"SELECT title, content, published_at, fetched_at FROM news "
            f"WHERE fetched_at >= ? AND ({where}) ORDER BY fetched_at DESC LIMIT 80",
            [since] + params,
        ).fetchall()
        conn.close()
    except Exception:
        return ""
    if not rows:
        return ""
    # 命中数+新鲜度排序; 标题前缀去重(同一事件多源转载防刷屏)
    scored = []
    now = time.time()
    for r in rows:
        title = r["title"] or ""
        content = (r["content"] or "")[:200]
        hits = sum(3 if k in title else (1 if k in content else 0) for k in kws)
        if hits == 0:
            continue
        age_h = max(0, (now - (r["fetched_at"] or 0)) / 3600)
        fresh = max(0, 3 - age_h / 24)  # 24h 内 3 分, 递减到 72h 归零
        scored.append((hits * 2 + fresh, title, content, r["published_at"], r["fetched_at"]))
    if not scored:
        return ""
    scored.sort(key=lambda x: -x[0])
    picked, seen = [], set()
    for _, title, content, pub, fetched in scored:
        key = title[:12]
        if key in seen:
            continue
        seen.add(key)
        # 时间标注(优先 published_at, 无则 fetched)
        ts_str = ""
        try:
            src_ts = int(fetched or 0)
            if src_ts:
                ts_str = time.strftime("%m-%d %H:%M", time.localtime(src_ts))
        except Exception:
            pass
        picked.append(f"- [{ts_str}] {title[:80]}" + (f": {content[:100]}" if content else ""))
        if len(picked) >= limit:
            break
    return "近3天相关消息面(自采集新闻库):\n" + "\n".join(picked)


def _shrink(obj) -> str:
    s = json.dumps(obj, ensure_ascii=False, default=str)
    if len(s) > RESULT_MAX_CHARS:
        s = s[:RESULT_MAX_CHARS] + '…(截断)"}'
    return s


def _session_state(now: _dt.datetime) -> str:
    if now.weekday() >= 5:
        return "周末休市"
    hm = now.hour * 60 + now.minute
    if 570 <= hm <= 690:
        return "A股交易中(上午盘)"
    if 690 < hm < 780:
        return "A股午间休市"
    if 780 <= hm <= 900:
        return "A股交易中(下午盘)"
    return "A股已收盘" if hm > 900 else "A股未开盘"


def _build_system() -> str:
    now = _dt.datetime.now()
    week = "一二三四五六日"[now.weekday()]
    session = _session_state(now)
    date_line = (f"# 当前时间\n{now.strftime('%Y-%m-%d %H:%M')} 周{week}, {session}。"
                 "所有'今天/现在'均以此为准, 严禁使用训练记忆里的日期和行情。")
    # 时段感知指引(2026-08-17 Donnie: 休市/盘后消息面对开盘影响很大, 分析姿态要区分)
    if "休市" in session or "已收盘" in session or "未开盘" in session:
        date_line += ("\n【时段姿态】当前非盘中, 行情快照定格, 分析重点在**盘后消息面对下一交易日开盘的影响**: "
                      "有实质催化(政策/业绩/事件)→说明开盘方向偏向; 无消息→说清纯技术面判断到下个交易日可能失效。")
    # 预取市场环境注入(原始事实, 无档位判定; 失败则由模型自行调 get_market_context)
    ctx_line = ""
    try:
        r = market_regime.get_market_context()
        if r.get("ok"):
            d = r["data"]
            idx = ", ".join(f"{i['name']}{i['pct_change']:+.2f}%" for i in d["indices"]
                            if i.get("pct_change") is not None)
            hot = ", ".join(f"{h['board']}({h['main_net_yi']:+}亿)" for h in (d.get("hot_sectors") or [])[:5]
                            if h.get("main_net_yi") is not None)
            out = ", ".join(f"{h['board']}({h['main_net_yi']:+}亿)" for h in (d.get("outflow_sectors") or [])
                            if h.get("main_net_yi") is not None)
            hv = d.get("hs300_vs_ma60") or {}
            hs_line = (f"沪深300 {hv['point']} vs 60日线 {hv['ma60']} ({hv['pct_vs_ma60']:+}%)"
                       if hv.get("pct_vs_ma60") is not None else "")
            ctx_line = (f"\n\n# 当日市场环境(已实时预取, 原始事实, 作为背景参考)\n"
                        f"指数: {idx} | 涨{d['market_breadth']['up']}家/跌{d['market_breadth']['down']}家"
                        f" | 两市成交{d['total_amount_yi']}亿\n"
                        + (hs_line + "\n" if hs_line else "")
                        + (f"主力净流入板块前5: {hot}\n" if hot else "")
                        + (f"主力净流出板块前3: {out}" if out else ""))
    except Exception:
        logger.warning("市场环境预取失败, 留给模型自行调用")
    return f"{PERSONA_PROMPT}\n\n{date_line}{ctx_line}\n\n{TOOL_DOCS}"


# 过渡语/半截话识别: DeepSeek 偶发"嘴上说要调工具但没真发 function call",
# 此时 content 是中间态不是终稿, 不能直接返回(否则群里收到"我再看一下X…"半句)。
_TRANSITION_RE = re.compile(
    r"^\s*(我(现在|先|再|来|还|需要|得|接着|继续)?(看|查|拉|调|确认|核实|获取|分析|了解)"
    r"|让我|接下来|下面我|稍等|马上|等我|我需要|请稍)")


def answer(question: str, context: str = "") -> dict:
    """引擎入口。context 可携带会话上下文(如群里同话题的上一问)。
    返回 {"answer": str, "tool_trace": [...], "rounds": int}
    """
    from .config import get_llm as _get_llm
    client = _get_llm(MODEL)
    user = f"[会话上下文]\n{context}\n\n[群友提问]\n{question}" if context else question
    messages = [{"role": "system", "content": _build_system()},
                {"role": "user", "content": user}]
    trace = []
    salvage = 0  # 续写守卫计数(防死循环)
    for rnd in range(1, MAX_ROUNDS + 1):
        final_round = rnd == MAX_ROUNDS
        resp = client.chat.completions.create(
            model=MODEL,
            messages=messages,
            tools=None if final_round else _TOOLS_SCHEMA,
            temperature=0.4,
            max_tokens=2048,
            timeout=120,
        )
        msg = resp.choices[0].message
        calls = getattr(msg, "tool_calls", None) or []
        if not calls:
            content = (msg.content or "").strip()
            # 续写守卫: 空/半截话/过渡语开头 → 是中间态而非终稿, 逼模型一次成稿(最多补救2次)
            if not final_round and salvage < 2 and (
                    not content or len(content) < 60 or _TRANSITION_RE.match(content)):
                salvage += 1
                logger.info("[salvage] 第%d次: 检测到过渡语/半截话, 要求重出终稿", salvage)
                messages.append({"role": "assistant", "content": content})
                messages.append({"role": "user", "content":
                    "把已采集到的数据整合成给群友的完整最终回答, 一次成稿: 不要说"
                    "'我再看/让我看/接下来查'这类过程话, 不要中途停顿, 直接给结论+数据+操作。"})
                continue
            return {"answer": scrub_compliance(content), "tool_trace": trace, "rounds": rnd}
        messages.append({"role": "assistant", "content": msg.content or "",
                         "tool_calls": [c.model_dump() for c in calls]})
        # 单轮多工具并行执行
        parsed = []
        for c in calls:
            try:
                args = json.loads(c.function.arguments or "{}")
            except json.JSONDecodeError:
                args = {}
            parsed.append((c.id, args.get("tool", ""), args.get("params") or {}))
        pool = ThreadPoolExecutor(max_workers=min(10, max(1, len(parsed))))
        futs = {cid: pool.submit(_run_tool, tool, params) for cid, tool, params in parsed}
        deadline = TOOL_TIMEOUT_S + 5 * max(0, len(parsed) - 10) / 10  # 超发时给排队余量
        for cid, tool, params in parsed:
            try:
                result = futs[cid].result(timeout=deadline)
            except _FutTimeout:
                result = {"ok": False, "error": {"message": f"{tool} 超时"}}
            except Exception as e:
                result = {"ok": False, "error": {"message": str(e)[:150]}}
            trace.append({"round": rnd, "tool": tool, "params": params,
                          "ok": bool(result.get("ok"))})
            logger.info("[tool] r%d %s(%s) ok=%s", rnd, tool,
                        json.dumps(params, ensure_ascii=False)[:80], result.get("ok"))
            messages.append({"role": "tool", "tool_call_id": cid, "content": _shrink(result)})
        pool.shutdown(wait=False, cancel_futures=True)
        if rnd == MAX_ROUNDS - 1:
            messages.append({"role": "user",
                             "content": "数据采集轮次已用完, 请基于以上已有数据直接给出最终回答。"})
    return {"answer": "", "tool_trace": trace, "rounds": MAX_ROUNDS}


# ── 快速通道: 个股问题跳过多轮规划, 并行预取标准数据包 + 单次成文 ──────────

_ROUTER_PROMPT = """从群友的股票问题中提取路由信息, 只输出JSON, 不要任何其他文字:
{"type": "stock"|"sector"|"ranking"|"board_pick"|"other", "stocks": ["股票名或6位代码"], "sector": "板块/题材名或空", "count": 5, "price_max": null}
规则: 只围绕1只具体股票(诊断/能不能买/怎么看/被套) → stock;
从某板块里选N只/最值得买的N只/排优先级/推荐几只/哪几只好 → ranking, sector 填板块名, count 填要几只(默认5);
围绕某板块整体能不能买/怎么样 → sector, sector 填题材名;
**给我N个/推荐N个/挑几个 板块/细分板块/方向/题材** → **board_pick** (排板块不是选股!), count 填要几个(默认3);
多股对比(用户已给定具体几只)/大盘/科普/其他 → other。
【重要】"热点/风口/资金流向/大数据分析/量化/技术面" 这类词是**分析方法描述**, 不是板块名——
严禁把"大数据分析"当成大数据板块! 用户没点名具体板块的选股(如"结合热点资金给我N只短线") →
ranking 且 sector 填 ""(空=按当日热点板块全市场选)。
价格约束("20以内/20元以下/低价股") → price_max 填数字(如 20), 没提就 null。
【区分】"给我3个板块" = board_pick / "给我3只股票" = ranking / "半导体怎么样" = sector / "半导体里选3只" = ranking。"""

_FAST_BUNDLE = ("get_technical_analysis", "get_realtime_moneyflow",
                "get_intraday_trend", "get_latest_quote", "get_stock_news",
                "get_financial_indicator", "get_earnings_forecast")  # 基本面维度(2026-08-10 Donnie 批准加入)

# 板块问答对每只选中票的数据包(核心4件, 下短线买卖结论足够, 与个股路径核心一致)
_SECTOR_STOCK_BUNDLE = ("get_technical_analysis", "get_realtime_moneyflow",
                        "get_intraday_trend", "get_latest_quote")


def _route(client, question: str) -> dict:
    try:
        resp = client.chat.completions.create(
            model=MODEL, temperature=0, max_tokens=100, timeout=15,
            messages=[{"role": "system", "content": _ROUTER_PROMPT},
                      {"role": "user", "content": question}],
        )
        m = re.search(r"\{[\s\S]*\}", resp.choices[0].message.content or "")
        return json.loads(m.group(0)) if m else {}
    except Exception as e:
        logger.warning("路由失败(%s), 走完整循环", str(e)[:80])
        return {}


def _resolve_code(name_or_code: str) -> str | None:
    s = name_or_code.strip()
    if re.fullmatch(r"\d{6}", s):
        return s
    try:
        from .registry import TOOL_REGISTRY
        r = TOOL_REGISTRY["search_stocks_by_name"](s, 1)
        hits = r.get("data") or []
        if r.get("ok") and hits:
            return str(hits[0].get("ts_code") or hits[0].get("stock_code") or "").split(".")[0] or None
    except Exception:
        pass
    return None


_SECTOR_PICK_PROMPT = """群友问的是"{sector}"这个题材/板块能不能买。列出该题材当前 A 股最有代表性的 3-4 只龙头/核心标的。
只输出JSON: {{"stocks": ["股票名", ...]}}。只给真实存在的A股, 拿不准就少给, 不要编。"""


def _sector_picks(client, sector_name: str, want: int = 4) -> tuple[str, list[str]]:
    """板块选票(确定性优先): 返回 (板块显示名, [6位代码...])。
    ①东财标准板块→按当日主力净流入取前 want(确定, 稳定复现)
    ②口语题材东财无板块→LLM列代表股+search验证代码(覆盖'算力租赁'这类)"""
    r = tools_rt.get_sector_top_stocks(sector_name, top_n=want)
    if r.get("ok") and r["data"]["top_stocks"]:
        return r["data"]["sector"], [s["stock_code"] for s in r["data"]["top_stocks"]]
    # 兜底: LLM 列票 + search 验证(避免编造代码)
    try:
        resp = client.chat.completions.create(
            model=MODEL, temperature=0, max_tokens=200, timeout=15,
            messages=[{"role": "user", "content": _SECTOR_PICK_PROMPT.format(sector=sector_name)}])
        m = re.search(r"\{[\s\S]*\}", resp.choices[0].message.content or "")
        names = (json.loads(m.group(0)).get("stocks") or []) if m else []
    except Exception:
        names = []
    codes = []
    for nm in names[:max(want, 5)]:
        c = _resolve_code(nm)
        if c and c not in codes:
            codes.append(c)
    return sector_name, codes


def answer_sector(sector_name: str, question: str, context: str = "") -> dict:
    """板块问答(方向2根治一致性): 确定性/半确定性选票 → 对每只跑个股级完整数据 →
    照个股同一标准汇总。保证'板块里某只票'的结论 == '单独问这只票'的结论。"""
    from .config import get_llm as _get_llm
    client = _get_llm(MODEL)
    t0 = time.time()
    disp, codes = _sector_picks(client, sector_name)
    if not codes:
        r = answer(question, context)          # 选票彻底失败才退回 agentic
        r["path"] = "agentic"
        return r
    # 对每只并行跑个股级数据包
    pool = ThreadPoolExecutor(max_workers=min(12, len(codes) * len(_SECTOR_STOCK_BUNDLE)))
    jobs = {(c, t): pool.submit(_run_tool, t, {"stock_code": c})
            for c in codes for t in _SECTOR_STOCK_BUNDLE}
    trace, per_stock = [], []
    for c in codes:
        parts = []
        for t in _SECTOR_STOCK_BUNDLE:
            try:
                res = jobs[(c, t)].result(timeout=TOOL_TIMEOUT_S)
            except Exception as e:
                res = {"ok": False, "error": {"message": str(e)[:100]}}
            trace.append({"round": 1, "tool": t, "params": {"stock_code": c}, "ok": bool(res.get("ok"))})
            parts.append(f"[{t}] {_shrink(res)}")
        per_stock.append(f"### {c}\n" + "\n".join(parts))
    pool.shutdown(wait=False, cancel_futures=True)
    data_text = "\n\n".join(per_stock)
    news_block = _sector_news(sector_name, disp)  # 2026-08-17 消息面注入(事件驱动 vs 资金脉冲判断)
    user = (f"[群友提问]\n{question}\n\n"
            f"[题材/板块]\n{disp}\n\n"
            f"[已对该板块内当日资金最强的 {len(codes)} 只跑了完整个股数据, 直接引用]\n{data_text}\n\n"
            + (f"[近期消息面]\n{news_block}\n\n" if news_block else "[近期消息面]\n无明确催化消息(纯资金/技术面行情, 持续性存疑)\n\n") +
            "输出要求: ①开头一句该板块自身整体状态+**归因(技术/资金/消息哪个是主驱动)** "
            "(不是拿别的风口当主线) ②对每只用和单独问个股时完全一样的标准下结论(BIAS/60日位置/资金 → "
            "能上/等回踩/别碰), 结论必须与其数据一致, 重词纪律照旧; 交叉题材股要点破当日真实驱动 "
            "③最后点出最值得关注的1-2只并说明**下个交易日/近期催化是否还在**。"
            "回答主体必须是用户问的这个板块, 别的板块最多一句带过。篇幅350-600字。")
    if context:
        user = f"[会话上下文]\n{context}\n\n{user}"
    resp = client.chat.completions.create(
        model=MODEL, temperature=0.4, max_tokens=1200, timeout=120,
        messages=[{"role": "system", "content": _build_system()},
                  {"role": "user", "content": user}])
    logger.info("[sector] %s picks=%s %.0fs", disp, codes, time.time() - t0)
    return {"answer": scrub_compliance((resp.choices[0].message.content or "").strip()),
            "tool_trace": trace, "rounds": 1, "path": "sector"}


_RANK_SORT_RULES = (
    "排序标准(短线买入价值, 从高到低综合判断): ①技术面多头排列 ②BIAS20在甜区(<15%)且不超买(RSI6<80) "
    "③主力资金净流入 ④60日位置偏低(有上行空间) ⑤放量突破关键位。"
    "出货结构(主力净流出)/BIAS20>20极端超买/空头排列 → 排最后或直接剔除, 不许硬塞进推荐位。")


def answer_board_pick(question: str, count: int = 3, context: str = "") -> dict:
    """选板块(不是选股): "给我3个明天可以买的细分板块" 这类。2026-08-17 Donnie:
    原来被路由成 ranking 直接给9只票, 用户要的是板块层面推荐。
    候选=当日主力净流入靠前的**细分板块**(排除电子/半导体/通信/医药等父级大类,
    父级涵盖太广不算"细分"), 每个带资金/涨幅/2-3只领涨股, LLM 综合排序。"""
    from .config import get_llm as _get_llm
    client = _get_llm(MODEL)
    t0 = time.time()
    count = max(1, min(int(count or 3), 5))
    # 父级/大类词过滤(用户口中"细分板块"排除这些)
    PARENT = {"电子", "半导体", "通信", "医药", "医药生物", "计算机", "机械设备",
              "电力设备", "汽车", "国防军工", "化工", "有色金属", "钢铁", "煤炭",
              "食品饮料", "家用电器", "轻工制造", "建筑材料", "建筑装饰",
              "银行", "非银金融", "房地产", "商业贸易", "农林牧渔", "综合", "传媒",
              "环保", "美容护理", "纺织服饰", "社会服务", "公用事业", "交通运输"}
    rk = tools_rt.get_sector_moneyflow_rank(top_n=25, board_type="industry")
    boards = []
    for b in ((rk.get("data") or {}).get("top_inflow") or []):
        bn = b.get("board") or ""
        if bn and bn not in PARENT and len(bn) >= 3:  # 名字>=3字过滤大类(电子/银行等)
            boards.append(b)
        if len(boards) >= count * 3:  # 取候选3倍数量, 让LLM再筛
            break
    if len(boards) < count:  # 细分池不够, 补概念榜
        rk2 = tools_rt.get_sector_moneyflow_rank(top_n=15, board_type="concept")
        seen_n = {b["board"] for b in boards}
        for b in ((rk2.get("data") or {}).get("top_inflow") or []):
            if b.get("board") and b["board"] not in seen_n and b["board"] not in PARENT:
                boards.append(b); seen_n.add(b["board"])
            if len(boards) >= count * 3:
                break
    if not boards:
        return {"answer": "现在拿不到明确的板块资金数据, 换个问法或稍后再问。",
                "tool_trace": [], "rounds": 1, "path": "board_pick"}
    # 每个候选板块拉 top 2 只成分股 (Donnie 2026-08-18: 板块推荐必须带具体标的可关注)
    rows, trace = [], []
    board_stocks = {}  # board_name -> [(name, code), ...]
    all_codes = []     # 全部去重后的 code, 后面统一并行拉深度数据
    for b in boards:
        bname = b["board"]
        rr = tools_rt.get_sector_top_stocks(bname, top_n=2, sort_by="flow")
        trace.append({"round": 1, "tool": "get_sector_top_stocks",
                     "params": {"sector_name": bname, "top_n": 2}, "ok": bool(rr.get("ok"))})
        top2 = []
        if rr.get("ok") and rr["data"]["top_stocks"]:
            for s in rr["data"]["top_stocks"][:2]:
                nm = s.get("name")
                cd = s.get("stock_code") or s.get("code")  # 数据源返回 stock_code
                if nm and cd:
                    top2.append((nm, cd))
                    if cd not in all_codes:
                        all_codes.append(cd)
        board_stocks[bname] = top2
        leaders_display = "、".join(f"{n}" for n, _ in top2) or "-"
        rows.append({"板块": bname, "涨跌%": b.get("pct_change"),
                     "主力净流入亿": b.get("main_net_yi"),
                     "主力净占比%": b.get("main_net_pct"),
                     "候选股": leaders_display})
    # 并行拉每只候选股的技术面+资金面(轻量2件, 板块推荐用不着完整个股 5 件套)
    STOCK_MINI_BUNDLE = ("get_technical_analysis", "get_realtime_moneyflow")
    pool = ThreadPoolExecutor(max_workers=min(12, max(1, len(all_codes) * len(STOCK_MINI_BUNDLE))))
    jobs = {(c, t): pool.submit(_run_tool, t, {"stock_code": c})
            for c in all_codes for t in STOCK_MINI_BUNDLE}
    stock_cards = {}   # code -> markdown 卡片
    for c in all_codes:
        parts = []
        for t in STOCK_MINI_BUNDLE:
            try:
                res = jobs[(c, t)].result(timeout=TOOL_TIMEOUT_S)
            except Exception as e:
                res = {"ok": False, "error": {"message": str(e)[:100]}}
            trace.append({"round": 1, "tool": t, "params": {"stock_code": c}, "ok": bool(res.get("ok"))})
            parts.append(f"[{t}] {_shrink(res)}")
        stock_cards[c] = "\n".join(parts)
    pool.shutdown(wait=False, cancel_futures=True)
    # 组装 LLM 数据: 板块表 + 每板块的候选股详细数据
    data_text = "\n".join(json.dumps(r, ensure_ascii=False) for r in rows)
    stock_detail_blocks = []
    for bname, stks in board_stocks.items():
        if not stks:
            continue
        block_lines = [f"### 【{bname}】板块候选股"]
        for nm, cd in stks:
            card = stock_cards.get(cd, "(无数据)")
            block_lines.append(f"**{nm}({cd})**\n{card}")
        stock_detail_blocks.append("\n".join(block_lines))
    stock_detail = "\n\n".join(stock_detail_blocks) if stock_detail_blocks else "(候选股数据未拉到)"

    news_block = _sector_news("板块热点", "")
    user = (f"[群友提问]\n{question}\n\n"
            f"[今日细分板块资金流入榜(已排除电子/半导体/通信等父级大类, 候选 {len(rows)} 个)]\n{data_text}\n\n"
            f"[候选股深度数据(技术面+主力资金, 已并行拉取)]\n{stock_detail}\n\n"
            + (f"[近期消息面]\n{news_block}\n\n" if news_block else "[近期消息面]\n无明确催化消息(纯资金/技术面行情, 持续性存疑)\n\n") +
            f"要求:\n"
            f"①**第一句必须直接给结论**——'我给你的 {count} 个板块是: X、Y、Z'(一行摆出), "
            f"严禁'X个板块都能看'这种没头没脑的开头(2026-08-17 事故)。\n"
            f"②然后分块讲每个板块, 每块 3 部分: "
            f"  a) 板块名(标注**东财板块**四字) + 主力净流入/占比 + **一句归因**(消息催化 or 纯资金脉冲) + 一句操作节奏\n"
            f"  b) **【值得关注】格式点评 2 只候选股**——每只必须挂 BIAS20 位置/60日位置/主力资金 三个数据+一句'能上/等回踩/别追'的判断。\n"
            f"     **候选股判断硬规则(2026-08-18 京东方A 三路径结论不一致事故, 强制统一到 ranking 排序标准)**:\n"
            f"     - {_RANK_SORT_RULES}\n"
            f"     - **甜区(BIAS20<15) + 60日位置<35% + 主力净流入**三条件同时满足 → **必须** '能上'/'能看', 严禁用'别追/看不清/趋势没走出来'等否决词把它推翻;\n"
            f"       MACD 零轴下/均线交织 是弱信号, 只能'仓位收一档'(如给 1 成不给 2 成), **不能**推翻上面的 ✅ 结论\n"
            f"     - '别追/看不清'只有在: 出货结构(主力持续净流出) OR BIAS20>20极端超买 OR 空头排列 时才用\n"
            f"     - 目的: 同一只股在 fast/ranking/board_pick 三路径里必须给一致结论, 不能这里 ✅ 那里 ❌\n"
            f"  c) 交叉股要点破: 若这只票主业不属该板块只是概念挂钩, 明说它今天走的是别的逻辑\n"
            f"③最后一句总结: 这 {count} 个里最优先看哪个板块+哪只票、原因。\n"
            f"忠实度: 板块必须来自[资金流入榜], 候选股必须来自[候选股深度数据], 都不许自己编。篇幅 500-800 字, 群聊场景信息密度优先。")
    if context:
        user = f"[会话上下文]\n{context}\n\n{user}"
    resp = client.chat.completions.create(
        model=MODEL, temperature=0.4, max_tokens=1200, timeout=120,
        messages=[{"role": "system", "content": _build_system()},
                  {"role": "user", "content": user}])
    logger.info("[board_pick] count=%d cand=%d %.0fs", count, len(rows), time.time() - t0)
    return {"answer": scrub_compliance((resp.choices[0].message.content or "").strip()),
            "tool_trace": trace, "rounds": 1, "path": "board_pick"}


def answer_ranking(sector_name: str, question: str, count: int = 5, context: str = "",
                   price_max: float = None) -> dict:
    """选股/排序: 从板块候选池按短线买入价值排序, 输出指定数量+优先级(方向2姊妹路径)。
    候选池对每只跑个股级技术+资金 → 照统一标准打分排序, 不硬凑'都能买'。
    sector_name 为空 = 全市场热点模式(2026-08-14 事故: "结合热点资金大数据分析选5只"被路由成
    大数据板块答非所问): 候选池=当日主力净流入前3行业板块各取资金榜前5。
    price_max: 用户价格约束(如 20 元以内), 候选池硬过滤。"""
    from .config import get_llm as _get_llm
    client = _get_llm(MODEL)
    t0 = time.time()
    count = max(1, min(int(count or 5), 8))
    cand, seen, disp = [], set(), sector_name
    hot_mode = not sector_name or sector_name in ("热点", "风口", "全市场", "热门", "大盘")
    if hot_mode:
        # 全市场热点: 当日资金净流入靠前行业为候选板块(语义=“结合当下热点资金流向”)。
        # 东财行业榜有层级(通信/通信设备/通信线缆是父子), 按前2字去系防候选同质化
        rk = tools_rt.get_sector_moneyflow_rank(top_n=10, board_type="industry")
        boards, _fams = [], set()
        for b in ((rk.get("data") or {}).get("top_inflow") or []):
            bn = b.get("board") or ""
            fam = bn[:2]
            if bn and fam not in _fams:
                _fams.add(fam); boards.append(bn)
            if len(boards) >= 3:
                break
        # 有价格约束时低价股常排资金榜后段, 加深抓取
        per_board = 15 if price_max else 5
        for bname in boards:
            rr = tools_rt.get_sector_top_stocks(bname, top_n=per_board, sort_by="flow")
            if rr.get("ok") and rr["data"]["top_stocks"]:
                for s in rr["data"]["top_stocks"]:
                    if s["stock_code"] not in seen:
                        seen.add(s["stock_code"]); s["所属板块"] = rr["data"]["sector"]; cand.append(s)
        disp = "今日资金热点(" + "、".join(boards) + ")" if boards else "今日热点"
    else:
        # 候选池 = 市值龙头 ∪ 当日资金强, 合并去重(防龙头因当日资金流出被漏掉, 如北方华创/中微)
        r_mv = tools_rt.get_sector_top_stocks(sector_name, top_n=12, sort_by="mv")
        r_flow = tools_rt.get_sector_top_stocks(sector_name, top_n=10, sort_by="flow")
        for rr in (r_mv, r_flow):
            if rr.get("ok") and rr["data"]["top_stocks"]:
                disp = rr["data"]["sector"]
                for s in rr["data"]["top_stocks"]:
                    if s["stock_code"] not in seen:
                        seen.add(s["stock_code"]); cand.append(s)
    # 价格硬过滤(约束丢失=答非所问的一半)
    if price_max and cand:
        priced = [c for c in cand if isinstance(c.get("price"), (int, float))]
        if priced:  # 有价格数据才过滤, 全无价格(LLM兜底票)交给 prompt 约束
            cand = [c for c in priced if c["price"] <= float(price_max)]
    if cand:
        had_flow = True
    elif not hot_mode:  # 口语题材东财无板块 → LLM 列票兜底
        disp, codes = _sector_picks(client, sector_name, want=max(count * 2, 8))
        if not codes:
            rr = answer(question, context); rr["path"] = "agentic"; return rr
        cand, had_flow = [{"stock_code": c} for c in codes], False
    else:  # 热点模式过滤后空(如20元内无候选): 如实告知而不是硬凑
        return {"answer": f"按你的条件筛了一圈——今天资金净流入靠前的板块里, "
                          f"{'股价' + str(price_max) + '元以内' if price_max else ''}够格的候选是空的, "
                          f"我不硬凑。要么放宽价格, 要么等明天资金结构变了再看。",
                "tool_trace": [], "rounds": 1, "path": "ranking"}
    cand = cand[:15]
    codes = [c["stock_code"] for c in cand]
    pool = ThreadPoolExecutor(max_workers=min(12, len(codes) * (1 if had_flow else 2)))
    ta_jobs = {c: pool.submit(_run_tool, "get_technical_analysis", {"stock_code": c}) for c in codes}
    mf_jobs = {} if had_flow else {
        c: pool.submit(_run_tool, "get_realtime_moneyflow", {"stock_code": c}) for c in codes}
    trace, rows = [], []
    for c in cand:
        code = c["stock_code"]
        try:
            ta = ta_jobs[code].result(timeout=TOOL_TIMEOUT_S)
            tad = ta.get("data") if ta.get("ok") else None
        except Exception:
            tad = None
        trace.append({"round": 1, "tool": "get_technical_analysis", "params": {"stock_code": code}, "ok": bool(tad)})
        row = {"代码": code, "名称": c.get("name")}
        if c.get("所属板块"):
            row["所属板块"] = c["所属板块"]
        if c.get("price") is not None:
            row["现价"] = c.get("price")
        if had_flow:
            row.update({"涨跌%": c.get("pct_change"), "主力净流入亿": c.get("main_net_yi"),
                        "主力净占比%": c.get("main_net_pct")})
        else:
            try:
                mf = mf_jobs[code].result(timeout=TOOL_TIMEOUT_S)
                md = mf["data"]["today_realtime"] if mf.get("ok") else {}
            except Exception:
                md = {}
            trace.append({"round": 1, "tool": "get_realtime_moneyflow", "params": {"stock_code": code}, "ok": bool(md)})
            row.update({"名称": md.get("name") or row["名称"], "涨跌%": md.get("pct_change"),
                        "主力净流入亿": md.get("main_net_yi"), "主力净占比%": md.get("main_net_pct")})
        if tad:
            row.update({"BIAS20": tad.get("bias", {}).get("bias20"), "均线": tad.get("ma_alignment"),
                        "60日位置%": tad.get("position", {}).get("pct_in_60d_range"),
                        "MACD零轴上": tad.get("macd", {}).get("above_zero"),
                        "RSI6": tad.get("rsi", {}).get("rsi6")})
        rows.append(row)
    pool.shutdown(wait=False, cancel_futures=True)
    data_text = "\n".join(json.dumps(x, ensure_ascii=False) for x in rows)
    # 消息面(2026-08-17): 热点模式取入选板块合集, 常规模式取该板块; 无消息也是信息
    _news_topic = " ".join({(r.get("所属板块") or "") for r in rows if r.get("所属板块")}) if hot_mode else sector_name
    _news_block = _sector_news(_news_topic, disp if not hot_mode else "")
    _constraint = f"股价 {price_max} 元以内(候选已按此过滤)" if price_max else ""
    _fidelity = (
        # 热点模式: 主体=今日资金热点, 不存在"用户问的板块"
        f"忠实度要求: 候选来自今日资金净流入靠前的板块(见'所属板块'字段), 点评时带上所属板块; "
        if hot_mode else
        f"忠实度要求: 回答主体必须是用户问的这个板块; 推荐序列(1/2/3…)只许放主业纯正标的, "
        f"当日由其他题材驱动的交叉股一律不入榜、放末尾附注并点破真实驱动('想做那题材另问'); "
        f"纯正标的必须点评(即使当日弱, 全弱就明说没有能买的+给复查条件); "
        f"严禁把答案变成别的风口板块的推荐。开头一句该板块自身整体。")
    user = (f"[群友提问]\n{question}\n\n[候选来源]\n{disp}"
            + (f"\n[用户硬约束]\n{_constraint}" if _constraint else "") +
            f"\n\n[候选池 {len(rows)} 只的实时数据]\n{data_text}\n\n"
            + (f"[近期消息面]\n{_news_block}\n\n" if _news_block else "[近期消息面]\n无明确催化消息(纯资金/技术面行情, 持续性存疑)\n\n") +
            f"{_RANK_SORT_RULES}\n\n"
            f"输出: **第一句必须先复述筛选口径**(候选从哪来{'+价格约束' if price_max else ''}+要几只), "
            f"让群友知道'这N只'指的是什么——严禁上来就说'这3只'这种没头没尾的指代(2026-08-14 群友看不懂事故)。"
            f"然后从候选里按短线买入价值排序, 给出优先级前 {count} 只(编号1/2/3…)。"
            f"每只: 名称(标注**东财板块归属**如'东财数字芯片设计', 让群友知道分类来源, 因东财板块口径与用户直觉可能有差异)"
            f"+一句话理由(必须挂 BIAS/60日位置/主力资金, 有对应消息面时点出催化)+简短操作。"
            f"结尾一句总归因(**事件驱动 vs 纯资金脉冲**, 影响持续性判断)。"
            f"若真达标的不足 {count} 只, 诚实说'够格的只有N只', 其余仍按序列出但标明硬伤, 不硬吹。"
            f"{_fidelity}篇幅400-700字。")
    if context:
        user = f"[会话上下文]\n{context}\n\n{user}"
    resp = client.chat.completions.create(
        model=MODEL, messages=[{"role": "system", "content": _build_system()},
                               {"role": "user", "content": user}],
        temperature=0.4, max_tokens=1400, timeout=120)
    logger.info("[ranking] %s cand=%d want=%d %.0fs", disp, len(rows), count, time.time() - t0)
    return {"answer": scrub_compliance((resp.choices[0].message.content or "").strip()),
            "tool_trace": trace, "rounds": 1, "path": "ranking"}


# ── 引擎层硬约束(代码强制, 不依赖模型自觉, 100%稳定) ──
_GAP_KEYWORDS = [
    (("高股息", "股息率", "红利股"), "股息率"),
    (("解禁", "限售股"), "解禁/限售"),
    (("两融", "融资融券"), "两融"),
    (("北向", "北上资金"), "北向资金个股明细"),
    (("大宗交易",), "大宗交易"),
]


def _gap_notice(question: str) -> str:
    """问题命中无数据维度/ST → 返回硬指令(注入prompt, 强于persona软规则)。"""
    parts = []
    hit = [label for kws, label in _GAP_KEYWORDS if any(k in question for k in kws)]
    if hit:
        parts.append(f"涉及「{'、'.join(hit)}」你的工具没有这些数据, 必须开门见山说'{hit[0]}这个数据我没有',"
                     " 只答有数据支撑的部分, 严禁编造任何相关数字。")
    if "ST" in question.upper() or "摘帽" in question:
        parts.append("涉及ST股, 回答里必须明确提示: ST有退市风险、每日涨跌停限制5%。")
    if any(k in question for k in ("连板", "打板", "妖股", "涨停")):
        parts.append("涉及连板/涨停, 必须用打板框架分析(连板高度/封单/炸板/换手/首封时间/全市场情绪),"
                     " 严禁只用BIAS超买劝退; 必须声明打板是高赔率低胜率游戏没人能预测,"
                     " 给纪律(小仓/破分时均价线走/不过夜)。")
    if any(k in question for k in ("PE", "pe", "估值", "贵不贵", "市盈率")):
        parts.append("涉及估值, 必须同时给出 动态PE 和 PE-TTM 两个口径的具体数值并标注口径,"
                     " 且结合业绩趋势(动态vsTTM差异/ROE/增速)判断贵不贵, 不许只甩一个数。")
    return "\n[数据/合规边界·硬约束] " + " ".join(parts) if parts else ""


def _enforce_st_warning(answer: str, name: str) -> str:
    """ST股回答若漏退市风险提示→强制补上(合规硬要求, 不靠模型自觉)。"""
    if not answer or "ST" not in (name or "").upper():
        return answer
    if "退市" in answer or "5%" in answer:
        return answer
    return answer + "\n\n⚠️ 这是ST股，有退市风险，每日涨跌停限制5%，务必轻仓、严设止损。"


def answer_fast(question: str, context: str = "") -> dict:
    """快速通道: 个股~20-40s / 板块走结构化选票 / 其余回退多轮循环。"""
    from .config import get_llm as _get_llm
    client = _get_llm(MODEL)
    t0 = time.time()
    gap = _gap_notice(question)      # 数据缺口硬指令, 注入 context 覆盖所有下游路径
    if gap:
        context = (context + gap).strip()
    route = _route(client, question)
    if route.get("type") == "board_pick":
        return answer_board_pick(question, route.get("count") or 3, context)
    if route.get("type") == "ranking":
        # sector 可为空 = 全市场热点模式("结合热点资金选N只"没点名板块)
        _pm = route.get("price_max")
        _pm = float(_pm) if isinstance(_pm, (int, float)) and _pm > 0 else None
        return answer_ranking(route.get("sector") or "", question,
                              route.get("count") or 5, context, price_max=_pm)
    if route.get("type") == "sector" and route.get("sector"):
        return answer_sector(route["sector"], question, context)
    stocks = route.get("stocks") or []
    if route.get("type") != "stock" or len(stocks) != 1:
        r = answer(question, context)
        r["path"] = "agentic"
        return r
    code = _resolve_code(stocks[0])
    if not code:
        r = answer(question, context)
        r["path"] = "agentic"
        return r
    # 标准数据包并行预取
    reg = _get_registry()
    bundle_tools = list(_FAST_BUNDLE)
    if any(k in question for k in ("连板", "涨停", "妖股", "打板")):
        bundle_tools.append("get_limit_up_pool")   # 连板类问题挂涨停池(打板框架数据)
    pool = ThreadPoolExecutor(max_workers=len(bundle_tools))
    futs = {t: pool.submit(_run_tool, t, {"stock_code": code}) for t in bundle_tools}
    bundle, trace = {}, []
    for t in bundle_tools:
        try:
            res = futs[t].result(timeout=TOOL_TIMEOUT_S)
        except Exception as e:
            res = {"ok": False, "error": {"message": str(e)[:120]}}
        bundle[t] = res
        trace.append({"round": 1, "tool": t, "params": {"stock_code": code}, "ok": bool(res.get("ok"))})
    pool.shutdown(wait=False, cancel_futures=True)
    t_data = time.time()
    data_text = "\n".join(f"[{t}]\n{_shrink(r)}" for t, r in bundle.items())
    user = (f"[群友提问]\n{question}\n\n[已实时采集的数据(直接引用, 无需再调工具)]\n{data_text}\n\n"
            "基于以上数据直接输出最终回答。快速模式: 篇幅压到250-450字, 结论/硬数据/操作三段即可。")
    if context:
        user = f"[会话上下文]\n{context}\n\n{user}"
    resp = client.chat.completions.create(
        model=MODEL, temperature=0.4, max_tokens=900, timeout=120,
        messages=[{"role": "system", "content": _build_system()},
                  {"role": "user", "content": user}],
    )
    logger.info("[fast] route+data=%.1fs llm=%.1fs", t_data - t0, time.time() - t_data)
    ans = (resp.choices[0].message.content or "").strip()
    mf = bundle.get("get_realtime_moneyflow", {})
    nm = (mf.get("data", {}).get("today_realtime", {}) or {}).get("name", "") if mf.get("ok") else ""
    ans = _enforce_st_warning(ans, nm)   # ST 退市警示硬兜底
    return {"answer": scrub_compliance(ans), "tool_trace": trace, "rounds": 1, "path": "fast"}


if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s %(message)s")
    q = " ".join(sys.argv[1:]) or "金钼股份现在怎么样, 能买吗"
    r = answer_fast(q)
    print("\n" + "=" * 60)
    print(f"[{r['rounds']}轮 | {len(r['tool_trace'])}次工具调用]")
    for t in r["tool_trace"]:
        print(f"  r{t['round']} {t['tool']}({json.dumps(t['params'], ensure_ascii=False)}) ok={t['ok']}")
    print("=" * 60 + "\n")
    print(r["answer"])
