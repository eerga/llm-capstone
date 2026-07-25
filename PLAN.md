# Plan: llm-capstone — Movie Assistant RAG Project

## Context
Building a new end-to-end RAG project for the LLM Zoomcamp capstone. The project is a movie recommendation/Q&A assistant: a user types a natural-language query ("mind-bending sci-fi like Inception", "best Coen Brothers films") and the system retrieves relevant movies from the TMDB dataset, then uses an LLM to synthesize a grounded recommendation.

The reference implementation is `alexeygrigorev/fitness-assistant` — we follow its architecture closely. All 9 evaluation criteria from the course rubric must be covered.

---

## Target Directory
`/Users/I556249/PycharmProjects/llm-capstone/`

---

## Directory Structure

```
llm-capstone/
├── movie_assistant/
│   ├── app.py          # Flask API (POST /question, POST /feedback)
│   ├── rag.py          # RAG pipeline: search → prompt → LLM → judge → cost
│   ├── ingest.py       # Loads data/movies_clean.csv → minsearch + FAISS indexes
│   ├── minsearch.py    # Copy from fitness-assistant (TF-IDF, sklearn)
│   ├── db.py           # psycopg2 read/write (conversations + feedback tables)
│   └── db_prep.py      # One-shot schema initializer
├── data/
│   ├── fetch_movies.py           # Scripted TMDB API fetch (replaces manual Kaggle download)
│   ├── movies_raw.json           # Raw TMDB API response (gitignored)
│   ├── movies_clean.csv          # Post-processed, ready to ingest
│   └── ground-truth-retrieval.csv  # Generated: query → expected movie id
├── notebooks/
│   ├── 01-data-prep.ipynb                   # Explore + clean API data, pick fields
│   ├── 02-rag-test.ipynb                    # Retrieval eval: minsearch vs FAISS vs RRF (Hit Rate + MRR), embedding model comparison
│   ├── 03-evaluation-data-generation.ipynb  # Generate ground truth Q&A pairs via LLM
│   └── 04-rag-eval.ipynb                    # Batch LLM-as-judge: 3 models × 2 prompts
├── grafana/
│   ├── init.py          # Bootstrap Grafana datasource + dashboard via REST API
│   └── dashboard.json   # Dashboard definition (panels query PostgreSQL)
├── docker-compose.yaml
├── Dockerfile
├── pyproject.toml       # uv-managed, Python 3.12
├── .envrc_template      # OPENAI_API_KEY, GEMINI_API_KEY, ANTHROPIC_API_KEY, TMDB_API_KEY, POSTGRES_*, GRAFANA_*
└── README.md
```

---

## Key Design Decisions

### Data Source
Use TMDB API directly via `data/fetch_movies.py` — no manual Kaggle download.
Paginate `/discover/movie` for 2000+ movies, with a follow-up `/movie/{id}` for runtime.

### Models (3)
Controlled by `LLM_MODEL` env var; all called through a thin `llm()` wrapper in `rag.py`:
- `gpt-4o-mini` (OpenAI) — confirm if you have access to `gpt-5.4-mini` and swap
- `gemini-2.0-flash` (Google)
- `claude-haiku-4-5-20251001` (Anthropic)

### Prompts (2)
Controlled by `PROMPT_VERSION` env var (`"a"` or `"b"`):
- Prompt A: written with Claude
- Prompt B: written with ChatGPT
Both defined as constants in `rag.py`. Notebook 04 compares RELEVANT% across both.

### Retrieval (hybrid + RRF)
Three retrieval methods, all evaluated in notebook 02:
1. **minsearch** — TF-IDF keyword search (boost: title high, keywords medium, overview medium)
2. **FAISS** — vector search; compare two embedding models:
   - `sentence-transformers/all-MiniLM-L6-v2`
   - `sentence-transformers/multi-qa-MiniLM-L6-cos-v1`
3. **RRF** — `score(d) = Σ 1/(60 + rank(d))` across minsearch + best FAISS model

### Typing
Use **pydantic-ai** for a typed agent wrapping the full `search → prompt → LLM → judge` pipeline.
`MovieDocument`, `RAGResponse`, and `RelevanceJudgement` are Pydantic models.

---

## Implementation Steps

