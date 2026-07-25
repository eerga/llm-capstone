# Movie Assistant

A RAG-powered movie recommendation chatbot built for the LLM Zoomcamp capstone.

Ask it natural language questions like _"mind-bending sci-fi like Inception"_ or _"best Coen Brothers films"_ and it retrieves relevant movies from a TMDB dataset and synthesises a grounded recommendation.

---

## Architecture

| Layer | Technology |
|---|---|
| Search | minsearch (TF-IDF) + FAISS (vector) + Reciprocal Rank Fusion |
| Embeddings | `sentence-transformers/all-MiniLM-L6-v2` (best performer; see retrieval eval) |
| LLMs | `gpt-5.6-luna`, `gpt-5.4-mini` |
| Prompt variants | A (Claude-authored), B (ChatGPT-authored) — compared in eval |
| Pipeline typing | pydantic-ai |
| UI | Streamlit |
| API | Flask |
| Storage | PostgreSQL 16 |
| Monitoring | Grafana |
| Infra | Docker Compose + Makefile |

---

## Quickstart (fresh clone)

### 1. Prerequisites

- Python 3.12+
- [uv](https://docs.astral.sh/uv/getting-started/installation/)
- Docker + Docker Compose

### 2. Clone and install

```bash
git clone <repo-url>
cd llm-capstone
uv sync
```

### 3. Configure environment

```bash
cp .envrc_template .envrc
```

Edit `.envrc` and fill in:

```
OPENAI_API_KEY=your_openai_key
TMDB_API_KEY=your_tmdb_key
```

Then load it:

```bash
source .envrc
```

### 4. Fetch and prepare movie data

```bash
# Fetch ~2000 movies from TMDB API → data/movies_raw.json
python data/fetch_movies.py
```

Then run `notebooks/01-data-prep.ipynb` to clean the data and write `data/movies_clean.csv`.

### 5. Start services

```bash
make up
```

This builds and starts PostgreSQL, the Flask app, and Grafana in the background.
The app initializes the DB schema automatically on first boot.

### 6. Bootstrap Grafana

```bash
make grafana
```

Registers the PostgreSQL datasource and posts the dashboard. Only needed once.

### 7. Run the UI

```bash
make streamlit
```

Open [http://localhost:8501](http://localhost:8501) in your browser.

---

## Makefile targets

| Target | What it does |
|---|---|
| `make up` | Build and start all Docker services (detached) |
| `make down` | Stop all services |
| `make streamlit` | Run the Streamlit UI |
| `make grafana` | Bootstrap Grafana datasource + dashboard |
| `make test` | Send a test question to the Flask API |
| `make restart` | `down` + `up` + `grafana` |

---

## Grafana dashboard

Open [http://localhost:3000](http://localhost:3000) — login: `admin` / `admin`.

Panels: last 5 conversations, response time, token usage, cost over time, model usage, relevance distribution, user feedback.

**Manual datasource setup** (if `make grafana` doesn't auto-configure):

1. Go to Configuration → Data Sources → Add data source → PostgreSQL
2. Host: `postgres:5432`
3. Database: `movie_assistant`
4. User: `postgres` / Password: `postgres`
5. SSL Mode: `disable`
6. Save & Test

---

## API

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

---

## Evaluation notebooks

| Notebook | What it does |
|---|---|
| `01-data-prep.ipynb` | Clean TMDB API data → `movies_clean.csv` |
| `02-rag-test.ipynb` | Hit Rate + MRR: minsearch / FAISS / RRF × 2 embedding models × 2 GT files |
| `03-evaluation-data-generation.ipynb` | Generate 6000 ground-truth Q&A pairs per model (chunked, resumable) |
| `04-rag-eval.ipynb` | LLM-as-judge: 2 models × 2 prompts → RELEVANT% comparison table |

### Retrieval evaluation results

Ground truth generated with `gpt-5.4-mini` and `gpt-5.6-luna` (6000 pairs each, 3 questions × 2000 movies).

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

**Winner: RRF + `all-MiniLM-L6-v2`** — best hit rate (0.609); used as the default in production.

### LLM-as-judge evaluation results

200 questions evaluated per combination (2 models × 2 prompts = 800 total RAG calls).

| Model | Prompt | RELEVANT% | PARTLY_RELEVANT% | NON_RELEVANT% | Cost |
|---|---|---|---|---|---|
| gpt-5.6-luna | B | **77.5%** | 22.0% | 0.5% | $0.27 |
| gpt-5.4-mini | B | 75.0% | 24.5% | 0.5% | $0.17 |
| gpt-5.6-luna | A | 72.0% | 26.5% | 1.5% | $0.29 |
| gpt-5.4-mini | A | 69.0% | 31.0% | 0.0% | $0.18 |

**Prompt B consistently outperforms Prompt A** across both models. **gpt-5.6-luna + Prompt B** is the best overall at 77.5% RELEVANT. `gpt-5.4-mini + Prompt B` offers the best cost/quality trade-off at 75% RELEVANT for $0.17.

---

## Dataset

Data fetched live from the [TMDB API](https://developer.themoviedb.org/docs/getting-started).
Register for a free API key at developer.themoviedb.org.
