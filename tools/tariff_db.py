"""HS 税率查询层（SQLite），数据库缺失时自动重建。"""
import os
import sqlite3

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "tariff.db")

_COLS = ["hs_code", "country", "description", "mfn_pct", "section301_pct",
         "ieepa_pct", "forced_labor301_pct", "effective_pct", "source", "note", "updated_at"]


def _ensure_db():
    """首次运行（如云端全新克隆）时自动用 seed 数据建库。"""
    if not os.path.exists(DB_PATH):
        from data.seed_tariff import build
        build()


def product_to_hs(product: str):
    _ensure_db()
    conn = sqlite3.connect(DB_PATH)
    row = conn.execute("SELECT hs_code FROM product_hs_map WHERE product = ?", (product,)).fetchone()
    conn.close()
    return row[0] if row else None


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
                "message": "该产品暂无 HS 编码映射（当前仅覆盖：儿童声光电动早教玩具）"}
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
            "最惠国MFN": t["mfn_pct"],
            "存量301(清单1-4A)": t["section301_pct"],
            "IEEPA(已失效)": t["ieepa_pct"],
            "新301(强迫劳动)": t["forced_labor301_pct"],
        },
        "effective_pct": t["effective_pct"],
        "source": t["source"],
        "note": t["note"],
        "updated_at": t["updated_at"],
    }
