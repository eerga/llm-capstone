"""
One-shot schema initializer. Run once before starting the app:
    python -m movie_assistant.db_prep
"""

import psycopg2
from movie_assistant.db import DSN


def init_db():
    with psycopg2.connect(**DSN) as conn, conn.cursor() as cur:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS conversations (
                id                TEXT PRIMARY KEY,
                question          TEXT NOT NULL,
                answer            TEXT NOT NULL,
                model             TEXT,
                prompt_version    TEXT,
                search_method     TEXT,
                relevance         TEXT,
                tokens_prompt     INTEGER,
                tokens_completion INTEGER,
                total_tokens      INTEGER,
                openai_cost       FLOAT,
                response_time     FLOAT,
                timestamp         TIMESTAMPTZ NOT NULL
            );

            CREATE TABLE IF NOT EXISTS feedback (
                id              SERIAL PRIMARY KEY,
                conversation_id TEXT REFERENCES conversations(id),
                feedback        INTEGER NOT NULL CHECK (feedback IN (-1, 1)),
                timestamp       TIMESTAMPTZ NOT NULL
            );
        """)
    print("Schema initialized.")


if __name__ == "__main__":
    init_db()
