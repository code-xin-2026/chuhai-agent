"""会话持久化存储（SQLite）：工作区保留历史对话，按访问者(client_id)隔离。"""
import os
import sqlite3
import uuid
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "chat.db")


def _conn():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""CREATE TABLE IF NOT EXISTS conversations (
        id TEXT PRIMARY KEY, title TEXT, created_at TEXT, updated_at TEXT,
        client_id TEXT DEFAULT '')""")
    conn.execute("""CREATE TABLE IF NOT EXISTS messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        conversation_id TEXT, role TEXT, content TEXT, seq INTEGER)""")
    # 迁移：旧库(无 client_id 列)补列；旧数据 client_id=''，对新访问者自动不可见
    cols = [r[1] for r in conn.execute("PRAGMA table_info(conversations)").fetchall()]
    if "client_id" not in cols:
        conn.execute("ALTER TABLE conversations ADD COLUMN client_id TEXT DEFAULT ''")
        conn.commit()
    # 迁移：消息表补 image 列（上传图片的本地路径，供历史重新显示）
    mcols = [r[1] for r in conn.execute("PRAGMA table_info(messages)").fetchall()]
    if "image" not in mcols:
        conn.execute("ALTER TABLE messages ADD COLUMN image TEXT")
        conn.commit()
    return conn


def _now():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def list_conversations(client_id):
    """按最近更新倒序返回「该访问者」的会话列表。"""
    conn = _conn()
    rows = conn.execute(
        "SELECT id, title, updated_at FROM conversations WHERE client_id=? ORDER BY updated_at DESC",
        (client_id,),
    ).fetchall()
    conn.close()
    return [{"id": r[0], "title": r[1], "updated_at": r[2]} for r in rows]


def create_conversation(title="新会话", client_id=""):
    cid = uuid.uuid4().hex[:12]
    now = _now()
    conn = _conn()
    conn.execute(
        "INSERT INTO conversations (id, title, created_at, updated_at, client_id) VALUES (?,?,?,?,?)",
        (cid, title, now, now, client_id),
    )
    conn.commit()
    conn.close()
    return cid


def get_conversation(cid, client_id=None):
    """返回 [{"role","content"}, ...]，按 seq 排序。带 client_id 时校验归属，防止串读他人会话。"""
    conn = _conn()
    if client_id is not None:
        owner = conn.execute(
            "SELECT client_id FROM conversations WHERE id=?", (cid,)
        ).fetchone()
        if owner is None or owner[0] != client_id:
            conn.close()
            return []
    rows = conn.execute(
        "SELECT role, content, image FROM messages WHERE conversation_id=? ORDER BY seq", (cid,)
    ).fetchall()
    conn.close()
    return [{"role": r[0], "content": r[1], "image": r[2]} for r in rows]


def add_message(cid, role, content, image=None):
    conn = _conn()
    seq = conn.execute(
        "SELECT COALESCE(MAX(seq),0)+1 FROM messages WHERE conversation_id=?", (cid,)
    ).fetchone()[0]
    cur = conn.execute("INSERT INTO messages (conversation_id, role, content, seq, image) VALUES (?,?,?,?,?)",
                       (cid, role, content, seq, image))
    conn.execute("UPDATE conversations SET updated_at=? WHERE id=?", (_now(), cid))
    conn.commit()
    mid = cur.lastrowid
    conn.close()
    return mid


def update_message(mid, content):
    """流式生成过程中实时更新某条消息内容（切换会话中断时，已生成部分仍保留）。"""
    conn = _conn()
    conn.execute("UPDATE messages SET content=? WHERE id=?", (content, mid))
    conn.commit()
    conn.close()


def delete_conversation(cid):
    conn = _conn()
    conn.execute("DELETE FROM messages WHERE conversation_id=?", (cid,))
    conn.execute("DELETE FROM conversations WHERE id=?", (cid,))
    conn.commit()
    conn.close()
