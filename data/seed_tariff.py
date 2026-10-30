"""初始化/更新 HS 税率 SQLite 数据库（真实数据，带来源与更新时间）。

运行：python seed_tariff.py

数据来源（截至 2026-10-29）：
- USITC HTS 2026 Rev（MFN 基础税率）
- USTR Section 301 关税行动通知（存量301清单 + 新301强迫劳动措施）
- 中美经贸磋商公开信息（300亿对等降税共识）

重要说明：美国对华关税为「分层叠加」结构，且 2026 年经历
IEEPA 违宪失效(02-24) → 122条款(07-24到期) → 新301(强迫劳动,07-24起) 的替换，
有效税率会随政策变动，必须以 updated_at 为准并定期更新。
"""
import os
import sqlite3

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tariff.db")

SCHEMA = """
CREATE TABLE IF NOT EXISTS tariff_rates (
    hs_code TEXT NOT NULL,
    country TEXT NOT NULL,
    description TEXT,
    mfn_pct REAL NOT NULL DEFAULT 0,             -- 最惠国基础税率
    section301_pct REAL NOT NULL DEFAULT 0,      -- 存量301(清单1-4A)
    ieepa_pct REAL NOT NULL DEFAULT 0,           -- IEEPA(已判违宪失效)
    forced_labor301_pct REAL NOT NULL DEFAULT 0, -- 新301(强迫劳动,2026-07-24起)
    effective_pct REAL NOT NULL,                 -- 合计有效税率
    source TEXT,
    note TEXT,
    updated_at TEXT,
    PRIMARY KEY (hs_code, country)
);
CREATE TABLE IF NOT EXISTS product_hs_map (
    product TEXT PRIMARY KEY,
    hs_code TEXT NOT NULL
);
"""

ROWS = [
    {
        "hs_code": "9503.00.00",
        "country": "美国",
        "description": "玩具（三轮车、玩偶、拼图、电动/声光玩具等；3-12岁及Other）",
        "mfn_pct": 0.0,
        "section301_pct": 0.0,
        "ieepa_pct": 0.0,
        "forced_labor301_pct": 12.5,
        "effective_pct": 12.5,
        "source": "USITC HTS 2026 Rev + USTR Section 301 通知",
        "note": "玩具属301清单4B(从未激活)→存量301为0；IEEPA关税2026-02-24判违宪失效；2026-07-24起新301(强迫劳动)对华12.5%，9503是否在豁免清单需以USTR附件为准；中美300亿对等降税清单含玩具、尚未生效，若生效附加税将归零。",
        "updated_at": "2026-10-29",
    },
]

PRODUCT_MAP = [
    ("儿童声光电动早教玩具", "9503.00.00"),
]


def build():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.executescript(SCHEMA)
    for r in ROWS:
        conn.execute(
            "INSERT OR REPLACE INTO tariff_rates VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            (r["hs_code"], r["country"], r["description"], r["mfn_pct"], r["section301_pct"],
             r["ieepa_pct"], r["forced_labor301_pct"], r["effective_pct"],
             r["source"], r["note"], r["updated_at"]),
        )
    for product, hs in PRODUCT_MAP:
        conn.execute("INSERT OR REPLACE INTO product_hs_map VALUES (?,?)", (product, hs))
    conn.commit()
    conn.close()
    print(f"OK: {DB_PATH}（{len(ROWS)} 条税率，{len(PRODUCT_MAP)} 条产品映射）")


if __name__ == "__main__":
    build()
