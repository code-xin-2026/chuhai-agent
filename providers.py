"""LLM 供应商配置 + 自动 failover。

优先级（按列表顺序）：JoyCode（大赛免费，拿到 key 后自动成为主力）
                        → DeepSeek（当前主力，OpenAI 兼容）
                        → tokenrhythm（备胎）

配置来源优先级：Streamlit Secrets > 环境变量(.env) > 默认值。
某个供应商额度用尽(429)/报错/超时 → 自动切下一个，评委无感知。
"""
import os
import time

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

try:
    import streamlit as st
except Exception:  # noqa: BLE001
    st = None


def _cfg(key, default=""):
    """读取配置：Streamlit Secrets > 环境变量 > 默认值。"""
    if st is not None:
        try:
            v = st.secrets.get(key)
            if v:
                return v
        except Exception:  # noqa: BLE001
            pass
    return os.getenv(key, default)


PROVIDERS = [
    {
        "name": "JoyCode",
        "base_url": _cfg("JOYCODE_BASE_URL", "https://modelservice.jdcloud.com/coding/openai/v1"),
        "api_key": _cfg("JOYCODE_API_KEY", ""),
        "model": _cfg("JOYCODE_MODEL", ""),
    },
    {
        "name": "DeepSeek",
        "base_url": _cfg("DEEPSEEK_BASE_URL", "https://api.deepseek.com"),
        "api_key": _cfg("DEEPSEEK_API_KEY", ""),
        "model": _cfg("DEEPSEEK_MODEL", "deepseek-chat"),
    },
    {
        "name": "tokenrhythm",
        "base_url": _cfg("TOKENRHYTHM_BASE_URL", "https://tokenrhythm.studio/v1"),
        "api_key": _cfg("TOKENRHYTHM_API_KEY", ""),
        "model": _cfg("TOKENRHYTHM_MODEL", "pro-0813"),
    },
]


def _make_client(p):
    return OpenAI(base_url=p["base_url"], api_key=p["api_key"], timeout=120.0)


def chat_completion(messages, tools=None, temperature=0.3, retries_per_provider=2):
    """依次尝试每个供应商，返回第一个成功的响应；全部失败则抛异常。"""
    errors = []
    for p in PROVIDERS:
        if not p["api_key"] or not p["model"]:
            errors.append(f"{p['name']}: 未配置，跳过")
            continue
        for attempt in range(retries_per_provider + 1):
            try:
                client = _make_client(p)
                kwargs = {"model": p["model"], "messages": messages, "temperature": temperature}
                if tools:
                    kwargs["tools"] = tools
                resp = client.chat.completions.create(**kwargs)
                resp._provider_name = p["name"]
                return resp
            except Exception as e:  # noqa: BLE001
                errors.append(f"{p['name']}(第{attempt + 1}次): {type(e).__name__}: {e}")
                if attempt < retries_per_provider:
                    time.sleep(1.5 * (attempt + 1))  # 退避重试，抗网络抖动
    raise RuntimeError("所有供应商均调用失败：\n" + "\n".join(errors))


def stream_completion(messages, tools=None, temperature=0.3):
    """流式调用，返回 (stream_iterator, provider_name)。用于最终回答的逐字输出。"""
    errors = []
    for p in PROVIDERS:
        if not p["api_key"] or not p["model"]:
            continue
        try:
            client = _make_client(p)
            kwargs = {"model": p["model"], "messages": messages, "temperature": temperature}
            if tools:
                kwargs["tools"] = tools
            stream = client.chat.completions.create(**kwargs, stream=True)
            return stream, p["name"]
        except Exception as e:  # noqa: BLE001
            errors.append(f"{p['name']}: {type(e).__name__}: {e}")
    raise RuntimeError("所有供应商流式调用失败：\n" + "\n".join(errors))
