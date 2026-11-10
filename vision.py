"""图片识别：调用智谱 GLM-4V-Flash 视觉模型，识别产品，供后续合规/关税测算。

设计原则：
- 这里只负责「描述图片里的产品」，**不猜 HS 编码**——HS 归类交给后端工具
  tools/tariff_db.py（真实关键词→HS 映射）和 tools/compliance.py（真实认证库），
  避免模型乱编编码（曾经把保温杯编成 6913/9018、塑料瓶编成 39206500）。
- 上传图先压缩（PIL：转 RGB、缩到最长边 ≤1024、JPEG），大图/PNG/透明底/webp 都压成小 JPEG，
  避免「图太大」超限或识别跑偏。
"""
import base64
import io
import os

from dotenv import load_dotenv
from openai import OpenAI
from PIL import Image

load_dotenv()

GLM_BASE_URL = "https://open.bigmodel.cn/api/paas/v4"
GLM_MODEL = "glm-4v-flash"
MAX_EDGE = 1024          # 压缩后最长边（像素）
JPEG_QUALITY = 82

_PROMPT = (
    "你是跨境电商产品识别助手。请仔细观察图片，用中文严格按以下格式逐行输出，"
    "每行只写答案，不要解释、不要给 HS 编码（海关编码由后端工具查询，你只负责描述产品）：\n"
    "产品类型：\n"
    "主要材质：\n"
    "是否电动/电子、是否含锂电池：\n"
    "主要用途：\n"
    "补充特征（品牌/型号/特殊结构等）：\n"
    "注意：若图片是电商页面截图，请聚焦页面主商品图来识别；"
    "若图片里没有明确产品（纯文字/二维码/文档等），产品类型写「无法识别」。"
)


def compress_image(image_bytes: bytes) -> bytes:
    """压缩图片为小 JPEG（RGB、最长边 ≤MAX_EDGE），返回 JPEG 字节。大图/PNG/透明底都适用。"""
    im = Image.open(io.BytesIO(image_bytes))
    if im.mode not in ("RGB", "L"):
        im = im.convert("RGB")
    im.thumbnail((MAX_EDGE, MAX_EDGE))
    buf = io.BytesIO()
    im.save(buf, "JPEG", quality=JPEG_QUALITY)
    return buf.getvalue()


def identify_product(image_bytes: bytes, mime: str = "image/jpeg"):
    """返回 {'description': ...} 或 {'error': ...}。图片自动压缩后发，格式统一 JPEG。"""
    key = os.getenv("GLM_API_KEY", "")
    if not key:
        return {"error": "未配置 GLM_API_KEY（智谱视觉模型密钥）"}
    try:
        image_bytes = compress_image(image_bytes)
    except Exception as e:  # noqa: BLE001
        return {"error": f"图片读取失败：{type(e).__name__}: {e}"}
    b64 = base64.b64encode(image_bytes).decode("ascii")
    client = OpenAI(base_url=GLM_BASE_URL, api_key=key, timeout=60.0)
    try:
        resp = client.chat.completions.create(
            model=GLM_MODEL,
            messages=[{
                "role": "user",
                "content": [
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}},
                    {"type": "text", "text": _PROMPT},
                ],
            }],
            max_tokens=600,
        )
        return {"description": resp.choices[0].message.content}
    except Exception as e:  # noqa: BLE001
        return {"error": f"图片识别失败：{type(e).__name__}: {e}"}
