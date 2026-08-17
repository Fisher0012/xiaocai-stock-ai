# -*- coding: utf-8 -*-
"""LLM 供应商适配 + 环境变量加载 (SPEC §2.1 引擎层)

支持: DeepSeek 官方 + OpenAI 兼容协议(Kimi/通义/豆包/DeepSeek 均实现了此协议)。
配置来自环境变量, 见 .env.example。
"""
import os
from functools import lru_cache

# 只在需要时导入 OpenAI SDK, 避免 import 时 crash 环境未配置的用户
_client_cache = {}


def _load_dotenv_once():
    """轻量加载 .env(避免强依赖 python-dotenv)"""
    if getattr(_load_dotenv_once, "_done", False):
        return
    for path in (".env", os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")):
        if os.path.exists(path):
            for line in open(path):
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    if k.strip() and k.strip() not in os.environ:
                        os.environ[k.strip()] = v.strip().strip('"').strip("'")
    _load_dotenv_once._done = True


def _resolve_provider(model: str):
    """按 model 前缀路由 (base_url, api_key_env, provider_name)。"""
    m = (model or "").lower()
    if m.startswith("deepseek"):
        return ("https://api.deepseek.com/v1",
                os.environ.get("DEEPSEEK_BASE_URL") or "https://api.deepseek.com/v1",
                "DEEPSEEK_API_KEY", "deepseek")
    # OpenAI 兼容协议 (openai/kimi/moonshot/qwen/doubao/glm 等)
    base = os.environ.get("OPENAI_BASE_URL") or "https://api.openai.com/v1"
    key_env = "OPENAI_API_KEY"
    return (base, base, key_env, "openai-compat")


def get_llm(model: str = None):
    """按 model 返回对应 provider 的 OpenAI SDK client(缓存)。
    model 为空时用 LLM_MODEL 环境变量或默认 'deepseek-chat'。"""
    _load_dotenv_once()
    model = model or os.environ.get("LLM_MODEL", "deepseek-chat")
    _, base_url, key_env, provider = _resolve_provider(model)
    if provider not in _client_cache:
        api_key = os.environ.get(key_env, "")
        if not api_key:
            raise RuntimeError(
                f"未配置 {key_env} 环境变量。请在 .env 或环境中设置 (或换一个 model 前缀走另一供应商)。"
            )
        try:
            from openai import OpenAI
        except ImportError:
            raise RuntimeError("需要安装 openai SDK: pip install openai>=1.0")
        _client_cache[provider] = OpenAI(api_key=api_key, base_url=base_url)
    return _client_cache[provider]


@lru_cache(maxsize=1)
def get_default_model() -> str:
    _load_dotenv_once()
    return os.environ.get("LLM_MODEL", "deepseek-chat")


@lru_cache(maxsize=1)
def get_news_endpoint():
    """xiaocai 官方消息面服务(可选). 未配置=消息面能力关闭, 引擎降级。"""
    _load_dotenv_once()
    ep = os.environ.get("XIAOCAI_NEWS_ENDPOINT", "").rstrip("/")
    key = os.environ.get("XIAOCAI_NEWS_API_KEY", "")
    return (ep, key) if ep else (None, None)