### 1. Project Bootstrap
- Create directory structure
- Init `pyproject.toml` with uv
- Deps: flask, openai, google-generativeai, anthropic, pydantic-ai, faiss-cpu, sentence-transformers, psycopg2-binary, pandas, scikit-learn, python-dotenv, requests, gunicorn

### 2. Data Fetch (`data/fetch_movies.py`)
- Authenticate with `TMDB_API_KEY`
- Paginate `/3/discover/movie?sort_by=vote_count.desc` for ~20 pages (2000 movies)
- For each: fetch `/3/movie/{id}` for runtime and tagline
- Write `data/movies_raw.json`

### 3. Data Preparation (`notebooks/01-data-prep.ipynb`)
- Load `movies_raw.json`
- Keep: `id`, `title`, `overview`, `genres` (list → comma string), `keywords`, `vote_average`, `release_year`, `runtime`, `tagline`
- Drop rows with empty overview
- Save `data/movies_clean.csv`

### 4. Ingestion (`movie_assistant/ingest.py`)
- Build minsearch index from text fields
- Build FAISS index from embeddings (configurable model via `EMBEDDING_MODEL` env var)
- Both indexes built once at module import, stored in RAM

### 5. RAG Pipeline (`movie_assistant/rag.py`)
- `search(query, method="rrf")` — dispatches to minsearch / FAISS / RRF
- `build_prompt(query, results, version="a")` — selects prompt template A or B
- `llm(prompt, model)` — wraps OpenAI / Gemini / Anthropic with unified interface
- `evaluate_relevance(question, answer)` — LLM judge → RELEVANT/PARTLY_RELEVANT/NON_RELEVANT
- `calculate_cost(model, tokens)` — USD estimate
- `rag(query)` — pydantic-ai typed agent orchestrating all above

### 6. Flask API (`movie_assistant/app.py`)
- `POST /question` → calls `rag()`, saves to DB, returns `{conversation_id, question, answer}`
- `POST /feedback` → saves `+1/-1` to DB

### 7. PostgreSQL (`movie_assistant/db.py` + `db_prep.py`)
Schema: `conversations` + `feedback` tables (identical to fitness-assistant).

### 8. Evaluation Notebooks
- **02**: Hit Rate + MRR for minsearch / FAISS (both embedding models) / RRF on ground truth
- **03**: Generate ~200 ground truth Q&A pairs (3 questions per movie × LLM)
- **04**: Batch LLM-as-judge over 200 pairs — 3 models × 2 prompts → RELEVANT% comparison table

### 9. Grafana (`grafana/init.py` + `dashboard.json`)
Panels: last 5 conversations, feedback pie, relevance gauge, cost over time, token usage, response time, model breakdown.

### 10. Containerization (`docker-compose.yaml` + `Dockerfile`)
Services: `postgres:16`, `app` (gunicorn), `grafana/grafana:latest`.

---

## Rubric Coverage

| Criterion | How covered |
|---|---|
| Problem description | README with problem statement + dataset description |
| Retrieval flow | minsearch + FAISS + RRF + pydantic-ai typed agent in `rag.py` |
| Retrieval evaluation | Hit Rate + MRR × 4 methods in `02-rag-test.ipynb` |
| LLM evaluation | LLM-as-judge: 3 models × 2 prompts in `04-rag-eval.ipynb` |
| Interface | Flask API + CLI client |
| Ingestion pipeline | `ingest.py` — automated at app start |
| Monitoring | Grafana dashboard + feedback endpoint |
| Containerization | `docker-compose.yaml` with all 3 services |
| Reproducibility | README setup instructions, `.envrc_template`, `data/fetch_movies.py`, pinned deps |
| **Bonus** | Hybrid search (RRF) + 2 embedding models + 3 LLMs + 2 prompts |

---

## Verification
1. `python data/fetch_movies.py` → writes `data/movies_raw.json`
2. `docker compose up` → all 3 services healthy
3. `curl -X POST localhost:5000/question -d '{"question": "sci-fi like Interstellar"}'` → returns answer
4. `curl -X POST localhost:5000/feedback -d '{"conversation_id": "...", "feedback": 1}'` → 200 OK
5. Open `localhost:3000` (Grafana) → dashboard shows data
6. `notebooks/02-rag-test.ipynb` → Hit Rate + MRR comparison table
7. `notebooks/04-rag-eval.ipynb` → relevance % by model and prompt version
