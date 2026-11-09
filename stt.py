"""语音识别（STT）：浏览器录音 → 文字，喂给大模型对话。

默认接入阿里云百炼（DashScope）Qwen3-ASR：国内可用、中文识别好、有免费额度。
OpenAI 兼容接口，配置优先级 Streamlit Secrets > 环境变量(.env)：

    ASR_API_KEY   百炼 API Key（sk-...，必填）
    ASR_BASE_URL  默认 https://dashscope.aliyuncs.com/compatible-mode/v1
    ASR_MODEL     默认 qwen3-asr-flash

想换成其它 OpenAI 兼容 ASR（硅基流动 SenseVoiceSmall、new-api whisper-1 等）：
改 ASR_MODEL 即可——非 qwen 模型会自动走标准 /audio/transcriptions 接口，无需改代码。
"""
import base64
import os

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


ASR_BASE_URL = _cfg("ASR_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1")
ASR_MODEL = _cfg("ASR_MODEL", "qwen3-asr-flash")


def _is_qwen_asr(model: str) -> bool:
    """千问 ASR 用 chat/completions + input_audio；其余用标准 audio/transcriptions。"""
    return "asr" in model.lower() or model.lower().startswith("qwen")


def transcribe(audio_bytes: bytes, mime: str = "audio/wav"):
    """把录音字节转成文字。返回 {'text': ...} 或 {'error': ...}。"""
    key = _cfg("ASR_API_KEY", "")
    if not key:
        return {"error": "未配置语音识别密钥 ASR_API_KEY（阿里云百炼，有免费额度）。详见 README「语音输入」一节。"}
    client = OpenAI(base_url=ASR_BASE_URL, api_key=key, timeout=120.0)
    try:
        if _is_qwen_asr(ASR_MODEL):
            # 千问 ASR：OpenAI 兼容 chat/completions + input_audio（base64 data URI）
            b64 = base64.b64encode(audio_bytes).decode("ascii")
            resp = client.chat.completions.create(
                model=ASR_MODEL,
                messages=[{
                    "role": "user",
                    "content": [{
                        "type": "input_audio",
                        "input_audio": {"data": f"data:{mime};base64,{b64}"},
                    }],
                }],
            )
            text = resp.choices[0].message.content
        else:
            # 标准 OpenAI /audio/transcriptions（whisper-1、SenseVoice 等）
            ext = {"audio/wav": "wav", "audio/mp3": "mp3", "audio/m4a": "m4a",
                   "audio/webm": "webm", "audio/ogg": "ogg"}.get(mime, "wav")
            resp = client.audio.transcriptions.create(
                model=ASR_MODEL,
                file=(f"audio.{ext}", audio_bytes, mime),
            )
            text = resp.text
        text = (text or "").strip()
        if not text:
            return {"error": "未识别到语音内容，请靠近麦克风、说清楚后重试。"}
        return {"text": text}
    except Exception as e:  # noqa: BLE001
        return {"error": f"语音识别失败：{type(e).__name__}: {e}"}
