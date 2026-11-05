"""Streamlit 前端：评委交互窗口 + 流式输出 + 推理过程可视化。"""
import json
import os

import streamlit as st

from agent import stream_agent
from providers import PROVIDERS

st.set_page_config(page_title="跨境出海合规&成本测算 Agent", page_icon="🚢", layout="wide")

# —— 可选访问密码：Streamlit Cloud Secrets 或本地 .env 配 APP_PASSWORD ——
PASSWORD = ""
try:
    PASSWORD = st.secrets.get("APP_PASSWORD", "")
except Exception:
    PASSWORD = ""
if not PASSWORD:
    PASSWORD = os.getenv("APP_PASSWORD", "")

if PASSWORD and not st.session_state.get("authed"):
    st.title("🔐 跨境出海合规 & 成本测算 Agent")
    with st.form("login"):
        pwd = st.text_input("访问密码", type="password")
        if st.form_submit_button("进入"):
            if pwd == PASSWORD:
                st.session_state["authed"] = True
                st.rerun()
            else:
                st.error("密码错误")
    st.stop()

st.title("🚢 跨境出海合规 & 成本测算 Agent")
st.caption("当前案例：美国 · 儿童声光电动早教玩具（数据为整理资料，正式版接官方法规/税率）")

if not any(p["api_key"] for p in PROVIDERS):
    st.error("⚠️ 尚未配置任何 LLM API Key。请在 Streamlit Cloud 的 Secrets 配置 DEEPSEEK_API_KEY。")
    st.stop()

if "history" not in st.session_state:
    st.session_state.history = []

EXAMPLES = [
    "500件早教玩具(单价15美元,含锂电池)卖到美国，算合规与到岸成本",
    "美国进口玩具的关税分几层构成？",
    "跳过CPC认证直接发货会有什么后果？",
    "换电池供应商需要重新做哪些认证？",
]


def copy_button(text: str):
    """复制按钮：json 安全转义后写进 JS（HTTPS 下 navigator.clipboard 可用）。"""
    payload = json.dumps(text)
    st.markdown(
        f'<button onclick="navigator.clipboard.writeText({payload})" '
        f'style="font-size:0.85rem;padding:2px 12px;border:1px solid #888;border-radius:6px;'
        f'background:transparent;cursor:pointer;">📋 复制</button>',
        unsafe_allow_html=True,
    )


# —— 渲染历史 ——
for m in st.session_state.history:
    with st.chat_message(m["role"]):
        st.markdown(m["content"])

# —— 工具条：清空对话 + 记忆指示 ——
c_clear, c_info = st.columns([1, 3])
with c_clear:
    if st.button("🗑️ 清空对话"):
        st.session_state.history = []
        st.rerun()
with c_info:
    st.caption(f"💬 已对话 {len(st.session_state.history) // 2} 轮（超长自动裁剪上下文）")

# —— 预设示例（仅无历史时显示）——
clicked = None
if not st.session_state.history:
    st.markdown("**💡 试试这些：**")
    cols = st.columns(len(EXAMPLES))
    for i, ex in enumerate(EXAMPLES):
        if cols[i].button(ex, key=f"ex{i}"):
            clicked = ex

user_input = st.chat_input("输入你的问题，例如：我想把 500 个充电宝卖到美国…")

msg = user_input or clicked
if msg:
    prior = [{"role": m["role"], "content": m["content"]} for m in st.session_state.history]
    st.session_state.history.append({"role": "user", "content": msg})

    with st.chat_message("user"):
        st.markdown(msg)

    with st.chat_message("assistant"):
        status = st.empty()
        status.markdown("🤔 思考中…")
        answer_ph = st.empty()
        full = []
        trace = []
        provider = "?"
        usage = None

        for ev in stream_agent(msg, prior):
            if ev["type"] == "tool":
                trace.append(ev)
                status.markdown("🔍 推理中：" + " → ".join(f"`{t['tool']}`" for t in trace))
            elif ev["type"] == "text":
                full.append(ev["text"])
                answer_ph.markdown("".join(full))
            elif ev["type"] == "done":
                provider = ev.get("provider", "?")
                usage = ev.get("usage")

        status.empty()
        final = "".join(full)
        answer_ph.markdown(final)

        meta = f"🤖 模型：{provider}"
        if usage and usage.get("total"):
            meta += f" · 本次约 {usage['total']} token"
        st.caption(meta)

        c_copy, c_dl = st.columns(2)
        with c_copy:
            copy_button(final)
        with c_dl:
            st.download_button(
                "⬇️ 导出报告 (.md)", data=final, file_name="chuhai_report.md",
                mime="text/markdown",
            )

        if trace:
            with st.expander(f"🔍 推理过程（{len(trace)} 步）"):
                for t in trace:
                    st.markdown(f"**步骤 {t['step']}** · 模型 `{t['provider']}` · 工具 `{t['tool']}`")
                    st.json({"参数": t["args"], "结果": t["result"]})

    st.session_state.history.append({"role": "assistant", "content": final})
