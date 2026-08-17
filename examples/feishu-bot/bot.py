# -*- coding: utf-8 -*-
"""飞书群机器人接入 xiaocai-stock-ai 示例。

功能:
- 群里 @机器人 触发问答, 私聊直接对话
- ACK 秒回, 引擎异步返回
- 15 分钟会话记忆(无需引用回复即可追问)
- 单人限频(同问题 90s 去重, 每分钟 6 问)

依赖:
    pip install lark-oapi httpx

配置(config.json, 参考 config.example.json):
    APP_ID / APP_SECRET / XIAOCAI_API_ENDPOINT

启动:
    python3 bot.py

生产建议用 PM2/systemd 管理常驻。
"""
import json
import os
import re
import sys
import threading
import time
import traceback
from concurrent.futures import ThreadPoolExecutor

import httpx
import lark_oapi as lark
from lark_oapi.api.im.v1 import P2ImMessageReceiveV1

# ---------- 配置 ----------
_CFG_PATH = os.path.join(os.path.dirname(__file__), "config.json")
if not os.path.exists(_CFG_PATH):
    print(f"缺少配置文件: {_CFG_PATH} (参考 config.example.json)"); sys.exit(1)
CFG = json.load(open(_CFG_PATH))
APP_ID = CFG["APP_ID"]
APP_SECRET = CFG["APP_SECRET"]
API_ENDPOINT = CFG.get("XIAOCAI_API_ENDPOINT", "https://xiaocai.sque.site/api/ask")
API_KEY = CFG.get("XIAOCAI_API_KEY", "")
ACK_REPLY = CFG.get("ACK_REPLY", "好的，马上分析")
ERROR_REPLY = CFG.get("ERROR_REPLY", "分析出了点问题, 稍后重试~")
DISCLAIMER = CFG.get("DISCLAIMER", "\n\n---\n数据来自公开市场数据 | AI 生成, 仅供研究参考, 不构成投资建议")

# ---------- 状态 ----------
_processed: set = set()
_MAX_CACHE = 500
_dedup: dict = {}   # (sender, text) → ts
_recent: dict = {}  # sender → [ts,...]
_DEDUP_S = 90
_RATE_WINDOW_S = 60
_RATE_MAX = 6

_SESSION_TTL_S = 15 * 60
_last_qa: dict = {}   # sender → (q, a, ts)

_ENGINE_WORKERS = 6
_engine_pool = ThreadPoolExecutor(max_workers=_ENGINE_WORKERS)
_inflight = {"n": 0}
_lock = threading.Lock()

_token_cache = {"token": "", "expire": 0}
_BOT_OPEN_ID = ""


# ---------- 飞书 SDK ----------
def _get_token() -> str:
    now = time.time()
    if _token_cache["token"] and _token_cache["expire"] > now + 60:
        return _token_cache["token"]
    r = httpx.post(
        "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal",
        json={"app_id": APP_ID, "app_secret": APP_SECRET}, timeout=10,
    ).json()
    _token_cache["token"] = r["tenant_access_token"]
    _token_cache["expire"] = now + r.get("expire", 7200)
    return _token_cache["token"]


def _get_bot_open_id() -> str:
    global _BOT_OPEN_ID
    if _BOT_OPEN_ID:
        return _BOT_OPEN_ID
    try:
        r = httpx.get("https://open.feishu.cn/open-apis/bot/v3/info",
                      headers={"Authorization": f"Bearer {_get_token()}"}, timeout=10)
        _BOT_OPEN_ID = ((r.json().get("bot") or {}).get("open_id")) or ""
    except Exception:
        traceback.print_exc()
    return _BOT_OPEN_ID


def _reply_text(msg_id: str, text: str):
    try:
        httpx.post(
            f"https://open.feishu.cn/open-apis/im/v1/messages/{msg_id}/reply",
            headers={"Authorization": f"Bearer {_get_token()}", "Content-Type": "application/json"},
            json={"msg_type": "text", "content": json.dumps({"text": text})},
            timeout=10,
        )
    except Exception:
        traceback.print_exc()


def _reply_rich(msg_id: str, text: str):
    """回复带免责尾注的富文本。"""
    try:
        content = json.dumps({
            "zh_cn": {"title": "", "content": [[{"tag": "text", "text": text + DISCLAIMER}]]}
        })
        httpx.post(
            f"https://open.feishu.cn/open-apis/im/v1/messages/{msg_id}/reply",
            headers={"Authorization": f"Bearer {_get_token()}", "Content-Type": "application/json"},
            json={"msg_type": "post", "content": content},
            timeout=15,
        )
    except Exception:
        traceback.print_exc()
        _reply_text(msg_id, text[:500] + DISCLAIMER)


