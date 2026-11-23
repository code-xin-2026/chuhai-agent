"""到岸成本测算（支持任意产品：税率库真实数据 或 大模型估算税率）。

分项：货值 / 进口关税 / 物流 / 危险品附加 / FBA预处理 / 认证摊薄 / 风险备用金，
另按目的国叠加：美国 MPF/HMF；印度 IGST；俄罗斯 VAT。
关税来源分级：① 传入的 tariff_rate_pct（模型估算）> ② SQLite 税率库（真实）。
"""
from tools import tariff_db
from tools.compliance import certification_total_cost_usd

# —— 报关费率（真实，CBP 现行，仅美国）——
MPF_RATE = 0.003464          # 商品处理费 0.3464%
MPF_MIN = 29.66
MPF_MAX = 575.35
HMF_RATE = 0.00125           # 港口维护费 0.125%（海运）

# —— 增值税性质税费（印度 IGST / 俄罗斯 VAT，按 CIF+关税 计）——
IGST_RATE = 0.18              # 印度 IGST（电子/一般 18%；部分玩具 5%，以 CBIC 为准）
RUSSIA_VAT_RATE = 0.22        # 俄罗斯 VAT（2026-01-01 起 22%）
RUSSIA_VAT_CHILD_RATE = 0.10  # 俄罗斯儿童玩具清单（俄政府 908 号令）10%
_CHILD_KW = ("玩具", "儿童", "早教", "玩偶", "积木", "婴儿", "童车")

# —— 物流/杂项（估算值，正式版接实时报价）——
FREIGHT_SEA_USD_PER_KG = 4.0
FREIGHT_AIR_USD_PER_KG = 10.0
FREIGHT_LAND_USD_PER_KG = 3.5
DANGEROUS_SURCHARGE_USD_PER_KG = 1.5
FBA_PREP_USD_PER_UNIT = 0.5
RISK_RESERVE_PCT_SMALL = 0.05
RISK_RESERVE_PCT_LARGE = 0.02
UNIT_WEIGHT_KG = 0.3


def _norm_dest(destination):
    """目的国归一化：兼容中文/英文/缩写。注意先判「俄罗斯」，避免 'us' 误匹配 russia。"""
    s = (destination or "").strip().lower()
    if "印度" in s or s == "india":
        return "印度"
    if "俄罗斯" in s or "俄国" in s or "russia" in s:
        return "俄罗斯"
    if "美国" in s or s in ("us", "usa", "america", "unitedstates"):
        return "美国"
    return s or "美国"


def _freight_rate(mode):
    """按运输方式解析运费单价：空运/海运/陆运/小包。"""
    m = (mode or "").strip()
    if any(k in m for k in ("空运", "air", "直邮", "小包", "快递", "express", "parcel", "专线")):
        return FREIGHT_AIR_USD_PER_KG
    if any(k in m for k in ("陆运", "land", "公路", "铁路")):
        return FREIGHT_LAND_USD_PER_KG
    return FREIGHT_SEA_USD_PER_KG


def _is_small_parcel(mode):
    """小包/直邮/快递/专线类（走空运、无 FBA 预处理、风险系数更高）。"""
    m = (mode or "").strip()
    return any(k in m for k in ("小包", "直邮", "快递", "专线", "express", "parcel"))


