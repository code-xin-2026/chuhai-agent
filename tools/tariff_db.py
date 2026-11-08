"""HS 税率查询层（SQLite），数据库缺失时自动重建。"""
import os
import sqlite3

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "tariff.db")

_COLS = ["hs_code", "country", "description", "mfn_pct", "china_surcharge_pct",
         "effective_pct", "source", "note", "updated_at"]

# 关键词 → HS（产品名命中任一子串即映射；顺序即优先级：玩具类排最前，安全优先）
_KEYWORD_HS = [
    ("玩具", "9503.00.00"), ("儿童", "9503.00.00"), ("早教", "9503.00.00"), ("积木", "9503.00.00"),
    ("不锈钢", "7323.93.00"), ("保温杯", "7323.93.00"), ("水杯", "7323.93.00"),
    ("餐具", "7323.93.00"), ("厨具", "7323.93.00"), ("食品接触", "7323.93.00"),
    ("充电宝", "8507.60.00"), ("移动电源", "8507.60.00"), ("电池", "8507.60.00"), ("锂电", "8507.60.00"),
    ("耳机", "8518.30.00"), ("耳塞", "8518.30.00"),
    ("音箱", "8518.22.00"), ("音响", "8518.22.00"), ("扬声器", "8518.22.00"),
]


def _ensure_db():
    """首次运行（如云端全新克隆）时自动用 seed 数据建库。"""
    if not os.path.exists(DB_PATH):
        from data.seed_tariff import build
        build()


def product_to_hs(product: str):
    """产品名 → HS 编码：先精确匹配 product_hs_map，再关键词匹配。"""
    _ensure_db()
    conn = sqlite3.connect(DB_PATH)
    row = conn.execute("SELECT hs_code FROM product_hs_map WHERE product = ?", (product,)).fetchone()
    conn.close()
    if row:
        return row[0]
    for kw, hs in _KEYWORD_HS:
        if kw in product:
            return hs
    return None


def get_tariff(hs_code: str, country: str):
    _ensure_db()
    conn = sqlite3.connect(DB_PATH)
    row = conn.execute(
        "SELECT * FROM tariff_rates WHERE hs_code = ? AND country = ?", (hs_code, country)
    ).fetchone()
    conn.close()
    return dict(zip(_COLS, row)) if row else None


def query_tariff(product: str, destination: str = "美国"):
    """按产品名查当前有效关税（先映射 HS 编码，再查分层税率）。"""
    hs = product_to_hs(product)
    if hs is None:
        return {"product": product, "in_scope": False,
                "message": "该产品暂无 HS 编码映射（当前覆盖：玩具/不锈钢食品接触容器/锂电池充电宝/蓝牙耳机音箱）"}
    t = get_tariff(hs, destination)
    if t is None:
        return {"product": product, "hs_code": hs, "destination": destination, "in_scope": False,
                "message": f"HS {hs} 在 {destination} 暂无税率数据"}
    return {
        "product": product,
        "hs_code": hs,
        "destination": destination,
        "in_scope": True,
        "description": t["description"],
        "rates": {
            "基础关税(稳定)": t["mfn_pct"],
            "附加税(政策波动)": t["china_surcharge_pct"],
        },
        "effective_pct": t["effective_pct"],
        "source": t["source"],
        "note": t["note"],
        "updated_at": t["updated_at"],
    }
