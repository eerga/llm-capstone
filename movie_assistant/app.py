"""
Flask API — two endpoints:
  POST /question   { "question": "...", "model": "...", "prompt_version": "a" }
  POST /feedback   { "conversation_id": "...", "feedback": 1 }
"""

import time
import uuid
from flask import Flask, request, jsonify

from movie_assistant.rag import rag
from movie_assistant.db import save_conversation, save_feedback
from movie_assistant.db_prep import init_db

app = Flask(__name__)

# Initialize DB schema on startup (idempotent — uses CREATE TABLE IF NOT EXISTS)
init_db()


@app.route("/question", methods=["POST"])
def question():
    body = request.get_json(force=True)
    q = body.get("question", "").strip()
    if not q:
        return jsonify({"error": "question is required"}), 400

    model = body.get("model", None)
    prompt_version = body.get("prompt_version", None)
    search_method = body.get("search_method", None)

    kwargs = {}
    if model:
        kwargs["model"] = model
    if prompt_version:
        kwargs["prompt_version"] = prompt_version
    if search_method:
        kwargs["search_method"] = search_method

    start = time.time()
    result = rag(q, **kwargs)
    response_time = time.time() - start

    conversation_id = str(uuid.uuid4())
    data = result.model_dump()
    data["response_time"] = round(response_time, 3)
    save_conversation(conversation_id, q, data)

    return jsonify({
        "conversation_id": conversation_id,
        "question": q,
        "answer": result.answer,
        "model": result.model,
        "relevance": result.relevance,
    })


@app.route("/feedback", methods=["POST"])
def feedback():
    body = request.get_json(force=True)
    conversation_id = body.get("conversation_id", "").strip()
    fb = body.get("feedback")
    if not conversation_id or fb not in (-1, 1):
        return jsonify({"error": "conversation_id and feedback (+1 or -1) required"}), 400
    save_feedback(conversation_id, fb)
    return jsonify({"status": "ok"})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
