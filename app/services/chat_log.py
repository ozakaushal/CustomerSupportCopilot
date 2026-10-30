import json
import os
import sqlite3
from datetime import datetime
from app.core.config import get_settings

settings = get_settings()


# creates the chat_log table if it is not already there
def create_table():
    os.makedirs(os.path.dirname(settings.chat_log_db), exist_ok=True)
    con = sqlite3.connect(settings.chat_log_db)
    con.execute("""
        CREATE TABLE IF NOT EXISTS chat_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            asked_at TEXT,
            question TEXT,
            answered_by TEXT,
            steps TEXT
        )
    """)
    con.commit()
    con.close()


# saves one question and how it was answered
def log_chat(question, answered_by, steps):
    con = sqlite3.connect(settings.chat_log_db)
    con.execute(
        "INSERT INTO chat_log (asked_at, question, answered_by, steps) VALUES (?, ?, ?, ?)",
        (datetime.now().isoformat(), question, answered_by, json.dumps(steps)),
    )
    con.commit()
    con.close()


# returns the latest questions from the log
def recent_chats(limit=20):
    con = sqlite3.connect(settings.chat_log_db)
    rows = con.execute(
        "SELECT asked_at, question, answered_by, steps FROM chat_log ORDER BY id DESC LIMIT ?",
        (limit,),
    ).fetchall()
    con.close()

    result = []
    for row in rows:
        result.append({
            "asked_at": row[0],
            "question": row[1],
            "answered_by": row[2],
            "steps": json.loads(row[3]),
        })
    return result
