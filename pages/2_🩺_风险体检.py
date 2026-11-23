"""🩺 风险体检页：填「产品 + 目标国 + 数量/单价」→ 一键跑完整链路 → 生成可下载报告。

纯确定性（不调 LLM）：合规查询 + 关税分层 + 到岸成本 + 风险提示 + 三国对比，
评委/卖家无需会提问，点一下即可拿到一份完整「体检报告」——从「一问一答」到「主动干活」。
"""
import os

import streamlit as st

from tools import compliance, tariff_db
from tools.cost import estimate_landed_cost
from orders.anomaly import (check_quantity, check_value, check_lithium,
                            check_underpriced, check_high_tariff)

st.set_page_config(page_title="帆朵 · 风险体检", page_icon="🩺", layout="wide")

# —— 密码门（与主应用一致）——
PASSWORD = ""
try:
    PASSWORD = st.secrets.get("APP_PASSWORD", "")
except Exception:
    PASSWORD = ""
if not PASSWORD:
    PASSWORD = os.getenv("APP_PASSWORD", "")
if PASSWORD and not st.session_state.get("authed"):
    st.title("🔐 帆朵 · 风险体检")
    with st.form("login3"):
        pwd = st.text_input("访问密码", type="password")
        if st.form_submit_button("进入"):
            if pwd == PASSWORD:
                st.session_state["authed"] = True
                st.rerun()
            else:
                st.error("密码错误")
    st.stop()

COUNTRIES = ["美国", "印度", "俄罗斯"]
ALL_COUNTRIES = ["美国", "印度", "俄罗斯"]
MODES = ["FBA大批量", "直邮小包"]

EXAMPLES = [
    ("儿童声光电动早教玩具", "美国", 500, 15.0, True),
    ("不锈钢保温杯", "印度", 500, 5.0, False),
    ("蓝牙耳机", "俄罗斯", 800, 12.0, True),
    ("充电宝", "美国", 2000, 20.0, True),
]

st.title("🩺 风险体检报告")
st.caption("填产品 + 目标国 + 数量/单价，一键跑完整链路（认证准入 + 关税分层 + 到岸成本 + 风险提示 + 三国对比），生成可下载报告。")

# —— 示例一键填入 ——
st.markdown("**快速示例：**")
ex_cols = st.columns(len(EXAMPLES))
picked = None
for i, (p, d, q, v, li) in enumerate(EXAMPLES):
    if ex_cols[i].button(f"{p} → {d}", key=f"ex_{i}", width="stretch"):
        picked = (p, d, q, v, li)

with st.form("checkup_form"):
    c1, c2 = st.columns(2)
    with c1:
        product = st.text_input("产品名", value=picked[0] if picked else "儿童声光电动早教玩具",
                                help="如：儿童声光电动早教玩具 / 不锈钢保温杯 / 蓝牙耳机 / 充电宝")
        unit_value = st.number_input("单品申报价值 (USD)", min_value=0.0, value=float(picked[3] if picked else 15.0), step=1.0)
        mode = st.selectbox("走货方式", MODES, index=0)
    with c2:
        destination = st.selectbox("目标国", ALL_COUNTRIES, index=ALL_COUNTRIES.index(picked[1]) if picked else 0)
        quantity = st.number_input("数量（件）", min_value=1, value=int(picked[2] if picked else 500), step=1)
        has_li = st.toggle("含锂电池", value=bool(picked[4] if picked else True))
    submit = st.form_submit_button("🚀 一键体检", width="stretch")

if not submit:
    st.info("👆 填写参数后点「一键体检」，帆朵会自动跑完整个分析链路并生成报告。")
    st.stop()

# ================= 跑完整链路 =================
product = (product or "").strip()
if not product:
    st.error("请填写产品名。")
    st.stop()

comp = compliance.check_compliance(destination, product)
tariff = tariff_db.query_tariff(product, destination)

try:
    cost_info = estimate_landed_cost(
        destination=destination, product=product, unit_value_usd=unit_value,
        quantity=quantity, mode=mode, has_lithium_battery=has_li)
except Exception:
    cost_info = None