def estimate_landed_cost(destination: str, product: str, unit_value_usd: float,
                         quantity: int, mode: str = "FBA大批量",
                         has_lithium_battery: bool = False,
                         tariff_rate_pct: float = None):
    """测算到岸成本。tariff_rate_pct 可选：产品不在税率库时由模型估算传入。

    增值税：印度 IGST 18%、俄罗斯 VAT 22%（儿童玩具 10%）已并入到岸成本；
    美国 MPF/HMF 仅美国征收，非美市场为 0。
    """
    dest = _norm_dest(destination)
    qty = int(quantity)
    total_value = float(unit_value_usd) * qty

    # 关税：① 传入的估算税率 > ② 税率库真实数据
    tariff = None
    if tariff_rate_pct is not None:
        effective_pct = float(tariff_rate_pct)
        tariff_note = "大模型估算的有效税率（需核实，以海关实时为准）"
        tariff = {"effective_pct": effective_pct, "source": "LLM估算",
                  "note": tariff_note, "hs_code": None, "rates": None, "updated_at": None}
    else:
        tariff = tariff_db.query_tariff(product, dest)
        if tariff and tariff.get("in_scope"):
            effective_pct = tariff["effective_pct"]
            tariff_note = tariff.get("note", "")
        else:
            effective_pct = 0.0
            tariff_note = "该产品无税率数据且未传估算税率，关税暂按 0（明显偏低，需重算）"
    duty = total_value * effective_pct / 100.0

    # 美国报关费（仅美国）
    if dest == "美国":
        mpf = max(MPF_MIN, min(MPF_MAX, total_value * MPF_RATE))
        hmf = total_value * HMF_RATE
    else:
        mpf = 0.0
        hmf = 0.0

    weight_kg = max(qty * UNIT_WEIGHT_KG, 1.0)
    freight_rate = _freight_rate(mode)
    freight = weight_kg * freight_rate
    dangerous_surcharge = weight_kg * DANGEROUS_SURCHARGE_USD_PER_KG if has_lithium_battery else 0.0
    fba_prep = qty * FBA_PREP_USD_PER_UNIT if not _is_small_parcel(mode) else 0.0

    cert_total = certification_total_cost_usd(dest, product)
    reserve_rate = RISK_RESERVE_PCT_SMALL if _is_small_parcel(mode) else RISK_RESERVE_PCT_LARGE
    risk_reserve = total_value * reserve_rate

    # 增值税（印度 IGST / 俄罗斯 VAT，按 CIF+关税 计）
    igst = 0.0
    vat = 0.0
    vat_rate = RUSSIA_VAT_RATE
    if dest == "印度":
        igst = (total_value + duty) * IGST_RATE
    elif dest == "俄罗斯":
        if any(k in (product or "") for k in _CHILD_KW):
            vat_rate = RUSSIA_VAT_CHILD_RATE
        vat = (total_value + duty) * vat_rate

    extra_costs = duty + mpf + hmf + freight + dangerous_surcharge + fba_prep + cert_total + risk_reserve + igst + vat
    total_landed = total_value + extra_costs

    breakdown = {
        "进口关税": round(duty, 2),
    }
    if dest == "美国":
        breakdown["MPF 商品处理费"] = round(mpf, 2)
        breakdown["HMF 港口维护费"] = round(hmf, 2)
    breakdown.update({
        "物流(空/海派)": round(freight, 2),
        "危险品附加费": round(dangerous_surcharge, 2),
        "FBA预处理/贴标": round(fba_prep, 2),
        "认证一次性成本(本批摊薄)": round(cert_total, 2),
        "风险备用金(退运/召回)": round(risk_reserve, 2),
    })
    if dest == "印度":
        breakdown["IGST 增值税(印度18%)"] = round(igst, 2)
    elif dest == "俄罗斯":
        breakdown[f"VAT 增值税(俄{int(vat_rate * 100)}%)"] = round(vat, 2)

    return {
        "destination": dest,
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
        "breakdown": breakdown,
        "extra_costs_usd": round(extra_costs, 2),
        "total_landed_usd": round(total_landed, 2),
        "unit_landed_usd": round(total_landed / qty, 2) if qty else None,
        "risk_note": "风险备用金为估算系数(试销5%/大批2%)，覆盖退运/召回。",
        "estimate_warning": "物流/杂项为估算值；关税最终以海关实时税率为准。印度 IGST / 俄 VAT 已并入；玩具 IGST 可能适用 5% 优惠档、以 CBIC 为准。",
    }
