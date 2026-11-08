"""📦 订单自动处理页：上传 CSV/Excel → 自动 合规+成本+异常 → 发货清单/异常清单/通知草稿。

Phase 1：只生成、不真发（通知均为「待确认」状态，人工确认后才导出/发送）。
"""
import os
import tempfile

import pandas as pd
import streamlit as st

from orders.parser import parse_csv_text, parse_xlsx
from orders.processor import process_orders
from orders.report import shipment_manifest, anomaly_report, shipping_notices, summary

st.set_page_config(page_title="帆朵 · 订单自动处理", page_icon="📦", layout="wide")

# —— 密码门（与主应用一致）——
PASSWORD = ""
try:
    PASSWORD = st.secrets.get("APP_PASSWORD", "")
except Exception:
    PASSWORD = ""
if not PASSWORD:
    PASSWORD = os.getenv("APP_PASSWORD", "")
if PASSWORD and not st.session_state.get("authed"):
    st.title("🔐 帆朵 · 订单自动处理")
    with st.form("login2"):
        pwd = st.text_input("访问密码", type="password")
        if st.form_submit_button("进入"):
            if pwd == PASSWORD:
                st.session_state["authed"] = True
                st.rerun()
            else:
                st.error("密码错误")
    st.stop()

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEMO_CSV = os.path.join(PROJECT_ROOT, "data", "demo_orders.csv")

st.title("📦 订单自动处理")
st.caption("上传订单 CSV/Excel → 帆朵自动跑「合规检查 + 关税/成本测算 + 异常识别」→ 产出 发货清单 / 异常清单 / 发货通知草稿。当前覆盖：美国 / 印度 / 俄罗斯。")

# —— 输入区 ——
c_up, c_btn = st.columns([3, 1])
with c_up:
    uploaded = st.file_uploader("上传订单文件（CSV 或 Excel）", type=["csv", "xlsx", "xls"])
with c_btn:
    st.write("")
    st.write("")
    load_demo = st.button("📂 加载演示样本", width="stretch")

orders = None
source_name = ""

if uploaded is not None:
    source_name = uploaded.name
    name = uploaded.name.lower()
    data = uploaded.read()
    if name.endswith(".csv"):
        orders = parse_csv_text(data.decode("utf-8-sig", errors="replace"))
    else:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as tf:
            tf.write(data)
            tf.flush()
            orders = parse_xlsx(tf.name)
        os.unlink(tf.name)
elif load_demo:
    source_name = "演示样本 demo_orders.csv"
    orders = parse_csv_text(open(DEMO_CSV, encoding="utf-8-sig").read())

if orders is not None:
    if not orders:
        st.warning("没有解析到任何订单。请检查文件内容或列名。")
    else:
        results = process_orders(orders)
        s = summary(orders, results)
        manifest = shipment_manifest(orders, results)
        anomalies = anomaly_report(orders, results)
        notices = shipping_notices(orders, results)

        st.subheader(f"📊 处理结果 · {source_name}")

        # 顶部指标
        m1, m2, m3, m4, m5 = st.columns(5)
        m1.metric("订单总数", s["total_orders"])
        m2.metric("总件数", s["total_units"])
        m3.metric("总货值(USD)", f"${s['total_value_usd']:,.0f}")
        m4.metric("有异常的订单", s["anomaly_orders"])
        m5.metric("🔴 高风险订单", s["critical_orders"])

        tab1, tab2, tab3 = st.tabs(["📦 发货清单", "⚠️ 异常清单", "✉️ 发货通知草稿"])

        with tab1:
            if manifest:
                df = pd.DataFrame(manifest).rename(columns={
                    "destination": "目的地", "mode": "物流方式", "dangerous": "类型",
                    "orders": "订单数", "units": "总件数", "value_usd": "货值(USD)",
                })
                st.dataframe(df, width="stretch", hide_index=True)
                st.caption(f"共 {len(manifest)} 批，按「目的地 + 物流方式 + 是否危险品」分组")
            else:
                st.info("无数据")

        with tab2:
            if anomalies:
                df = pd.DataFrame(anomalies).rename(columns={
                    "order_id": "订单号", "category": "品类", "product": "产品", "country": "目的地",
                    "type": "异常类型", "severity": "严重级", "message": "说明", "suggestion": "建议",
                })
                st.dataframe(df, width="stretch", hide_index=True)
                st.caption(f"共 {len(anomalies)} 条异常，涉及 {s['anomaly_orders']} 个订单")
            else:
                st.success("✅ 全部订单正常，无异常")

        with tab3:
            st.caption("Phase 1 只生成草稿、不真实发送，人工确认后再导出。🔴 高风险的订单会被阻塞。")
            for n in notices:
                icon = "🔴" if n["blocked"] else "🟢"
                with st.expander(f"{icon} {n['order_id']} · {n['buyer']} · [{n['status']}]"):
                    st.text(n["text"])
            if notices:
                all_text = "\n\n---\n\n".join(
                    f"【{n['order_id']}】{n['buyer']}（{n['status']}）\n{n['text']}" for n in notices
                )
                st.download_button("⬇️ 导出全部通知草稿 (.txt)", data=all_text,
                                   file_name="shipping_notices.txt", mime="text/plain")

        # 订单明细
        with st.expander("🔍 全部订单明细（合规 + 关税 + 到岸成本）"):
            rows = []
            for o, r in zip(orders, results):
                comp = r["compliance"]
                tariff = r["tariff"]
                cost = r["cost"]
                rows.append({
                    "订单号": o.get("order_id") or "—",
                    "品类": o.get("category") or "—",
                    "产品": o.get("product") or "—",
                    "目的地": o.get("country") or "未填",
                    "数量": o.get("quantity"),
                    "货值(USD)": (o.get("unit_value_usd") or 0) * (o.get("quantity") or 0),
                    "合规品类": comp.get("label") if comp.get("in_scope") else "未覆盖",
                    "HS编码": tariff.get("hs_code") if tariff.get("in_scope") else "—",
                    "有效关税%": tariff.get("effective_pct") if tariff.get("in_scope") else None,
                    "到岸成本(USD)": cost.get("total_landed_usd") if cost else None,
                    "异常数": r["anomaly_count"],
                })
            st.dataframe(pd.DataFrame(rows), width="stretch", hide_index=True)
else:
    st.info("👈 上传订单文件，或点「加载演示样本」看帆朵自动处理 24 笔演示订单（含各类异常）。")