# —— 产品级风险提示（不含订单地址类，只跑与产品/成本相关规则）——
_order = {"product": product, "quantity": quantity, "unit_value_usd": unit_value,
          "has_lithium": has_li}
risks = []
risks += check_quantity(_order)
risks += check_value(_order)
risks += check_lithium(_order)
risks += check_underpriced(_order)
risks += check_high_tariff(_order, cost_info)

# —— 三国有效关税对比 ——
compare = {}
for c in ALL_COUNTRIES:
    t = tariff_db.query_tariff(product, c)
    compare[c] = {"effective_pct": t["effective_pct"], "in_scope": t.get("in_scope"),
                  "hs_code": t.get("hs_code"), "source_url": t.get("source_url", "")} if t else None

# ================= 报告渲染 =================
hs_code = tariff.get("hs_code") if tariff and tariff.get("in_scope") else (comp.get("hs_hint") or "未映射")
eff_pct = tariff.get("effective_pct") if tariff and tariff.get("in_scope") else None

st.subheader("📊 体检结果")
m1, m2, m3, m4 = st.columns(4)
m1.metric("HS 编码", hs_code)
m2.metric("有效关税", f"{eff_pct}%" if eff_pct is not None else "—")
m3.metric("到岸成本 (USD)", f"${cost_info['total_landed_usd']:,.0f}" if cost_info else "—")
m4.metric("风险提示", f"{len(risks)} 项")

tab1, tab2, tab3, tab4, tab5 = st.tabs(["🛃 认证准入", "💰 关税分层", "🧮 到岸成本", "⚠️ 风险提示", "🌍 三国对比"])

with tab1:
    if comp.get("in_scope"):
        st.markdown(f"**{comp['label']}** · 归类参考 {comp.get('hs_hint')}")
        st.markdown(comp["summary"])
        st.markdown("**强制项**")
        for c_ in comp["mandatory"]:
            st.markdown(f"- **{c_['name']}** · `{c_['reg']}`\n  - 原因：{c_['why']}\n  - 跳过后果：{c_['risk']}\n  - 成本：${c_['one_time_cost_usd'][0]}–{c_['one_time_cost_usd'][1]} · 周期约 {c_['lead_time_days']} 天")
        if comp.get("optional"):
            st.markdown("**建议项**")
            for c_ in comp["optional"]:
                st.markdown(f"- **{c_['name']}** · `{c_['reg']}` — {c_['why']}")
        for n in comp.get("notes", []):
            st.caption(f"· {n}")
    else:
        st.warning("该品类暂无结构化认证数据，请以带法规编号的通用知识为准并标注需核实项。")

with tab2:
    if tariff and tariff.get("in_scope"):
        rates = tariff["rates"]
        st.markdown(f"**基础关税（稳定）**：{rates['基础关税(稳定)']}%  \n"
                    f"**附加税/捐税（政策波动）**：{rates['附加税(政策波动)']}%  \n"
                    f"**有效关税**：**{tariff['effective_pct']}%**")
        st.markdown(f"**来源**：[{tariff['source']}]({tariff.get('source_url')}) · 更新时间 {tariff['updated_at']}")
        st.caption(tariff["note"])
    else:
        st.warning("该产品暂未映射到 HS 编码，关税按 0% 处理（明显偏低，需重算）。")

with tab3:
    if cost_info:
        b = cost_info["breakdown"]
        st.markdown(f"**申报货值**：${cost_info['declared_value_usd']:,.2f} · **到岸总成本**：**${cost_info['total_landed_usd']:,.2f}** · **单件**：${cost_info['unit_landed_usd']:,.2f}")
        st.table([{"费用项": k, "金额(USD)": f"${v:,.2f}"} for k, v in b.items()])
        st.caption(cost_info["estimate_warning"])
    else:
        st.warning("成本测算失败。")

with tab4:
    if risks:
        for r in risks:
            sev = r["severity"]
            st.markdown(f"**{sev} · {r['type']}**  \n{r['message']}  \n→ 建议：{r['suggestion']}")
    else:
        st.success("✅ 该产品在给定参数下未触发产品级风险提示。")

