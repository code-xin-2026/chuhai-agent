"""规则式异常检测（规则打底）。每条规则返回 异常类型/严重级/建议。

严重级：🔴高 / 🟠较高 / 🟡中。
LLM 兜底（模糊项如 PO Box、疑似转口）在 Phase 1.5 由 order_processor 可选接入。
"""
import re

SANCTION_RISK_COUNTRIES = {"俄罗斯", "russia"}
SUPPORTED_COUNTRIES = {"美国", "印度", "俄罗斯", "usa", "us", "india", "russia", "america"}

LOWBALL_RATIO = 0.4
MAX_ORDER_QTY = 10000


def check_address(order):
    issues = []
    missing = [f for f in ("city", "state", "postal_code") if not order.get(f)]
    if missing:
        issues.append({
            "type": "地址缺失",
            "severity": "🟡 中",
            "message": f"收货地址缺字段：{'、'.join(missing)}",
            "suggestion": "补全地址后再发货，否则物流可能退件或延误",
        })
    pc = (order.get("postal_code") or "")
    if pc and not any(ch.isdigit() for ch in pc):
        issues.append({
            "type": "邮编异常",
            "severity": "🟡 中",
            "message": f"邮编「{pc}」不含数字，疑似格式错误",
            "suggestion": "核对邮编格式（美国 5 位 ZIP、印度 6 位 PIN、俄罗斯 6 位）",
        })
    return issues


def check_destination(order):
    issues = []
    country = (order.get("country") or "").strip()
    if not country:
        issues.append({
            "type": "目的地缺失",
            "severity": "🔴 高",
            "message": "订单未填写目的地国家",
            "suggestion": "无法做合规/关税/物流测算，请补全目的地国家",
        })
        return issues
    if country in SANCTION_RISK_COUNTRIES:
        issues.append({
            "type": "目的地制裁/结算风险",
            "severity": "🔴 高",
            "message": "目的地为俄罗斯：存在收款结算受限 + 次级制裁风险（若含美国技术/组件）",
            "suggestion": "发货前核实 OFAC/BIS 清单与结算通道，确认货物与付款不受限",
        })
    if country not in SUPPORTED_COUNTRIES:
        issues.append({
            "type": "目的地未覆盖",
            "severity": "🟡 中",
            "message": f"目的地「{country}」暂不在合规/税率库覆盖范围（当前：美国/印度/俄罗斯）",
            "suggestion": "按通用知识给出合规清单并标注需核实项",
        })
    return issues


def check_quantity(order):
    qty = order.get("quantity")
    issues = []
    if qty is None:
        issues.append({"type": "数量缺失", "severity": "🟡 中", "message": "订单数量为空", "suggestion": "补全数量"})
    elif qty <= 0:
        issues.append({"type": "数量异常", "severity": "🔴 高", "message": f"数量为 {qty}，不合法", "suggestion": "核对订单，疑似数据录入错误"})
    elif qty > MAX_ORDER_QTY:
        issues.append({"type": "数量异常", "severity": "🟡 中", "message": f"单笔数量 {qty} 件，远超常规阈值（{MAX_ORDER_QTY} 件）", "suggestion": "核对是否笔误，大单需单独走大宗贸易流程并复核买家资信"})
    return issues


def check_value(order):
    v = order.get("unit_value_usd")
    issues = []
    if v is None:
        issues.append({"type": "单价缺失", "severity": "🟡 中", "message": "订单单价为空", "suggestion": "补全单价才能算关税/成本"})
    elif v <= 0:
        issues.append({"type": "单价异常", "severity": "🔴 高", "message": f"单价 ${v}，不合法", "suggestion": "核对申报价值"})
    return issues


def check_lithium(order):
    has_li = order.get("has_lithium")
    product = (order.get("product") or "").lower()
    issues = []
    li_keywords = ["锂", "电池", "充电宝", "移动电源", "power", "battery", "蓝牙", "耳机", "音箱"]
    suspected = any(k in product for k in li_keywords)
    if suspected and has_li is False:
        issues.append({
            "type": "危险品未标注",
            "severity": "🟠 较高",
            "message": f"产品「{order.get('product')}」疑似含锂电池，但「是否含锂」填了否",
            "suggestion": "确认为锂电池则需 UN38.3 运输鉴定，物流按危险品计",
        })
    if suspected and has_li is None:
        issues.append({
            "type": "危险品信息缺失",
            "severity": "🟡 中",
            "message": f"产品「{order.get('product')}」疑似含锂电池，但未标注是否含锂",
            "suggestion": "补全是否含锂，影响物流与成本",
        })
    return issues


