"""初始化/更新 HS 税率 SQLite 数据库（真实 MFN 基础税率 + 对华附加税，带来源与更新时间）。

运行：python seed_tariff.py

设计原则（可信度分级，解决「数字没底气」）：
- mfn_pct（最惠国基础税率）：稳定、可核实，来自 USITC HTS。
- china_surcharge_pct（对华附加税）：政策波动大（232/301/新301强迫劳动等），
  给出「当前已知值 + 构成」，但必须以 updated_at 为准并提示查最新。
- effective_pct = mfn + china_surcharge（中国原产合计有效税率）。

数据来源（截至 2026-10-29，USITC HTS 2026 Rev + USTR/CBP 公开通知）：
- 9503.00.00 玩具：MFN 0 + 新301(强迫劳动) 12.5%
- 7323.93.00 不锈钢厨具：MFN 2% + 232 钢铝衍生品 25%
- 8507.60.00 锂电池：MFN 3.4% + 301(25%) + 新301(强迫劳动 12.5%)
- 8518.30.00 耳机 / 8518.22.00 音箱：MFN 0 + 301(25%)
"""
import os
import sqlite3

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tariff.db")

SCHEMA = """
CREATE TABLE IF NOT EXISTS tariff_rates (
    hs_code TEXT NOT NULL,
    country TEXT NOT NULL,
    description TEXT,
    mfn_pct REAL NOT NULL DEFAULT 0,            -- 最惠国基础税率(稳定,可核实)
    china_surcharge_pct REAL NOT NULL DEFAULT 0, -- 对华附加税(政策波动,以最新为准)
    effective_pct REAL NOT NULL,                 -- 中国原产合计有效税率 = mfn + china_surcharge
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
        "description": "玩具（玩偶、拼图、电动/声光玩具等）",
        "mfn_pct": 0.0,
        "china_surcharge_pct": 12.5,
        "effective_pct": 12.5,
        "source": "USITC HTS 2026 Rev + USTR Section 301 通知",
        "note": "MFN 0%；对华新301(强迫劳动)12.5%。9503 是否在豁免清单需以 USTR 附件为准；若中美 300 亿对等降税生效，附加税可能归零。",
        "updated_at": "2026-10-29",
    },
    {
        "hs_code": "7323.93.00",
        "country": "美国",
        "description": "不锈钢餐桌/厨房/家用器具（厨具、餐具、食品接触容器）",
        "mfn_pct": 2.0,
        "china_surcharge_pct": 25.0,
        "effective_pct": 27.0,
        "source": "USITC HTS 2026 Rev + CBP CSMS（Section 232 钢铝衍生品）",
        "note": "MFN 2%；对华 Section 232 钢铝衍生品 25%（9903.82.09）。真空保温杯另见 9617.00（MFN 0）。以 CBP/USTR 最新为准。",
        "updated_at": "2026-10-29",
    },
    {
        "hs_code": "8507.60.00",
        "country": "美国",
        "description": "锂离子电池（电芯、模组、电池包、充电宝）",
        "mfn_pct": 3.4,
        "china_surcharge_pct": 37.5,
        "effective_pct": 40.9,
        "source": "USITC HTS 2026 Rev + USTR Section 301(25%) + 新301强迫劳动(12.5%)",
        "note": "MFN 3.4%；对华 = 301(25%) + 新301强迫劳动(12.5%) = 37.5%，合计约 40.9%。若叠加「互惠关税」会更高，务必以 CBP 实时为准。",
        "updated_at": "2026-10-29",
    },
    {
        "hs_code": "8518.30.00",
        "country": "美国",
        "description": "耳机/耳塞（含蓝牙耳机）",
        "mfn_pct": 0.0,
        "china_surcharge_pct": 25.0,
        "effective_pct": 25.0,
        "source": "USITC HTS 2026 Rev + USTR Section 301 清单3",
        "note": "MFN 0%；对华 Section 301(清单3) 25%。以 USTR 最新清单为准。",
        "updated_at": "2026-10-29",
    },
    {
        "hs_code": "8518.22.00",
        "country": "美国",
        "description": "多扬声器箱体（蓝牙音箱）",
        "mfn_pct": 0.0,
        "china_surcharge_pct": 25.0,
        "effective_pct": 25.0,
        "source": "USITC HTS 2026 Rev + USTR Section 301 清单3",
        "note": "MFN 0%；对华 Section 301(清单3) 25%。单扬声器见 8518.21。以 USTR 最新清单为准。",
        "updated_at": "2026-10-29",
    },
    # ================= 印度（BCD 基础关税 + AIDC 附加） =================
    {
        "hs_code": "9503.00.00",
        "country": "印度",
        "description": "玩具",
        "mfn_pct": 20.0,
        "china_surcharge_pct": 20.0,
        "effective_pct": 40.0,
        "source": "印度 CBIC 关税表 + Union Budget 2025-26",
        "note": "BCD 20% + AIDC 20% = 40%（玩具非制造用途）；IGST(18%/28%)另计；SWS 2026 起对 9503 豁免。以 CBIC 最新为准。",
        "updated_at": "2026-10-29",
    },
    {
        "hs_code": "7323.93.00",
        "country": "印度",
        "description": "不锈钢餐具/厨具",
        "mfn_pct": 20.0,
        "china_surcharge_pct": 0.0,
        "effective_pct": 20.0,
        "source": "印度 CBIC 关税表（估算）",
        "note": "BCD 约 20%（⚠️估算，需核实 CBIC）；IGST 另计。",
        "updated_at": "2026-10-29",
    },
    {
        "hs_code": "8507.60.00",
        "country": "印度",
        "description": "锂离子电池/充电宝",
        "mfn_pct": 20.0,
        "china_surcharge_pct": 0.0,
        "effective_pct": 20.0,
        "source": "印度 CBIC 关税表（估算）",
        "note": "BCD 约 20%（⚠️估算，需核实 CBIC）；IGST 另计。",
        "updated_at": "2026-10-29",
    },
    {
        "hs_code": "8518.30.00",
        "country": "印度",
        "description": "耳机/耳塞",
        "mfn_pct": 20.0,
        "china_surcharge_pct": 0.0,
        "effective_pct": 20.0,
        "source": "印度 CBIC 关税表（估算）",
        "note": "BCD 约 20%（⚠️估算，需核实 CBIC）；IGST 另计。",
        "updated_at": "2026-10-29",
    },
    {
        "hs_code": "8518.22.00",
        "country": "印度",
        "description": "蓝牙音箱",
        "mfn_pct": 20.0,
        "china_surcharge_pct": 0.0,
        "effective_pct": 20.0,
        "source": "印度 CBIC 关税表（估算）",
        "note": "BCD 约 20%（⚠️估算，需核实 CBIC）；IGST 另计。",
        "updated_at": "2026-10-29",
    },
    # ================= 俄罗斯（EAEU CCT 统一关税） =================
    {
        "hs_code": "9503.00.00",
        "country": "俄罗斯",
        "description": "玩具",
        "mfn_pct": 5.0,
        "china_surcharge_pct": 0.0,
        "effective_pct": 5.0,
        "source": "EAEU 统一关税表 CCT（估算）",
        "note": "EAEU CCT 约 5%（⚠️估算，需核实 EEC 官网）；增值税 VAT 另计。",
        "updated_at": "2026-10-29",
    },
    {
        "hs_code": "7323.93.00",
        "country": "俄罗斯",
        "description": "不锈钢餐具/厨具",
        "mfn_pct": 10.0,
        "china_surcharge_pct": 0.0,
        "effective_pct": 10.0,
        "source": "EAEU 统一关税表 CCT（估算）",
        "note": "EAEU CCT 约 10%（⚠️估算，需核实 EEC 官网）；增值税 VAT 另计。",
        "updated_at": "2026-10-29",
    },
    {
        "hs_code": "8507.60.00",
        "country": "俄罗斯",
        "description": "锂离子电池/充电宝",
        "mfn_pct": 5.0,
        "china_surcharge_pct": 0.0,
        "effective_pct": 5.0,
        "source": "EAEU 统一关税表 CCT（估算）",
        "note": "EAEU CCT 约 5%（⚠️估算，需核实 EEC 官网）；增值税 VAT 另计。",
        "updated_at": "2026-10-29",
    },
    {
        "hs_code": "8518.30.00",
        "country": "俄罗斯",
        "description": "耳机/耳塞",
        "mfn_pct": 5.0,
        "china_surcharge_pct": 0.0,
        "effective_pct": 5.0,
        "source": "EAEU 统一关税表 CCT（估算）",
        "note": "EAEU CCT 约 5%（⚠️估算，需核实 EEC 官网）；增值税 VAT 另计。",
        "updated_at": "2026-10-29",
    },
    {
        "hs_code": "8518.22.00",
        "country": "俄罗斯",
        "description": "蓝牙音箱",
        "mfn_pct": 5.0,
        "china_surcharge_pct": 0.0,
        "effective_pct": 5.0,
        "source": "EAEU 统一关税表 CCT（估算）",
        "note": "EAEU CCT 约 5%（⚠️估算，需核实 EEC 官网）；增值税 VAT 另计。",
        "updated_at": "2026-10-29",
    },
]

PRODUCT_MAP = [
    ("儿童声光电动早教玩具", "9503.00.00"),
    ("不锈钢食品接触容器", "7323.93.00"),
    ("锂电池/充电宝", "8507.60.00"),
    ("蓝牙耳机", "8518.30.00"),
    ("蓝牙音箱", "8518.22.00"),
]


def build():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.executescript(SCHEMA)
    for r in ROWS:
        conn.execute(
            "INSERT OR REPLACE INTO tariff_rates VALUES (?,?,?,?,?,?,?,?,?)",
            (r["hs_code"], r["country"], r["description"], r["mfn_pct"],
             r["china_surcharge_pct"], r["effective_pct"],
             r["source"], r["note"], r["updated_at"]),
        )
    for product, hs in PRODUCT_MAP:
        conn.execute("INSERT OR REPLACE INTO product_hs_map VALUES (?,?)", (product, hs))
    conn.commit()
    conn.close()
    print(f"OK: {DB_PATH}（{len(ROWS)} 条税率，{len(PRODUCT_MAP)} 条产品映射）")


if __name__ == "__main__":
    build()
