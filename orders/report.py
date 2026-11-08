"""产出报告：发货清单 / 异常清单 / 发货通知草稿。"""
from collections import defaultdict


def shipment_manifest(orders, results):
    """按「目的地 + 物流方式 + 是否危险品」分组统计件数、金额。"""
    groups = {}
    for o, r in zip(orders, results):
        key = (o.get("country") or "未填", o.get("mode") or "未填", bool(o.get("has_lithium")))
        g = groups.setdefault(key, {"destination": key[0], "mode": key[1], "dangerous": key[2],
                                    "orders": 0, "units": 0, "value_usd": 0.0})
        g["orders"] += 1
        g["units"] += o.get("quantity") or 0
        g["value_usd"] += (o.get("unit_value_usd") or 0) * (o.get("quantity") or 0)
    rows = []
    for g in groups.values():
        rows.append({
            "destination": g["destination"],
            "mode": g["mode"],
            "dangerous": "危险品" if g["dangerous"] else "普货",
            "orders": g["orders"],
            "units": g["units"],
            "value_usd": round(g["value_usd"], 2),
        })
    rows.sort(key=lambda x: (x["destination"], x["mode"], x["dangerous"]))
    return rows


def anomaly_report(orders, results):
    """汇总所有异常单。"""
    rows = []
    for o, r in zip(orders, results):
        for issue in r["anomalies"]:
            rows.append({
                "order_id": o.get("order_id") or "—",
                "category": o.get("category") or "—",
                "product": o.get("product") or "—",
                "country": o.get("country") or "未填",
                "type": issue["type"],
                "severity": issue["severity"],
                "message": issue["message"],
                "suggestion": issue["suggestion"],
            })
    return rows


def shipping_notices(orders, results):
    """给买家的发货通知草稿（只生成不真发，待人工确认）。"""
    notices = []
    for o, r in zip(orders, results):
        has_critical = any(i["severity"].startswith("🔴") for i in r["anomalies"])
        qty = o.get("quantity") or 0
        country = o.get("country") or "未填"
        buyer = o.get("buyer_name") or "亲爱的客户"
        oid = o.get("order_id") or "订单"
        if has_critical:
            text = "（存在高风险异常，发货前需人工处理，暂不生成通知）"
        else:
            text = (
                f"您好 {buyer}：\n"
                f"您的订单 {oid} 共 {qty} 件商品已备货完成，即将发往 {country}。\n"
                "物流单号将在发货后 24 小时内提供，感谢您的耐心等待。"
            )
        notices.append({
            "order_id": oid,
            "buyer": buyer,
            "status": "阻塞" if has_critical else "待确认",
            "blocked": has_critical,
            "text": text,
        })
    return notices


def summary(orders, results):
    """整批汇总统计。"""
    total = len(orders)
    units = sum(o.get("quantity") or 0 for o in orders)
    value = sum((o.get("unit_value_usd") or 0) * (o.get("quantity") or 0) for o in orders)
    anomaly_orders = sum(1 for r in results if r["anomaly_count"] > 0)
    critical_orders = sum(1 for r in results if r["critical_count"] > 0)
    return {
        "total_orders": total,
        "total_units": units,
        "total_value_usd": round(value, 2),
        "anomaly_orders": anomaly_orders,
        "critical_orders": critical_orders,
    }
