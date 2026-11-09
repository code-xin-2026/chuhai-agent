"""Streamlit 前端：评委交互窗口 + 工作区（历史会话）+ 流式输出 + 推理过程可视化。"""
import html
import json
import os

import streamlit as st

import chat_store
import client
from agent import stream_agent
from providers import PROVIDERS
import stt
import vision

st.set_page_config(page_title="帆朵 · 跨境出海助手", page_icon="🚢", layout="wide")


def chat_page():
    # —— 可选访问密码：Streamlit Cloud Secrets 或本地 .env 配 APP_PASSWORD ——
    PASSWORD = ""
    try:
        PASSWORD = st.secrets.get("APP_PASSWORD", "")
    except Exception:
        PASSWORD = ""
    if not PASSWORD:
        PASSWORD = os.getenv("APP_PASSWORD", "")

    if PASSWORD and not st.session_state.get("authed"):
        st.title("🔐 帆朵 · 跨境出海助手")
        with st.form("login"):
            pwd = st.text_input("访问密码", type="password")
            if st.form_submit_button("进入"):
                if pwd == PASSWORD:
                    st.session_state["authed"] = True
                    st.rerun()
                else:
                    st.error("密码错误")
        st.stop()

    if not any(p["api_key"] for p in PROVIDERS):
        st.error("⚠️ 尚未配置任何 LLM API Key。请在 Streamlit Cloud 的 Secrets 配置 DEEPSEEK_API_KEY。")
        st.stop()

    # —— 访问者身份：每个浏览器一个唯一 ID（cookie 持久化），隔离各自历史 ——
    client_id = client.get_client_id()

    # —— 会话初始化：默认载入最近一次会话 ——
    if "current_id" not in st.session_state:
        convs = chat_store.list_conversations(client_id)
        st.session_state.current_id = convs[0]["id"] if convs else None

    EXAMPLES = [
        "500件早教玩具(单价15美元,含锂电池)卖到美国，算合规与到岸成本",
        "美国进口玩具的关税分几层构成？",
        "跳过CPC认证直接发货会有什么后果？",
        "换电池供应商需要重新做哪些认证？",
    ]

    WELCOME_MESSAGE = (
        "您好，我是「帆朵」🚢，一名跨境出海合规与成本测算助手。\n\n"
        "我能帮中小卖家/创业者解决这些问题：\n"
        "- 📋 **认证准入**：产品出口到美国/印度/俄罗斯需要什么认证（CPC/FCC/FDA/BIS/EAC 等），带法规编号和跳过后果；\n"
        "- 💰 **关税与到岸成本**：分层税率 + 到岸成本测算，带来源和更新时间；\n"
        "- ⚠️ **风险识别**：制裁、危险品、低报等风险提醒；\n"
        "- 📦 **订单自动处理**：到侧边栏「订单处理」页上传订单表，我自动跑合规 + 成本 + 异常检测。\n\n"
        "您可以直接提问，或上传产品图片让我识别分析。"
    )

    def copy_button(text: str):
        """复制按钮：json 序列化 + HTML 实体转义，避免引号/尖括号破坏 HTML 属性。"""
        payload = html.escape(json.dumps(text, ensure_ascii=False), quote=True)
        st.markdown(
            f'<button onclick="navigator.clipboard.writeText({payload})" '
            f'style="font-size:0.85rem;padding:2px 12px;border:1px solid #888;border-radius:6px;'
            f'background:transparent;cursor:pointer;">📋 复制</button>',
            unsafe_allow_html=True,
        )

    # —— 侧边栏：工作区（历史会话） ——
    with st.sidebar:
        st.header("💬 工作区")
        if st.button("➕ 新建会话", width="stretch"):
            st.session_state.current_id = None
            st.rerun()

        st.divider()
        convs = chat_store.list_conversations(client_id)
        if convs:
            st.caption(f"共 {len(convs)} 个会话")
            for c in convs:
                active = c["id"] == st.session_state.current_id
                label = ("▶ " if active else "") + c["title"]
                if st.button(label, key=f"c_{c['id']}", width="stretch"):
                    st.session_state.current_id = c["id"]
                    st.rerun()
        else:
            st.caption("暂无历史会话，发送第一条消息后会自动保存到这里")

    # —— 主区域 ——
    st.title("🚢 帆朵 · 跨境出海助手")
    st.caption("合规成本测算 + 外贸客服 + 订单自动处理 · 覆盖：美国 / 印度 / 俄罗斯")

    messages = chat_store.get_conversation(st.session_state.current_id, client_id) if st.session_state.current_id else []

    for m in messages:
        with st.chat_message(m["role"]):
            st.markdown(m["content"])

    # —— 预设示例（仅空会话时显示） ——
    clicked = None
    if not messages:
        with st.chat_message("assistant"):
            st.markdown(WELCOME_MESSAGE)
        st.markdown("**💡 试试这些：**")
        cols = st.columns(len(EXAMPLES))
        for i, ex in enumerate(EXAMPLES):
            if cols[i].button(ex, key=f"ex{i}"):
                clicked = ex

    msg = None
    user_image_bytes = None
    from_voice = False

    # —— 聊天输入：文字 + 图片 + 语音（都内置在输入框里）——
    user_input = st.chat_input("输入问题，或直接上传产品图片 / 录音…",
                               accept_file=True, accept_audio=True)
    if user_input is not None:
        d = user_input.to_dict()
        text = d.get("text", "")
        files = d.get("files", [])
        audio = d.get("audio")          # UploadedFile | None（accept_audio=True 时）
        if audio is not None:
            # 语音录音 → 转文字
            with st.spinner("🎤 正在转写语音…"):
                r = stt.transcribe(audio.getvalue(), audio.type or "audio/wav")
            if "error" in r:
                st.error(r["error"])
            else:
                voice_text = r["text"]
                msg = f"{voice_text} {text}".strip() if text else voice_text
                from_voice = True
        elif files:
            f = files[0]
            user_image_bytes = f.getvalue()
            mime = f.type or "image/jpeg"
            with st.spinner("🔍 正在识别产品…"):
                r = vision.identify_product(user_image_bytes, mime)
            if "error" in r:
                st.error(r["error"])
            else:
                desc = r["description"]
                if text:
                    msg = f"我上传了一张产品图片，图片识别结果：\n{desc}\n\n我的问题：{text}"
                else:
                    msg = (f"我上传了一张产品图片，图片识别结果：\n{desc}\n\n"
                           "请基于此帮我分析该产品出口美国的合规要求与关税成本。")
        elif text:
            msg = text

    if msg is None and clicked:
        msg = clicked

    if msg:
        # 新会话 → 先用首条消息做标题建会话
        if st.session_state.current_id is None:
            title = msg[:18] + ("…" if len(msg) > 18 else "")
            st.session_state.current_id = chat_store.create_conversation(title, client_id)
            chat_store.add_message(st.session_state.current_id, "assistant", WELCOME_MESSAGE)
        cid = st.session_state.current_id
        prior = chat_store.get_conversation(cid, client_id)  # 本次之前的历史
        chat_store.add_message(cid, "user", msg)

        with st.chat_message("user"):
            if user_image_bytes is not None:
                st.image(user_image_bytes, caption="上传的产品图片")
            st.markdown(msg)
            if from_voice:
                st.caption("🎤 由语音转写")

        with st.chat_message("assistant"):
            status = st.empty()
            status.markdown("🤔 思考中…")
            answer_ph = st.empty()
            full = []
            trace = []
            provider = "?"
            usage = None
            error_msg = None

            try:
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
            except Exception as e:  # noqa: BLE001
                error_msg = str(e)

            status.empty()
            if error_msg:
                final = "连接模型失败，请稍后重试。"
                answer_ph.error("😥 连接模型失败（可能是网络波动），请稍后重试。")
                st.caption("网络不稳定时可多点几次重试；云端部署版会更稳定。")
            else:
                final = "".join(full)
                answer_ph.markdown(final)

            if not error_msg:
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
                            st.code(json.dumps({"参数": t["args"], "结果": t["result"]},
                                               ensure_ascii=False, indent=2), language="json")

        chat_store.add_message(cid, "assistant", final)
        st.rerun()


pg = st.navigation([
    st.Page(chat_page, title="主对话", icon="💬", default=True),
    st.Page("pages/1_📦_订单处理.py", title="订单处理", icon="📦"),
])
pg.run()
