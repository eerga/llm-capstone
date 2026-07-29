# 🎬 Movie Assistant

Still scrolling for over an hour on Netflix hoping to find something to watch? Your pursuit is over. Movie Assistant is a RAG-powered chatbot that knows what you're in the mood for — just describe it, and it'll find THE movie you'll actually watch and love.

Ask it things like _"mind-bending sci-fi like Inception"_, _"something funny but not stupid"_, or _"best Coen Brothers films"_ and it retrieves relevant movies from a 2000-title TMDB dataset and synthesises a grounded recommendation — no hallucinated titles, no generic lists.

> **Note:** This is a capstone project for the [LLM Zoomcamp 2026](https://github.com/DataTalksClub/llm-zoomcamp) course. It is not for profit and is open for testing.

---

## Demo Video

_(add YouTube video link here)_

---

## The Data

Movie data is fetched directly from the [TMDB API](https://developer.themoviedb.org/docs/getting-started) — no manual downloads needed. Register for a free API key to run the ingestion pipeline yourself.

| Field | Description |
|---|---|
| `title` | Movie title |
| `overview` | Plot summary |
| `genres` | Comma-separated list (e.g. "Action, Thriller") |
| `keywords` | Thematic tags (e.g. "time travel, dystopia") |
| `tagline` | Marketing one-liner |
| `vote_average` | TMDB rating (0–10) |
| `release_year` | Year of release |
| `runtime` | Length in minutes |

**~2000 movies** are retrieved with the following fields:

When you type a question, the system:

1. **Searches** the movie database using a hybrid of two methods:
   - **minsearch (TF-IDF)** — exact keyword matching, fast and precise for titles and genres
   - **FAISS (Facebook AI Similarity Search)** — semantic similarity using sentence embeddings, finds movies that *feel* similar even without exact word matches
   - **Reciprocal Rank Fusion (RRF)** — combines both rankings so you get the best of exact and semantic search
2. **Builds context** from the top results (title, genres, overview, rating)
3. **Asks an LLM** to synthesise a grounded, conversational recommendation using only the retrieved movies
4. **Scores the answer** with an LLM judge (RELEVANT / PARTLY_RELEVANT / NON_RELEVANT) for monitoring
5. **Collects your feedback** — after each answer you can give a 👍 or 👎 to help track recommendation quality

---

## Architecture

| Layer | Technology | Notes |
|---|---|---|
| Search | minsearch + FAISS + RRF | Hybrid: exact + semantic, combined via RRF |
| Embeddings | `sentence-transformers/all-MiniLM-L6-v2` | Best performer across 2 models tested |
| LLMs | `gpt-5.6-luna`, `gpt-5.4-mini` | 2 models compared via LLM-as-judge |
| Prompt variants | A (Claude-authored), B (ChatGPT-authored) | A/B tested — B wins by ~5% RELEVANT |
| Pipeline typing | pydantic-ai | Typed `RAGResponse` model |
| UI | Streamlit | Calls RAG pipeline directly; no Flask needed for the UI |
| API | Flask | Optional — for programmatic/curl access to the same pipeline |
| Storage | PostgreSQL 16 (local) or [Neon](https://neon.tech) (cloud) | Free serverless Postgres |
| Monitoring | Grafana (local Docker or [Grafana Cloud](https://grafana.com) free tier) | 7-panel dashboard |
| Ingestion | **Option A — Python script:** `data/fetch_movies.py` → `notebooks/01-data-prep.ipynb` → `data/movies_clean.csv` | Manual, run once |
| Ingestion | **Option B — Kestra:** automated weekly flow → `data/movies_clean_kestra.csv` (see [Ingestion Pipeline](#ingestion-pipeline-kestra)) | Scheduled, no manual steps |

---

## Ingestion Pipeline (Kestra)

Movie data is fetched and cleaned automatically via a [Kestra](https://kestra.io) workflow (`kestra/flows/movie_ingestion.yaml`):

1. Fetches ~2000 movies from the TMDB API (`/discover/movie`)
2. Enriches each with genres, keywords, runtime, tagline via `/movie/{id}`
3. Cleans and normalizes fields → outputs `movies_clean_kestra.csv`

The flow runs on a **weekly schedule** (Sunday 3am) and can be triggered manually.

```bash
make kestra-up      # start Kestra at http://localhost:8080
make kestra-ingest  # trigger the flow
make kestra-copy    # download output CSV to data/
```

![Kestra Ingestion](img/kestra_log.png)

---

## Evaluation

### How ground truth was generated

For each of 2000 movies, an LLM generated 3 natural user questions that would make that movie a relevant answer. This produced **6000 ground-truth pairs** per model, used to benchmark retrieval quality.

```
notebooks/03-evaluation-data-generation.ipynb → ground-truth-retrieval-{model}.csv
```

### Retrieval evaluation

Hit Rate and MRR measured across 4 methods × 2 embedding models × 2 ground truth sources:

| GT model | Embedding | Method | Hit Rate | MRR |
|---|---|---|---|---|
| gpt-5.6-luna | all-MiniLM-L6-v2 | **rrf** | **0.609** | **0.381** |
| gpt-5.6-luna | all-MiniLM-L6-v2 | faiss | 0.597 | 0.386 |
| gpt-5.6-luna | multi-qa-MiniLM-L6-cos-v1 | rrf | 0.582 | 0.361 |
| gpt-5.6-luna | multi-qa-MiniLM-L6-cos-v1 | faiss | 0.556 | 0.357 |
| gpt-5.4-mini | all-MiniLM-L6-v2 | rrf | 0.553 | 0.333 |
| gpt-5.4-mini | all-MiniLM-L6-v2 | faiss | 0.541 | 0.338 |
| gpt-5.4-mini | multi-qa-MiniLM-L6-cos-v1 | rrf | 0.532 | 0.311 |
| gpt-5.4-mini | multi-qa-MiniLM-L6-cos-v1 | faiss | 0.506 | 0.315 |
| gpt-5.6-luna | all-MiniLM-L6-v2 | minsearch | 0.388 | 0.193 |
| gpt-5.6-luna | multi-qa-MiniLM-L6-cos-v1 | minsearch | 0.388 | 0.193 |
| gpt-5.4-mini | all-MiniLM-L6-v2 | minsearch | 0.349 | 0.170 |
| gpt-5.4-mini | multi-qa-MiniLM-L6-cos-v1 | minsearch | 0.349 | 0.170 |

**Winner: RRF + `all-MiniLM-L6-v2`** — best hit rate (0.609); used as the production default.

### Boost tuning

Minsearch boost weights were tuned over 64 combinations on 500 ground truth questions:

| | title | keywords | overview | Hit Rate | MRR |
|---|---|---|---|---|---|
| Default | 3.0 | 2.0 | 1.5 | 0.334 | 0.163 |
| **Tuned** | **1.0** | **2.0** | **2.0** | **0.620** | **0.409** |

Overview and keywords matter more than title for movie retrieval.

### LLM-as-judge evaluation

200 questions evaluated per combination (2 models × 2 prompts = 800 RAG calls):

| Model | Prompt | RELEVANT% | PARTLY_RELEVANT% | NON_RELEVANT% | Cost |
|---|---|---|---|---|---|
| gpt-5.6-luna | B | **77.5%** | 22.0% | 0.5% | $0.27 |
| gpt-5.4-mini | B | 75.0% | 24.5% | 0.5% | $0.17 |
| gpt-5.6-luna | A | 72.0% | 26.5% | 1.5% | $0.29 |
| gpt-5.4-mini | A | 69.0% | 31.0% | 0.0% | $0.18 |

**Prompt B consistently outperforms Prompt A.** `gpt-5.4-mini + Prompt B` offers the best cost/quality trade-off.

---

## Local Setup (Path A)

Everything runs on your machine via Docker Compose.

### Prerequisites

- Python 3.12+
- [uv](https://docs.astral.sh/uv/getting-started/installation/)
- Docker + Docker Compose

### Steps

```bash
# 1. Clone and install
git clone https://github.com/eerga/llm-capstone.git
uv lock && uv sync

# 2. Configure environment
cp .envrc_template .envrc
# Fill in OPENAI_API_KEY and TMDB_API_KEY
source .envrc

# 3. Fetch and prepare data
python data/fetch_movies.py
# Then run notebooks/01-data-prep.ipynb → writes data/movies_clean.csv

# 4. Start all services (Postgres + Flask API + Grafana)
make up

# 5. Bootstrap Grafana (first time only)
make grafana

# 6. Run the UI
make streamlit
# Open http://localhost:8501
```

### Screenshots

![Streamlit UI](img/streamlit.png)

![Grafana Dashboard (local)](img/Grafana_dashboard.png)

---

## 🌐 Cloud Setup (Path B)

Run the UI on Streamlit Community Cloud, store data in Neon Postgres, and monitor via Grafana Cloud — all free tiers.

> ⚠️ **Disclaimer:** The live demo links below are running on free trial tiers (set up 2026-07-27) and are intended for demonstration purposes only. They may stop working after approximately 14 days or when free tier limits are reached. This is a capstone project and is not maintained as a production service.

### Neon Postgres (free serverless Postgres)

1. Sign up at [neon.tech](https://neon.tech) → create a project (Postgres 16, US East)
2. Copy the connection string: `postgresql://user:password@host/dbname?sslmode=require`
3. Add to `.envrc`: `DATABASE_URL="your_connection_string"`
4. Initialize schema:
   ```bash
   python -m movie_assistant.db_prep
   ```

**View your data in Neon:**

Tables view:

![Conversations Table](img/conversations_table.png)
![Feedback Table](img/feedback_table.png)

SQL Editor:

![Conversations SQL Editor](img/conversations_sql_editor.png)
![Feedback SQL Editor](img/feedback_sql_editor.png)

```sql
-- Recent conversations
SELECT timestamp, question, relevance, openai_cost FROM conversations ORDER BY timestamp DESC LIMIT 10;

-- Feedback
SELECT c.question, f.feedback, f.timestamp
FROM feedback f JOIN conversations c ON f.conversation_id = c.id
ORDER BY f.timestamp DESC LIMIT 10;
```

### Grafana Cloud (free tier)

1. Sign up at [grafana.com](https://grafana.com) → free tier
2. **Connections → Data Sources → Add → PostgreSQL**:
   - Host: `<your-neon-host>:5432`
   - Database: `neondb` / User: `neondb_owner`
   - Password: your Neon password / SSL Mode: `require`
   - Name: `MovieAssistantDB` (must match exactly)
3. **Save & Test** → green ✓
4. **Dashboards → Import → Upload JSON** → select `grafana/dashboard.json`

![Grafana Cloud](img/grafana_cloud.png)

### Streamlit Community Cloud

1. Go to [share.streamlit.io](https://share.streamlit.io) → **New app**
2. Select repo `eerga/llm-capstone` → main file: `streamlit_app.py`
3. **Advanced settings** → Python `3.12` → Secrets:
   ```toml
   OPENAI_API_KEY = "your_openai_key"
   DATABASE_URL = "postgresql://user:password@host/dbname?sslmode=require"
   ```
4. **Deploy**

### Run locally with Neon

```bash
make streamlit-cloud
# Loads DATABASE_URL from .envrc → writes to Neon
```

---

## Live Demo

| Service | URL | Notes |
|---|---|---|
| Streamlit UI | [movie-recommend67.streamlit.app](https://movie-recommend67.streamlit.app) | May expire after ~14 days |
| Grafana Dashboard | [wisemullet536.grafana.net](https://wisemullet536.grafana.net/d/movie-assistant/movie-assistant?orgId=1&from=now-6h&to=now&timezone=browser&refresh=30s) | May expire after ~14 days |
| Database | [Neon Postgres](https://neon.tech) — `ep-steep-king-awasy5fu.c-12.us-east-1.aws.neon.tech` | Free tier |

---

## Makefile Targets

```bash
make help  # show all targets
```

| Target | What it does |
|---|---|
| `make up` | Build and start all Docker services (detached) |
| `make down` | Stop all services |
| `make streamlit` | Run Streamlit UI locally (http://localhost:8501) |
| `make streamlit-cloud` | Run Streamlit UI with Neon Postgres |
| `make grafana` | Bootstrap Grafana datasource + dashboard |
| `make test` | Send a test question to the Flask API |
| `make kestra-up` | Start Kestra + its Postgres (http://localhost:8080) |
| `make kestra-ingest` | Trigger the movie ingestion flow |
| `make kestra-copy` | Download Kestra-generated CSV to `data/` |
| `make restart` | `down` + `up` + `grafana` |

---

## Cleanup

```bash
make down
```

Stops all Docker services (app, Postgres, Grafana, Kestra). Data in named volumes is preserved — run `docker volume rm llm-capstone_postgres_data` to wipe the local database.

---

## API

The Flask API runs locally at `http://localhost:5000` when `make up` is active.

```bash
# Ask a question
curl -X POST http://localhost:5000/question \
  -H 'Content-Type: application/json' \
  -d '{"question": "sci-fi films with time travel"}'

# Submit feedback
curl -X POST http://localhost:5000/feedback \
  -H 'Content-Type: application/json' \
  -d '{"conversation_id": "<id>", "feedback": 1}'
```

Override model or prompt per-request:
```json
{"question": "...", "model": "gpt-5.4-mini", "prompt_version": "b"}
```
