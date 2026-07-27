"""
PostgreSQL helpers — all reads and writes for conversations and feedback.
"""

import os
from datetime import datetime, timezone
from urllib.parse import urlparse

import psycopg2
from psycopg2.extras import DictCursor

_DATABASE_URL = os.getenv("DATABASE_URL")
if _DATABASE_URL:
    _p = urlparse(_DATABASE_URL)
    DSN = {
        "host": _p.hostname,
        "port": _p.port or 5432,
        "dbname": _p.path.lstrip("/"),
        "user": _p.username,
        "password": _p.password,
    }
else:
    DSN = {
        "host": os.getenv("POSTGRES_HOST", "localhost"),
        "port": int(os.getenv("POSTGRES_PORT", "5432")),
        "dbname": os.getenv("POSTGRES_DB", "movie_assistant"),
        "user": os.getenv("POSTGRES_USER", "postgres"),
        "password": os.getenv("POSTGRES_PASSWORD", ""),
    }


def _conn():
    return psycopg2.connect(**DSN)


def save_conversation(conversation_id: str, question: str, answer_data: dict):
    with _conn() as conn, conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO conversations
                (id, question, answer, model, prompt_version, search_method,
                 relevance, tokens_prompt, tokens_completion, total_tokens,
                 openai_cost, response_time, timestamp)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                conversation_id,
                question,
                answer_data["answer"],
                answer_data.get("model", ""),
                answer_data.get("prompt_version", "a"),
                answer_data.get("search_method", "rrf"),
                answer_data.get("relevance", "UNKNOWN"),
                answer_data.get("tokens_prompt", 0),
                answer_data.get("tokens_completion", 0),
                answer_data.get("tokens_prompt", 0) + answer_data.get("tokens_completion", 0),
                answer_data.get("cost", 0.0),
                answer_data.get("response_time", 0.0),
                datetime.now(timezone.utc),
            ),
        )


def save_feedback(conversation_id: str, feedback: int):
    with _conn() as conn, conn.cursor() as cur:
        cur.execute(
            "INSERT INTO feedback (conversation_id, feedback, timestamp) VALUES (%s, %s, %s)",
            (conversation_id, feedback, datetime.now(timezone.utc)),
        )


def get_recent_conversations(limit: int = 5) -> list[dict]:
    with _conn() as conn, conn.cursor(cursor_factory=DictCursor) as cur:
        cur.execute(
            "SELECT * FROM conversations ORDER BY timestamp DESC LIMIT %s", (limit,)
        )
        return [dict(r) for r in cur.fetchall()]
