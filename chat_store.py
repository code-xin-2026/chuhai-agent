"""会话持久化存储（SQLite）：工作区保留历史对话。"""
import os
import sqlite3
import uuid
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "chat.db")


def _conn():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""CREATE TABLE IF NOT EXISTS conversations (
        id TEXT PRIMARY KEY, title TEXT, created_at TEXT, updated_at TEXT)""")
    conn.execute("""CREATE TABLE IF NOT EXISTS messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        conversation_id TEXT, role TEXT, content TEXT, seq INTEGER)""")
    return conn


def _now():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def list_conversations():
    """按最近更新倒序返回会话列表。"""
    conn = _conn()
    rows = conn.execute(
        "SELECT id, title, updated_at FROM conversations ORDER BY updated_at DESC"
    ).fetchall()
    conn.close()
    return [{"id": r[0], "title": r[1], "updated_at": r[2]} for r in rows]


def create_conversation(title="新会话"):
    cid = uuid.uuid4().hex[:12]
    now = _now()
    conn = _conn()
    conn.execute("INSERT INTO conversations VALUES (?,?,?,?)", (cid, title, now, now))
    conn.commit()
    conn.close()
    return cid


def get_conversation(cid):
    """返回 [{"role","content"}, ...]，按 seq 排序。"""
    conn = _conn()
    rows = conn.execute(
        "SELECT role, content FROM messages WHERE conversation_id=? ORDER BY seq", (cid,)
    ).fetchall()
    conn.close()
    return [{"role": r[0], "content": r[1]} for r in rows]


def add_message(cid, role, content):
    conn = _conn()
    seq = conn.execute(
        "SELECT COALESCE(MAX(seq),0)+1 FROM messages WHERE conversation_id=?", (cid,)
    ).fetchone()[0]
    conn.execute("INSERT INTO messages (conversation_id, role, content, seq) VALUES (?,?,?,?)",
                 (cid, role, content, seq))
    conn.execute("UPDATE conversations SET updated_at=? WHERE id=?", (_now(), cid))
    conn.commit()
    conn.close()


def delete_conversation(cid):
    conn = _conn()
    conn.execute("DELETE FROM messages WHERE conversation_id=?", (cid,))
    conn.execute("DELETE FROM conversations WHERE id=?", (cid,))
    conn.commit()
    conn.close()
