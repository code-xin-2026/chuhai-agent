"""访问者身份：每个浏览器一个唯一 client_id（cookie 持久化），用于隔离各自的历史会话。"""
import uuid

import streamlit as st
import streamlit.components.v1 as components

COOKIE_NAME = "chuhai_client_id"


def get_client_id():
    """返回当前访问者的唯一 ID。

    - 已在本次会话内缓存 → 直接用；
    - 否则读 cookie（同一浏览器再次访问能拿回原 ID，历史可见）；
    - 都没有 → 生成新 ID，并通过 JS 写入 cookie（下次访问生效）。
    """
    if "client_id" in st.session_state:
        return st.session_state.client_id

    cid = ""
    try:
        cid = st.context.cookies.get(COOKIE_NAME, "") or ""
    except Exception:  # noqa: BLE001
        cid = ""

    if not cid:
        cid = uuid.uuid4().hex
        # 写 cookie：max-age 一年；path=/ 保证整站生效
        components.html(
            f"<script>document.cookie='{COOKIE_NAME}={cid};max-age=31536000;path=/';</script>",
            height=0,
        )

    st.session_state.client_id = cid
    return cid
