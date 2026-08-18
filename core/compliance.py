"""输出合规清洗: 引擎返回给用户前统一走这一层, 实现"严禁买入/卖出/目标价字眼"的硬约束。

分层设计:
- BASE 层(默认开启, 不可关): 操作指令词软化 + 目标价→参考区间 + 煽动性形容词软化 + 内部字眼过滤 + 格式规整。
  这一层是 README 承诺的"合规底线", 无论用户跑在哪里都执行。
- STRICT 层(默认关, XIAOCAI_STRICT_COMPLIANCE=1 开启): 删股票代码 / 删带符号涨跌幅。
  这是给做小程序/公众号/金融资讯类平台的开发者用的, 避免被审核判成"股票行情屏"。
  个人本地用/Claude Code Skill 场景一般不需要开, 开了看不到代码/涨跌幅反而信息损失。
"""
from __future__ import annotations
import os
import re

# ------ BASE 层规则(默认开) ------

# 系统内部字眼(工具名/调用失败叙述)绝不能到用户面前 —— prompt 铁律之外的程序兜底
_INTERNAL_LEAK_RE = re.compile(
    r"(?:get|list|search)_[a-z_]{3,}|FinMCP|调用失败|未采集|未能采集|接口未返回|均未返回|"
    r"数据均未提供|亦未提供|返回空列表|返回\s*`?\[\]|未识别出任何成分股|标准化收录"
)

# ------ STRICT 层规则(env 开启) ------

_CODE_RE = re.compile(r"[（(]\s*\d{6}\.(?:SH|SZ|BJ)\s*[)）]|\b\d{6}\.(?:SH|SZ|BJ)\b", re.I)
_CODE_BARE_RE = re.compile(r"([一-龥A-Za-z])(\d{6})(?![\d亿万元户点倍％%])")
_SIGNED_PCT_RE = re.compile(r"[，、,]?\s*[+＋\-−]\s*\d+(?:\.\d+)?\s*%")
_DIR_PCT_RE = re.compile(r"(上涨|下跌|涨幅|跌幅|收涨|收跌|涨|跌)(?:超|约|达|近|逾|均|最高|最多|收于?|报)*\s*\d+(?:\.\d+)?\s*%")


def _scrub_internal(text: str) -> str:
    """按句删除泄漏系统内部细节的内容, 保留段内其他正常句子。"""
    if not text:
        return text
    out_lines = []
    for ln in text.split("\n"):
        if not _INTERNAL_LEAK_RE.search(ln):
            out_lines.append(ln)
            continue
        parts = re.split(r"(?<=[。;!?])", ln)
        kept = [p for p in parts if p and not _INTERNAL_LEAK_RE.search(p)]
        rebuilt = "".join(kept).strip()
        rebuilt = re.sub(r"（\s*）|\(\s*\)", "", rebuilt).strip("，,、;; ")
        if rebuilt:
            out_lines.append(rebuilt)
    return "\n".join(out_lines)


def _scrub_market_display(text: str) -> str:
    """STRICT 层: 去除股票行情屏判定特征。保留现价(元)/占比%/ROE等无向%/市值PE。"""
    if not text:
        return text
    text = _CODE_RE.sub("", text)
    text = _CODE_BARE_RE.sub(r"\1", text)
    text = _DIR_PCT_RE.sub(r"\1", text)
    text = _SIGNED_PCT_RE.sub("", text)
    text = re.sub(r"[（(][\s至到~～\-—、,,和]*[)）]", "", text)
    text = re.sub(r"[（(][、,\s]+", lambda m: m.group(0)[0], text)
    text = re.sub(r"[，、]{2,}", "，", text)
    text = re.sub(r"[，、]\s*。", "。", text)
    text = re.sub(r"([→↓↑←])[\s→↓↑←]*\1+", r"\1", text)
    text = re.sub(r"→\s*→", "→", text)
    text = re.sub(r"→\s*$", "", text, flags=re.MULTILINE)
    return text


def _normalize_md(text: str) -> str:
    """展示层格式规整: 粗体小标题与内容并回一行, 块间空一行, 收敛 3+ 连续空行。"""
    if not text:
        return text
    text = re.sub(r"(\*\*[^*\n]{1,50}\*\*[:：])[ \t]*\n+(?=[^\n#*\-])", r"\1", text)
    text = re.sub(r"([^\n])\n(?=\*\*[^*\n]{1,50}\*\*[:：])", r"\1\n\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text


def scrub_compliance(text: str) -> str:
    """引擎输出统一清洗入口。

    BASE 层永远执行, STRICT 层由 XIAOCAI_STRICT_COMPLIANCE=1 触发。
    """
    if not text:
        return text

    # BASE: 操作指令词软化 (README 承诺的"严禁买入/卖出/目标价字眼")
    text = text.replace("买入", "看好").replace("卖出", "看淡")

    # BASE: 看涨/看跌软化(品牌名"看涨跌"不误伤)
    text = re.sub(r"看涨(?!跌)", "偏强", text)
    text = re.sub(r"看跌", "偏弱", text)

    # BASE: 目标价 → 参考区间
    text = re.sub(r"(短期|中期|长期)?目标价", "参考区间", text)
    text = re.sub(r"(短期|中期|长期)目标(?!价)", r"\1参考", text)

    # BASE: 煽动性形容词软化(保留事实方向)
    text = re.sub(r"暴涨|大涨|飙升|狂涨|猛涨", "上涨", text)
    text = re.sub(r"暴跌|大跌|跳水|猛跌|重挫", "下跌", text)

    # BASE: 系统内部字眼句子级删除
    text = _scrub_internal(text)

    # STRICT: 需要 env 触发
    if os.environ.get("XIAOCAI_STRICT_COMPLIANCE", "0") == "1":
        text = _scrub_market_display(text)

    return _normalize_md(text)
