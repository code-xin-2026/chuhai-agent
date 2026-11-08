"""图片识别：调用智谱 GLM-4V-Flash 视觉模型，识别产品并提取 HS 归类所需信息。"""
import base64
import os

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

GLM_BASE_URL = "https://open.bigmodel.cn/api/paas/v4"
GLM_MODEL = "glm-4v-flash"

_PROMPT = (
    "请识别图片中的产品，用于后续出口美国的海关归类(HS编码)和合规测算。"
    "请用中文严格按以下格式输出（不知道的写'未知'）：\n"
    "产品类型：\n"
    "主要材质：\n"
    "是否电动/电子、是否含锂电池：\n"
    "主要用途：\n"
    "可能对应的HS编码大类：(如玩具9503、锂电池8507、蓝牙耳机8518等；不确定写'需人工确认')"
)


def identify_product(image_bytes: bytes, mime: str = "image/jpeg"):
    """返回 {'description': ...} 或 {'error': ...}。"""
    key = os.getenv("GLM_API_KEY", "")
    if not key:
        return {"error": "未配置 GLM_API_KEY（智谱视觉模型密钥）"}
    b64 = base64.b64encode(image_bytes).decode("ascii")
    client = OpenAI(base_url=GLM_BASE_URL, api_key=key, timeout=60.0)
    try:
        resp = client.chat.completions.create(
            model=GLM_MODEL,
            messages=[{
                "role": "user",
                "content": [
                    {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{b64}"}},
                    {"type": "text", "text": _PROMPT},
                ],
            }],
            max_tokens=600,
        )
        return {"description": resp.choices[0].message.content}
    except Exception as e:  # noqa: BLE001
        return {"error": f"图片识别失败：{type(e).__name__}: {e}"}
