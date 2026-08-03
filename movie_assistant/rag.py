"""
RAG pipeline: search → prompt → LLM → judge → cost.

Environment variables:
    LLM_MODEL        — openai or gemini model id (default: gpt-5.6-luna)
    PROMPT_VERSION   — "a" or "b" (default: a)
    SEARCH_METHOD    — "rrf", "minsearch", or "faiss" (default: rrf)

OpenAI models use the Responses API (client.responses.create / responses.parse).
Token fields from that API are input_tokens / output_tokens.
"""

import os
from typing import Literal

from pydantic import BaseModel

import movie_assistant.ingest as ingest

LLM_MODEL = os.getenv("LLM_MODEL", "gpt-5.6-luna")
PROMPT_VERSION = os.getenv("PROMPT_VERSION", "a")
SEARCH_METHOD = os.getenv("SEARCH_METHOD", "rrf")

# Per-provider cost per 1M tokens (prompt, completion) in USD
_COST = {
    "gpt-5.6-luna":     (0.20,  1.20),
    "gpt-5.4-mini":     (0.75,  4.50),
    "gemini-2.0-flash": (0.075, 0.30),
}

# ---------------------------------------------------------------------------
# Prompt templates — A written with Claude, B written with ChatGPT
# ---------------------------------------------------------------------------

_PROMPT_A = """\
You are an expert movie recommender and film critic.
Use ONLY the movie information provided below — do not invent titles or facts.
Answer the user's question conversationally in 2-4 sentences.
If no movie fits well, say so honestly.

Movies:
{context}

Question: {question}
"""

_PROMPT_B = """\
You are a knowledgeable movie assistant. Your job is to help users discover films
they will love based on their preferences. Rely exclusively on the context provided.
Keep your response concise (2-4 sentences) and friendly.
Do not mention movies not listed in the context.

Context:
{context}

User question: {question}
"""

_PROMPTS = {"a": _PROMPT_A, "b": _PROMPT_B}

# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------

class MovieDocument(BaseModel):
    id: int | str
    title: str
    overview: str
    genres: str = ""
    keywords: str = ""
    tagline: str = ""
    vote_average: float = 0.0
    release_year: int | str = ""


class RAGResponse(BaseModel):
    answer: str
    model: str
    prompt_version: str
    search_method: str
    relevance: Literal["RELEVANT", "PARTLY_RELEVANT", "NON_RELEVANT"]
    tokens_prompt: int
    tokens_completion: int
    cost: float


class RelevanceJudgement(BaseModel):
    relevance: Literal["RELEVANT", "PARTLY_RELEVANT", "NON_RELEVANT"]
    explanation: str


# ---------------------------------------------------------------------------
# LLM wrapper — unified interface for OpenAI / Gemini
# ---------------------------------------------------------------------------

def _llm(prompt: str, model: str = LLM_MODEL) -> tuple[str, int, int]:
    """Returns (answer_text, input_tokens, output_tokens)."""
    if model.startswith("gpt") or model.startswith("o"):
        from openai import OpenAI
        client = OpenAI()
        resp = client.responses.create(
            model=model,
            input=[{"role": "user", "content": prompt}],
        )
        return (
            resp.output_text,
            resp.usage.input_tokens,
            resp.usage.output_tokens,
        )

    elif model.startswith("gemini"):
        from google import genai
        client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
        resp = client.models.generate_content(model=model, contents=prompt)
        pt = resp.usage_metadata.prompt_token_count if resp.usage_metadata else 0
        ct = resp.usage_metadata.candidates_token_count if resp.usage_metadata else 0
        return resp.text, pt, ct

    else:
        raise ValueError(f"Unknown model prefix: {model}")


def _calculate_cost(model: str, prompt_tokens: int, completion_tokens: int) -> float:
    prompt_rate, comp_rate = _COST.get(model, (0.0, 0.0))
    return (prompt_tokens * prompt_rate + completion_tokens * comp_rate) / 1_000_000


_JUDGE_INSTRUCTIONS = """\
You are an expert evaluator for a movie RAG system.
Analyze the relevance of the generated answer to the given question.
Classify as RELEVANT, PARTLY_RELEVANT, or NON_RELEVANT.
""".strip()

_JUDGE_PROMPT = "Question: {question}\nGenerated Answer: {answer}"


def _evaluate_relevance(question: str, answer: str) -> RelevanceJudgement:
    from openai import OpenAI
    client = OpenAI()
    prompt = _JUDGE_PROMPT.format(question=question, answer=answer)
    resp = client.responses.parse(
        model=LLM_MODEL,
        input=[
            {"role": "developer", "content": _JUDGE_INSTRUCTIONS},
            {"role": "user", "content": prompt},
        ],
        text_format=RelevanceJudgement,
    )
    return resp.output_parsed


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def search(query: str, method: str = SEARCH_METHOD, num_results: int = 10) -> list[dict]:
    if method == "minsearch":
        return ingest.search_minsearch(query, num_results=num_results)
    elif method == "faiss":
        return ingest.search_faiss(query, num_results=num_results)
    else:
        return ingest.search_rrf(query, num_results=num_results)


def build_prompt(question: str, results: list[dict], version: str = PROMPT_VERSION) -> str:
    context_lines = []
    for r in results:
        context_lines.append(
            f"- {r.get('title','')} ({r.get('release_year','')}) | "
            f"Genres: {r.get('genres','')} | Rating: {r.get('vote_average','')} | "
            f"{r.get('overview','')[:200]}"
        )
    context = "\n".join(context_lines)
    template = _PROMPTS.get(version, _PROMPT_A)
    return template.format(context=context, question=question)


def rag(
    question: str,
    model: str = LLM_MODEL,
    prompt_version: str = PROMPT_VERSION,
    search_method: str = SEARCH_METHOD,
) -> RAGResponse:
    results = search(question, method=search_method)
    prompt = build_prompt(question, results, version=prompt_version)
    answer, pt, ct = _llm(prompt, model=model)
    relevance_judge = _evaluate_relevance(question, answer)
    cost = _calculate_cost(model, pt, ct)

    return RAGResponse(
        answer=answer,
        model=model,
        prompt_version=prompt_version,
        search_method=search_method,
        relevance=relevance_judge.relevance,
        tokens_prompt=pt,
        tokens_completion=ct,
        cost=cost,
    )
