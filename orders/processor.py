"""订单批量处理编排：解析 → 逐单 合规/关税/成本/异常 → 汇总结果。

核心流水线是「确定性」的：纯工具 + 纯规则，不调 LLM，快、可复现、不幻觉。
LLM 只用于两个可选的后续环节（模糊异常兜底、买家 AI 客服），Phase 1 不依赖。
"""
from tools import compliance, tariff_db
from tools.cost import estimate_landed_cost
from orders.anomaly import detect_all

COUNTRY_ALIAS = {
    "usa": "美国", "us": "美国", "美国": "美国", "america": "美国", "unitedstates": "美国",
    "india": "印度", "印度": "印度",
    "russia": "俄罗斯", "俄罗斯": "俄罗斯", "俄国": "俄罗斯", "russianfederation": "俄罗斯",
}


def norm_country(c):
    return COUNTRY_ALIAS.get((c or "").strip().lower(), (c or "").strip() or "美国")


def _map_mode(mode):
    m = (mode or "").strip()
    if any(k in m for k in ("小包", "直邮", "快递", "专线", "express", "parcel", "小包裹")):
        return "直邮小包"
    return "FBA大批量"


def process_orders(orders):
    """对每笔订单跑 合规+关税+成本+异常，返回逐单结果。"""
    results = []
    for o in orders:
        country = norm_country(o.get("country"))
        product = o.get("product") or ""
        unit_value = o.get("unit_value_usd") or 0
        qty = o.get("quantity") or 0
        has_li = bool(o.get("has_lithium"))
        mode = _map_mode(o.get("mode"))

        comp = compliance.check_compliance(country, product)
        tariff = tariff_db.query_tariff(product, country)
        try:
            cost_info = estimate_landed_cost(
                destination=country, product=product, unit_value_usd=unit_value,
                quantity=qty, mode=mode, has_lithium_battery=has_li)
        except Exception:
            cost_info = None

        anomalies = detect_all(o, cost_info)
        results.append({
            "order": o,
            "compliance": comp,
            "tariff": tariff,
            "cost": cost_info,
            "anomalies": anomalies,
            "anomaly_count": len(anomalies),
            "critical_count": sum(1 for a in anomalies if a["severity"].startswith("🔴")),
        })
    return results


def process_csv_text(text):
    """一站式：CSV 文本 → 处理结果。"""
    from orders.parser import parse_csv_text
    orders = parse_csv_text(text)
    results = process_orders(orders)
    return orders, results