with tab5:
    rows = []
    for c in ALL_COUNTRIES:
        t = compare.get(c)
        if t and t.get("in_scope"):
            rows.append({"市场": c, "HS编码": t["hs_code"], "有效关税": f"{t['effective_pct']}%",
                         "来源": t["source_url"]})
        else:
            rows.append({"市场": c, "HS编码": "—", "有效关税": "未覆盖", "来源": ""})
    st.table(rows)
    scoped = [t["effective_pct"] for t in compare.values() if t and t.get("in_scope")]
    if scoped:
        highest = max(scoped)
        lowest = min(scoped)
        st.markdown(f"💡 三国中有效关税最高 **{highest}%**，最低 **{lowest}%**，价差 **{highest - lowest:.1f} 个百分点**——同一产品换个市场，税负天差地别。")

# ================= 生成可下载 Markdown 报告 =================
def _md_report():
    L = []
    L.append(f"# 🩺 帆朵 · 风险体检报告\n")
    L.append(f"- 产品：{product}")
    L.append(f"- 目标国：{destination}")
    L.append(f"- HS 编码：{hs_code}")
    L.append(f"- 数量：{quantity} 件 · 单价：${unit_value:,.2f}")
    L.append(f"- 走货方式：{mode} · 含锂电池：{'是' if has_li else '否'}\n")
    L.append("## 一、关税分层")
    if tariff and tariff.get("in_scope"):
        rates = tariff["rates"]
        L.append(f"- 基础关税（稳定）：{rates['基础关税(稳定)']}%")
        L.append(f"- 附加税/捐税（政策波动）：{rates['附加税(政策波动)']}%")
        L.append(f"- 有效关税：{tariff['effective_pct']}%")
        L.append(f"- 来源：{tariff['source']}（{tariff.get('source_url')}）· 更新 {tariff['updated_at']}")
        L.append(f"- 说明：{tariff['note']}")
    else:
        L.append("- 未映射到 HS 编码，关税按 0% 处理（需重算）")
    L.append("\n## 二、认证准入")
    if comp.get("in_scope"):
        L.append(f"- 品类：{comp['label']}")
        L.append(f"- 概览：{comp['summary']}")
        L.append("- 强制项：")
        for c_ in comp["mandatory"]:
            L.append(f"  - {c_['name']}（{c_['reg']}）：跳过后果 {c_['risk']}；成本 ${c_['one_time_cost_usd'][0]}–{c_['one_time_cost_usd'][1]}，周期 {c_['lead_time_days']} 天")
        if comp.get("optional"):
            L.append("- 建议项：")
            for c_ in comp["optional"]:
                L.append(f"  - {c_['name']}（{c_['reg']}）")
        for n in comp.get("notes", []):
            L.append(f"- 备注：{n}")
    else:
        L.append("- 该品类暂无结构化认证数据")
    L.append("\n## 三、到岸成本")
    if cost_info:
        L.append(f"- 申报货值：${cost_info['declared_value_usd']:,.2f}")
        for k, v in cost_info["breakdown"].items():
            L.append(f"- {k}：${v:,.2f}")
        L.append(f"- 到岸总成本：${cost_info['total_landed_usd']:,.2f}")
        L.append(f"- 单件成本：${cost_info['unit_landed_usd']:,.2f}")
        L.append(f"- 说明：{cost_info['estimate_warning']}")
    L.append("\n## 四、风险提示")
    if risks:
        for r in risks:
            L.append(f"- {r['severity']} {r['type']}：{r['message']} → {r['suggestion']}")
    else:
        L.append("- 无产品级风险提示")
    L.append("\n## 五、三国有效关税对比")
    for c in ALL_COUNTRIES:
        t = compare.get(c)
        if t and t.get("in_scope"):
            L.append(f"- {c}：{t['effective_pct']}%（{t['source_url']}）")
        else:
            L.append(f"- {c}：未覆盖")
    L.append("\n> 本报告由帆朵自动生成。数字分级：✅确定 / ⚠️估算 / ❓需核实，以官方海关实时为准。")
    return "\n".join(L)

report_md = _md_report()
st.download_button("⬇️ 下载体检报告 (.md)", data=report_md,
                   file_name=f"fanduo_checkup_{hs_code.replace('.', '')}.md", mime="text/markdown")