# ---------- 限频/会话记忆 ----------
def _rate_check(sender: str, text: str, now: float):
    if not sender:
        return None
    dk = (sender, text)
    if now - _dedup.get(dk, 0) < _DEDUP_S:
        return "去重"
    _dedup[dk] = now
    hist = [t for t in _recent.get(sender, []) if now - t < _RATE_WINDOW_S]
    if len(hist) >= _RATE_MAX:
        return "限流"
    hist.append(now); _recent[sender] = hist
    return None


def _session_ctx(sender: str) -> str:
    it = _last_qa.get(sender)
    if not it or time.time() - it[2] > _SESSION_TTL_S:
        return ""
    q, a, _ = it
    return f"该用户最近一轮问答(如是追问作上下文, 否则忽略):\n[用户] {q[:300]}\n[回复] {a[:800]}"


def _session_store(sender: str, q: str, a: str):
    if not sender:
        return
    _last_qa[sender] = (q, a, time.time())


# ---------- 引擎调用 ----------
def _call_engine(question: str, context: str) -> str:
    """POST 到 xiaocai HTTP API, 返回 answer 字符串。"""
    try:
        headers = {"Content-Type": "application/json"}
        if API_KEY:
            headers["X-API-Key"] = API_KEY
        r = httpx.post(API_ENDPOINT, headers=headers,
                       json={"question": question, "context": context}, timeout=180)
        r.raise_for_status()
        return r.json().get("answer", "") or ""
    except Exception as e:
        traceback.print_exc()
        return f"引擎调用失败: {str(e)[:100]}"


# ---------- 消息处理 ----------
def _handle(msg_id: str, question: str, sender: str):
    try:
        ctx = _session_ctx(sender)
        answer = _call_engine(question, ctx)
        if answer:
            _session_store(sender, question, answer)
            _reply_rich(msg_id, answer)
        else:
            _reply_text(msg_id, ERROR_REPLY)
    except Exception:
        traceback.print_exc()
        _reply_text(msg_id, ERROR_REPLY)


def on_message(data: P2ImMessageReceiveV1):
    event = data.event
    if not event or not event.message:
        return
    msg = event.message
    msg_id = msg.message_id or ""
    if msg.message_type != "text" or msg_id in _processed:
        return
    _processed.add(msg_id)
    if len(_processed) > _MAX_CACHE:
        for r in list(_processed)[: _MAX_CACHE // 2]:
            _processed.discard(r)

    # 群聊必须真 @ 本 bot; 私聊无需
    chat_type = getattr(msg, "chat_type", "") or ""
    if chat_type == "group":
        mentions = getattr(msg, "mentions", None) or []
        bot_oid = _get_bot_open_id()
        mentioned = []
        for m in mentions:
            try: mentioned.append(m.id.open_id or "")
            except AttributeError: continue
        if bot_oid and bot_oid not in mentioned:
            return
        if not bot_oid and not mentions:
            return

    try:
        text = json.loads(msg.content or "{}").get("text", "").strip()
    except (json.JSONDecodeError, AttributeError):
        return
    text = re.sub(r"@\S+\s*", "", text).strip()
    if not text:
        return

    sender = ""
    try:
        sender = event.sender.sender_id.open_id or ""
    except AttributeError:
        pass

    blocked = _rate_check(sender, text, time.time())
    if blocked:
        print(f"[{blocked}] {sender[-8:]} 忽略: {text[:30]}")
        return

    print(f"[收到] {text} (msg_id={msg_id})")

    with _lock:
        _inflight["n"] += 1
        ahead = max(0, _inflight["n"] - 1 - _ENGINE_WORKERS)
    ack = ACK_REPLY if ahead == 0 else f"{ACK_REPLY}(前面还排着 {ahead} 个)"
    threading.Thread(target=_reply_text, args=(msg_id, ack), daemon=True).start()

    def _job():
        try:
            _handle(msg_id, text, sender)
        finally:
            with _lock:
                _inflight["n"] = max(0, _inflight["n"] - 1)

    _engine_pool.submit(_job)


def main():
    _get_bot_open_id()
    print(f"[feishu-bot] 启动, 引擎: {API_ENDPOINT}, bot_open_id: {'已获取' if _BOT_OPEN_ID else '获取失败'}")
    handler = (
        lark.EventDispatcherHandler.builder("", "")
        .register_p2_im_message_receive_v1(on_message)
        .build()
    )
    client = lark.ws.Client(
        app_id=APP_ID, app_secret=APP_SECRET,
        event_handler=handler, log_level=lark.LogLevel.INFO,
        auto_reconnect=True,
    )
    client.start()


if __name__ == "__main__":
    main()
