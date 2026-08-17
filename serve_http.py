# -*- coding: utf-8 -*-
"""HTTP API 服务 (SPEC §4)

主打形态。用 FastAPI 暴露引擎为 HTTP 接口, 供任何平台调用
(Coze/Kimi/Codex/飞书 bot/自建 agent)。

启动:
    python3 serve_http.py                          # 开发模式
    uvicorn serve_http:app --host 0.0.0.0 --port 8080  # 生产
    docker-compose up -d                           # 一键起

端点见 openapi.yaml。
"""
import logging
import os
import time
from typing import Optional

from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from core.config import _load_dotenv_once, get_default_model
from core.engine import (
    answer,
    answer_board_pick,
    answer_fast,
    answer_ranking,
    answer_sector,
)

logger = logging.getLogger("xiaocai.http")
_load_dotenv_once()

VERSION = "1.0.0"

# ============================================================
# 演示服务限流 (仅 XIAOCAI_DEMO_MODE=1 时启用, 自部署默认关闭)
# ============================================================
DEMO_MODE = os.environ.get("XIAOCAI_DEMO_MODE") == "1"
DEMO_DAILY_LIMIT = int(os.environ.get("XIAOCAI_DEMO_DAILY_LIMIT", "20"))
DEMO_MINUTE_LIMIT = int(os.environ.get("XIAOCAI_DEMO_MINUTE_LIMIT", "3"))

# 内存版限流(单进程够用; 集群部署换 Redis)。key = IP, value = [(ts, count_today), ...]
_rate_daily: dict = {}   # ip -> (date_str, count)
_rate_minute: dict = {}  # ip -> [ts, ts, ...]


def _rate_check(ip: str) -> Optional[str]:
    """demo 模式限流。返回错误消息(触发限流)或 None(放行)。"""
    if not DEMO_MODE:
        return None
    now = time.time()
    today = time.strftime("%Y-%m-%d")
    # 日限
    d = _rate_daily.get(ip)
    if d and d[0] == today:
        if d[1] >= DEMO_DAILY_LIMIT:
            return f"演示服务每日 {DEMO_DAILY_LIMIT} 次上限已到, 请自行部署实例(见 GitHub README)。"
        _rate_daily[ip] = (today, d[1] + 1)
    else:
        _rate_daily[ip] = (today, 1)
    # 分限
    hist = [t for t in _rate_minute.get(ip, []) if now - t < 60]
    if len(hist) >= DEMO_MINUTE_LIMIT:
        return f"演示服务每分钟 {DEMO_MINUTE_LIMIT} 次上限, 请稍后再试。"
    hist.append(now)
    _rate_minute[ip] = hist
    return None


# ============================================================
# FastAPI app
# ============================================================
app = FastAPI(
    title="xiaocai-stock-ai",
    description="A 股问答引擎 HTTP API - 数据取证 + 分析策略 + 敢下判断",
    version=VERSION,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 自部署可收紧
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)


class AskRequest(BaseModel):
    question: str = Field(..., description="用户问题, 如 '中际旭创能上吗' / '光通信怎么样'")
    context: str = Field("", description="可选上下文, 用于追问(带入上一轮问答)")
    persona: str = Field("default", description="人设 key, 目前仅 'default'; V2 支持自定义")
    options: dict = Field(default_factory=dict, description="{max_tokens, path_hint}")


class AskResponse(BaseModel):
    answer: str
    path: str
    meta: dict


class HealthResponse(BaseModel):
    ok: bool
    version: str
    model: str


# ============================================================
# 端点
# ============================================================


@app.get("/health", response_model=HealthResponse)
def health():
    return HealthResponse(ok=True, version=VERSION, model=get_default_model())


@app.get("/api/version")
def version():
    return {"version": VERSION, "model": get_default_model(), "demo_mode": DEMO_MODE}


def _client_ip(request: Request) -> str:
    xf = request.headers.get("x-forwarded-for", "")
    if xf:
        return xf.split(",")[0].strip()
    return (request.client.host if request.client else "unknown")


def _run(fn_key: str, req: AskRequest, request: Request) -> AskResponse:
    """通用执行器: 限流 → 路径分发 → 组装响应。"""
    ip = _client_ip(request)
    blocked = _rate_check(ip)
    if blocked:
        raise HTTPException(status_code=429, detail=blocked)

    t0 = time.time()
    ctx = req.context or ""
    try:
        if fn_key == "auto":
            hint = (req.options or {}).get("path_hint")
            if hint == "stock":
                r = answer(req.question, ctx)
            elif hint == "sector":
                r = answer_sector(req.question, req.question, ctx)  # sector_name = 从 question 抽取, engine 内会再路由
            elif hint == "ranking":
                r = answer_ranking("", req.question, count=5, context=ctx)
            elif hint == "board_pick":
                r = answer_board_pick(req.question, count=3, context=ctx)
            else:
                r = answer_fast(req.question, context=ctx)
        elif fn_key == "stock":
            r = answer_fast(req.question, context=ctx)  # answer_fast 会自动路由到 stock 路径
        elif fn_key == "sector":
            r = answer_sector(req.question, req.question, ctx)
        elif fn_key == "ranking":
            count = (req.options or {}).get("count", 5)
            price_max = (req.options or {}).get("price_max")
            r = answer_ranking("", req.question, count=count, context=ctx, price_max=price_max)
        elif fn_key == "board_pick":
            count = (req.options or {}).get("count", 3)
            r = answer_board_pick(req.question, count=count, context=ctx)
        else:
            raise HTTPException(status_code=400, detail=f"未知路径: {fn_key}")
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("engine failed")
        raise HTTPException(status_code=500, detail=f"引擎错误: {str(e)[:200]}")

    return AskResponse(
        answer=r.get("answer", ""),
        path=r.get("path", "?"),
        meta={
            "tool_trace": r.get("tool_trace") or [],
            "duration_s": round(time.time() - t0, 1),
            "engine_version": VERSION,
            "rounds": r.get("rounds", 1),
        },
    )


@app.post("/api/ask", response_model=AskResponse,
          summary="通用问答", description="自动路由到最合适的分析路径")
def api_ask(req: AskRequest, request: Request):
    return _run("auto", req, request)


@app.post("/api/stock", response_model=AskResponse,
          summary="个股研判", description="强制走个股快速通道(7 工具并行)")
def api_stock(req: AskRequest, request: Request):
    return _run("stock", req, request)


@app.post("/api/sector", response_model=AskResponse,
          summary="板块诊断", description="板块整体 + 龙头逐只点评")
def api_sector(req: AskRequest, request: Request):
    return _run("sector", req, request)


@app.post("/api/ranking", response_model=AskResponse,
          summary="选股", description="从候选池按短线买入价值排序, 诚实分级")
def api_ranking(req: AskRequest, request: Request):
    return _run("ranking", req, request)


@app.post("/api/board_pick", response_model=AskResponse,
          summary="选板块", description="从当日资金流入榜挑细分板块")
def api_board_pick(req: AskRequest, request: Request):
    return _run("board_pick", req, request)


@app.exception_handler(Exception)
async def catch_all(request: Request, exc: Exception):
    logger.exception("unhandled")
    return JSONResponse(status_code=500, content={"detail": f"服务异常: {str(exc)[:200]}"})


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("HTTP_PORT", "8080"))
    host = os.environ.get("HTTP_HOST", "0.0.0.0")
    logging.basicConfig(level=os.environ.get("LOG_LEVEL", "INFO"))
    print(f"[xiaocai-stock-ai] serving on http://{host}:{port} (demo_mode={DEMO_MODE})")
    uvicorn.run(app, host=host, port=port)
