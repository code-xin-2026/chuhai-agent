"""Streamlit 前端：评委交互窗口 + 智能体推理过程可视化。"""
import os

import streamlit as st

from agent import run_agent
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
    st.error("⚠️ 尚未配置任何 LLM API Key。请在 Streamlit Cloud 的 Secrets（或本地 .env）配置 DEEPSEEK_API_KEY。")
    st.stop()

if "history" not in st.session_state:
    st.session_state.history = []

for m in st.session_state.history:
    with st.chat_message(m["role"]):
        st.markdown(m["content"])

user_input = st.chat_input("例如：我想把 500 个儿童声光电动早教玩具（单价 15 美元，含锂电池）卖到美国，算一下两种走货方式的合规与成本")
if user_input:
    prior = [{"role": m["role"], "content": m["content"]} for m in st.session_state.history]
    st.session_state.history.append({"role": "user", "content": user_input})

    with st.chat_message("user"):
        st.markdown(user_input)

    with st.chat_message("assistant"):
        with st.spinner("思考中…"):
            answer, trace = run_agent(user_input, prior)
        st.markdown(answer)
        if trace:
            with st.expander(f"🔍 智能体推理过程（{len(trace)} 步）"):
                for t in trace:
                    st.markdown(f"**步骤 {t['step']}** · 模型：`{t['provider']}` · 工具：`{t['tool']}`")
                    st.json({"参数": t["args"], "结果": t["result"]})

    st.session_state.history.append({"role": "assistant", "content": answer})
