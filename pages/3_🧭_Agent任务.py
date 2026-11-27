"""Agent 任务页：给「目标」而非「问题」，实时看 Agent 一步步干活，产出交付报告。

与「主对话」的区别：这里是任务执行视图——表单提交目标 → 实时显示每一步工具调用
→ 产出可下载的结构化报告 + 人工确认闸口。证明「AI 在干活」，而不是一问一答。
"""
import json
import os
import time

import streamlit as st

from agent import stream_agent

st.set_page_config(page_title="帆朵 · Agent 任务", page_icon="🧭", layout="wide")

# —— 密码门（与主应用一致）——
PASSWORD = ""
try:
    PASSWORD = st.secrets.get("APP_PASSWORD", "")
except Exception:
    PASSWORD = ""
if not PASSWORD:
    PASSWORD = os.getenv("APP_PASSWORD", "")
if PASSWORD and not st.session_state.get("authed"):
    st.title("🔐 帆朵 · Agent 任务")
    with st.form("login_task"):
        pwd = st.text_input("访问密码", type="password")
        if st.form_submit_button("进入"):
            if pwd == PASSWORD:
                st.session_state["authed"] = True
                st.rerun()
            else:
                st.error("密码错误")
    st.stop()

st.title("🧭 Agent 任务")
st.caption("给一个目标，Agent 自己规划、调用工具、产出报告。你看到的每一步都是它自己决定的，不是写死的流程。")


def _build_task(product, destination, platform, quantity, unit_value, mode, has_lithium, goal):
    return (
        f"【任务目标】{goal}\n"
        f"产品：{product}；目的国：{destination}；平台：{platform}；"
        f"数量：{quantity} 件；单价：${unit_value}；物流方式：{mode}；"
        f"{'含锂电池' if has_lithium else '不含锂电池'}。\n\n"
        f"请你自己决定调用哪些工具完成分析，不要走固定流程。"
        f"含锂电池时必须额外查危险品运输。最后输出一份结构化报告，包含：\n"
        f"1. 结论（能否发货：GO / 需补证 / NO-GO，说明理由）\n"
        f"2. 合规清单（强制项/建议项，带法规编号和跳过后果）\n"
        f"3. 关税与到岸成本（带来源和更新时间）\n"
        f"4. 风险与阻断项\n"
        f"5. 补齐路径（下一步该做什么）\n"
        f"数字必须标置信度，查不到就老实说需联网核实，不要编造。"
    )


with st.form("task_form"):
    c1, c2 = st.columns(2)
    with c1:
        product = st.text_input("产品", value="儿童声光电动早教玩具")
        destination = st.selectbox("目标市场", ["美国", "印度", "俄罗斯"])
        platform = st.selectbox("渠道/平台", ["Amazon", "独立站", "TikTok Shop", "其他"])
        quantity = st.number_input("数量", min_value=1, value=500)
    with c2:
        unit_value = st.number_input("单品申报价值(USD)", min_value=0.01, value=15.0)
        mode = st.selectbox("物流方式", ["FBA大批量", "直邮小包", "海运", "空运", "陆运"])
        has_lithium = st.toggle("含锂电池", value=True)
    goal = st.text_input(
        "任务目标",
        value="帮我把「儿童声光电动早教玩具」推进到「美国」市场，判断现在能否发货，并给出补齐路径",
    )
    submitted = st.form_submit_button("🚀 启动 Agent 任务", width="stretch")

if submitted:
    task = _build_task(product, destination, platform, quantity, unit_value, mode, has_lithium, goal)

    step_ph = st.empty()
    report_ph = st.empty()
    trace = []
    full = []
    error = None

    try:
        for ev in stream_agent(task, []):
            if ev["type"] == "tool":
                trace.append(ev)
                chain = " → ".join(f"`{t['tool']}`" for t in trace)
                step_ph.markdown(f"**🔍 Agent 正在执行第 {len(trace)} 步：** {chain}")
                time.sleep(0.4)  # 让每一步的执行状态可见
            elif ev["type"] == "text":
                full.append(ev["text"])
    except Exception as exc:  # noqa: BLE001
        error = str(exc)

    if error:
        step_ph.error(f"😥 执行失败：{error}（可能是网络波动，请重试）")
    else:
        step_ph.markdown(f"✅ Agent 自主执行完成，共 {len(trace)} 步")

    # —— 执行过程（任务看板式：每一步 + 参数 + 结果）——
    if trace:
        st.markdown("### 📋 执行过程（Agent 自己走的每一步）")
        for i, t in enumerate(trace, 1):
            with st.expander(f"步骤 {i} · `{t['tool']}`", expanded=(i == len(trace))):
                st.caption(f"模型 {t.get('provider', '?')}")
                st.code(
                    json.dumps({"参数": t.get("args"), "结果": t.get("result")},
                               ensure_ascii=False, indent=2)[:3000],
                    language="json",
                )

    # —— 交付报告 ——
    report = "".join(full)
    if report:
        st.markdown("### 📄 交付报告")
        st.markdown(report)
        st.download_button(
            "⬇️ 下载报告(.md)", data=report,
            file_name="帆朵出海任务报告.md", mime="text/markdown",
        )
        st.info("⚠️ 以上为 AI 分析建议；上架、发货、报关等高风险操作需人工确认后再执行，Agent 不会自动执行。")
