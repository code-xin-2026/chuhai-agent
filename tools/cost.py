"""到岸成本测算（美国 · 儿童声光电动早教玩具）。

分项：货值 / 进口关税(实时HS) / MPF / HMF / 物流 / 危险品附加 / FBA预处理 / 认证摊薄 / 风险备用金。
关税税率从 SQLite 实时查询（分层：MFN/301/IEEPA/新301，带来源）；物流等其余费率为估算值。
"""
from tools import tariff_db
from tools.compliance import certification_total_cost_usd

# —— 报关费率（真实，CBP 现行）——
MPF_RATE = 0.003464          # 商品处理费 0.3464%
MPF_MIN = 29.66
MPF_MAX = 575.35
HMF_RATE = 0.00125           # 港口维护费 0.125%（海运）

# —— 物流/杂项（估算值，正式版接实时报价）——
FREIGHT_SEA_USD_PER_KG = 4.0
FREIGHT_AIR_USD_PER_KG = 10.0
DANGEROUS_SURCHARGE_USD_PER_KG = 1.5
FBA_PREP_USD_PER_UNIT = 0.5
RISK_RESERVE_PCT_SMALL = 0.05
RISK_RESERVE_PCT_LARGE = 0.02
UNIT_WEIGHT_KG = 0.3


def estimate_landed_cost(destination: str, product: str, unit_value_usd: float,
                         quantity: int, mode: str = "FBA大批量",
                         has_lithium_battery: bool = True):
    """测算到岸成本。mode: 直邮小包 | FBA大批量。"""
    qty = int(quantity)
    total_value = float(unit_value_usd) * qty

    # 关税：实时查 HS 分层税率
    tariff = tariff_db.query_tariff(product, destination)
    if tariff and tariff.get("in_scope"):
        effective_pct = tariff["effective_pct"]
        tariff_note = tariff.get("note", "")
    else:
        effective_pct = 0.0
        tariff_note = "该产品/国家暂无税率数据，关税按 0 估算，需核实"
    duty = total_value * effective_pct / 100.0

    mpf = max(MPF_MIN, min(MPF_MAX, total_value * MPF_RATE))
    hmf = total_value * HMF_RATE

    weight_kg = max(qty * UNIT_WEIGHT_KG, 1.0)
    freight_rate = FREIGHT_AIR_USD_PER_KG if mode == "直邮小包" else FREIGHT_SEA_USD_PER_KG
    freight = weight_kg * freight_rate
    dangerous_surcharge = weight_kg * DANGEROUS_SURCHARGE_USD_PER_KG if has_lithium_battery else 0.0
    fba_prep = qty * FBA_PREP_USD_PER_UNIT if mode == "FBA大批量" else 0.0

    cert_total = certification_total_cost_usd(destination, product)
    reserve_rate = RISK_RESERVE_PCT_SMALL if mode == "直邮小包" else RISK_RESERVE_PCT_LARGE
    risk_reserve = total_value * reserve_rate

    extra_costs = duty + mpf + hmf + freight + dangerous_surcharge + fba_prep + cert_total + risk_reserve
    total_landed = total_value + extra_costs

    return {
        "destination": destination,
        "product": product,
        "mode": mode,
        "has_lithium_battery": has_lithium_battery,
        "quantity": qty,
        "declared_value_usd": round(total_value, 2),
        "tariff": {
            "hs_code": tariff.get("hs_code") if tariff else None,
            "effective_pct": effective_pct,
            "layers": tariff.get("rates") if tariff else None,
            "source": tariff.get("source") if tariff else None,
            "note": tariff_note,
            "updated_at": tariff.get("updated_at") if tariff else None,
        },
        "breakdown": {
            "进口关税": round(duty, 2),
            "MPF 商品处理费": round(mpf, 2),
            "HMF 港口维护费": round(hmf, 2),
            "物流(空/海派)": round(freight, 2),
            "危险品附加费": round(dangerous_surcharge, 2),
            "FBA预处理/贴标": round(fba_prep, 2),
            "认证一次性成本(本批摊薄)": round(cert_total, 2),
            "风险备用金(退运/召回)": round(risk_reserve, 2),
        },
        "extra_costs_usd": round(extra_costs, 2),
        "total_landed_usd": round(total_landed, 2),
        "unit_landed_usd": round(total_landed / qty, 2) if qty else None,
        "risk_note": "风险备用金为估算系数(试销5%/大批2%)，覆盖退运/召回。",
        "estimate_warning": "物流/杂项为估算值；关税为 SQLite 实时查询的分层税率，最终以海关实时税率为准。",
    }