# 参考单价（USD，整理估算值，用于低报嫌疑判断）
REFERENCE_PRICE = [
    ("儿童", 15), ("玩具", 15),
    ("不锈钢", 5), ("保温杯", 5),
    ("充电宝", 20), ("电池", 20),
    ("耳机", 12),
    ("音箱", 25), ("音响", 25),
]
LOWBALL_RATIO = 0.4


def _ref_price(product):
    p = (product or "").lower()
    for kw, price in REFERENCE_PRICE:
        if kw in p:
            return price
    return None


def check_underpriced(order):
    """低报嫌疑：申报单价明显低于同类参考价。"""
    v = order.get("unit_value_usd")
    product = order.get("product") or ""
    if v is None or v <= 0:
        return []  # 单价异常规则已处理
    ref = _ref_price(product)
    if ref and v < ref * LOWBALL_RATIO:
        return [{
            "type": "低报嫌疑",
            "severity": "🔴 高",
            "message": f"单价 ${v} 明显低于同类参考价 ${ref}（低于 40%），疑似低报逃税",
            "suggestion": "核对申报价值，低报可能被海关查扣、罚款",
        }]
    return []


def check_high_tariff(order, cost_info):
    """高关税目的地：有效关税税率超过阈值时提醒（比「成本侵蚀」更有区分度）。"""
    if not cost_info:
        return []
    eff = (cost_info.get("tariff") or {}).get("effective_pct")
    if eff is not None and eff > 30:
        return [{
            "type": "高关税目的地",
            "severity": "🟡 中",
            "message": f"该目的地有效关税约 {eff:.1f}%，属高关税（如对华叠加 232/301 或高 BCD）",
            "suggestion": "核算利润空间，考虑调整申报价值、走货方式或目标市场",
        }]
    return []


def check_address_type(order):
    """PO Box 地址：多数快递/专线不收，且常见于货代转口。"""
    at = (order.get("address_type") or "").strip().lower()
    if at and ("po" in at or "box" in at):
        return [{
            "type": "PO Box 地址",
            "severity": "🟠 较高",
            "message": "收货地址为 PO Box，多数快递/专线不收，且无法核实实际收件人",
            "suggestion": "确认是否有实体收货地址；PO Box 常见于货代转口，需核实最终收货方",
        }]
    return []


def check_origin(order):
    """原产地缺失：影响关税归类与优惠判定。"""
    if not (order.get("origin") or "").strip():
        return [{
            "type": "原产地缺失",
            "severity": "🟡 中",
            "message": "订单未填写原产地，影响关税归类与优惠（FTA/附加税）判定",
            "suggestion": "补录原产地，原产地直接决定适用税率",
        }]
    return []


def check_cert_status(order):
    """认证状态缺失：品类强制认证可能未完成。"""
    cs = (order.get("cert_status") or "").strip()
    if cs and any(k in cs for k in ("缺失", "未提供", "未申请", "未确认", "待确认")):
        return [{
            "type": "认证缺失",
            "severity": "🟠 较高",
            "message": f"认证状态为「{cs}」，该品类强制认证可能缺失",
            "suggestion": "核对品类强制认证清单，补齐后再发货",
        }]
    return []


def check_notes(order):
    """备注陷阱：转口贸易 / 危险品漏报 / 收货方不明。"""
    notes = (order.get("notes") or "").lower()
    issues = []
    if any(k in notes for k in ("转口", "forward", "reship", "drop ship", "dropship", "transship", "third party", "第三方", "转运")):
        issues.append({
            "type": "疑似转口贸易",
            "severity": "🟠 较高",
            "message": "备注提示货代/转口/第三方转运，最终目的地可能非申报国",
            "suggestion": "核实最终收货方与实际目的地，转口有合规与制裁风险",
        })
    if any(k in notes for k in ("易燃", "液体", "flammable", "liquid")):
        issues.append({
            "type": "危险品申报风险",
            "severity": "🔴 高",
            "message": "备注提示液体/易燃风险，但可能按普货申报",
            "suggestion": "核对是否危险品，按危险品申报与运输，否则有拒收/罚款风险",
        })
    if any(k in notes for k in ("consignee unknown", "收货方不明", "未知收货")):
        issues.append({
            "type": "收货方不明",
            "severity": "🟡 中",
            "message": "备注提示收货方不明/无法核实",
            "suggestion": "核实实际收货方身份",
        })
    return issues


def detect_all(order, cost_info=None):
    """跑全部规则，返回该订单的异常列表。"""
    issues = []
    issues += check_address(order)
    issues += check_destination(order)
    issues += check_quantity(order)
    issues += check_value(order)
    issues += check_lithium(order)
    issues += check_underpriced(order)
    issues += check_high_tariff(order, cost_info)
    issues += check_address_type(order)
    issues += check_origin(order)
    issues += check_cert_status(order)
    issues += check_notes(order)
    return issues
