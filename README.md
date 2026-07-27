# Movie Assistant

Still scrolling for over an hour on Netflix hoping to find something to watch? Your pursuit is over. Movie Assistant is a RAG-powered chatbot that knows what you're in the mood for — just describe it, and it'll find THE movie you'll actually watch and love.

Ask it things like _"mind-bending sci-fi like Inception"_, _"something funny but not stupid"_, or _"best Coen Brothers films"_ and it retrieves relevant movies from a 2000-title TMDB dataset and synthesises a grounded recommendation — no hallucinated titles, no generic lists.

> **Note:** This is a capstone project for the [LLM Zoomcamp 2026](https://github.com/DataTalksClub/llm-zoomcamp) course. It is not for profit and is open for testing.

## Live Demo

| Service | URL |
|---|---|
| Grafana Dashboard | [wisemullet536.grafana.net](https://wisemullet536.grafana.net/d/movie-assistant/movie-assistant?orgId=1&from=now-6h&to=now&timezone=browser&refresh=30s) |
| Streamlit UI | _coming soon_ |

---

## Screenshots

### Streamlit UI
Just type a cave-man version of what you want — "good movie", "sad but beautiful", "explosions" — and get 1, 2, or even 3 recommendations back.

![Streamlit UI](img/streamlit.png)

### Grafana Cloud Dashboard
Live monitoring connected to Neon Postgres — accessible from anywhere.

![Grafana Cloud](img/grafana_cloud.png)

### Grafana Dashboard (local)
Real-time monitoring of conversations, token usage, cost, relevance distribution, and user feedback.

![Grafana Dashboard](img/Grafana_dashboard.png)

### Kestra Ingestion Pipeline
Automated weekly pipeline that fetches and cleans movie data from the TMDB API.

![Kestra Ingestion](img/kestra_log.png)

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
| Storage | PostgreSQL 16 (local via Docker) or [Neon](https://neon.tech) (free cloud Postgres) |
| Monitoring | Grafana |
| Ingestion pipeline | Kestra (automated, scheduled weekly) |

---

## Ingestion pipeline (Kestra)

Movie data is fetched and cleaned automatically via a [Kestra](https://kestra.io) workflow (`kestra/flows/movie_ingestion.yaml`). The flow:

1. Fetches ~2000 movies from the TMDB API
2. Enriches each with genres, keywords, runtime, tagline
3. Cleans and normalizes fields → writes `data/movies_clean_kestra.csv`

The flow runs on a weekly schedule (Sunday 3am) and can be triggered manually.

**To start Kestra:**
```bash
make kestra-up
```
Open [http://localhost:8080](http://localhost:8080) — login: `admin@kestra.io` / `Admin1234!`

**To trigger the ingestion flow manually:**
```bash
make kestra-ingest
```
Or click **Execute** on the `movie_data_ingestion` flow in the Kestra UI.

---

## Quickstart (fresh clone)

### 1. Prerequisites

- Python 3.12+
- [uv](https://docs.astral.sh/uv/getting-started/installation/)
- Docker + Docker Compose

### 2. Clone and install

```bash
git clone https://github.com/eerga/llm-capstone.git
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
DATABASE_URL=postgresql://user:password@host/dbname?sslmode=require
```

**PostgreSQL options:**
- **Local** (default): leave `DATABASE_URL` unset — uses the Docker Compose Postgres on `localhost:5432`
- **Neon** (free cloud Postgres): sign up at [neon.tech](https://neon.tech), create a project, copy the connection string into `DATABASE_URL`

Then load it:

```bash
source .envrc
```

### 4. Fetch and prepare movie data

**Option A — manual:**
```bash
# Fetch ~2000 movies from TMDB API → data/movies_raw.json
python data/fetch_movies.py
```
Then run `notebooks/01-data-prep.ipynb` to clean the data and write `data/movies_clean.csv`.

**Option B — automated (Kestra):**
```bash
make kestra-up
make kestra-ingest   # wait ~7 min for completion
make kestra-copy     # downloads movies_clean_kestra.csv to data/
```

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
| `make kestra-up` | Start only Kestra + its Postgres (no app rebuild) |
| `make kestra-ingest` | Trigger the movie ingestion flow via API |
| `make kestra-copy` | Download Kestra-generated CSV to `data/` |
| `make restart` | `down` + `up` + `grafana` |

### Neon Screenshots

#### Tables view — conversations and feedback rows visible after first use

![Conversations Table](img/conversations_table.png)
![Feedback Table](img/feedback_table.png)

#### SQL Editor — run queries directly against your Neon database

![Conversations SQL Editor](img/conversations_sql_editor.png)
![Feedback SQL Editor](img/feedback_sql_editor.png)

Example queries:
```sql
-- View recent conversations
SELECT timestamp, question, relevance, openai_cost FROM conversations ORDER BY timestamp DESC LIMIT 10;

-- View feedback
SELECT c.question, f.feedback, f.timestamp
FROM feedback f JOIN conversations c ON f.conversation_id = c.id
ORDER BY f.timestamp DESC LIMIT 10;
```

---

## Grafana dashboard

Two options:

### Option A — Local (Docker)

```bash
make up && make grafana
```

Open [http://localhost:3000](http://localhost:3000) — login: `admin` / `admin`.

### Option B — Grafana Cloud (free tier)

1. Sign up at [grafana.com](https://grafana.com) → free tier
2. Go to **Connections → Data Sources → Add → PostgreSQL** and fill in your Neon connection:
   - Host: `<your-neon-host>:5432`
   - Database: `neondb`
   - User: `neondb_owner`
   - Password: your Neon password
   - SSL Mode: `require`
   - Name: `MovieAssistantDB` (must match exactly)
3. Click **Save & Test** — should show green
4. Go to **Dashboards → Import → Upload JSON** → select `grafana/dashboard.json`

Panels: last 5 conversations, response time, token usage, cost over time, model usage, relevance distribution, user feedback.

**Manual datasource setup for local Grafana** (if `make grafana` doesn't auto-configure):

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

The evaluation pipeline follows this flow:
```
03 (generate questions) → 02 (measure retrieval + tune boosts) → 04 (LLM-as-judge)
```

1. **Notebook 03** uses an LLM to generate 3 realistic user questions per movie → ground truth CSV
2. **Notebook 02** uses that ground truth to measure Hit Rate + MRR across search methods and tune boost weights
3. **Notebook 04** runs the full RAG pipeline on a sample and scores answer quality with an LLM judge

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

### Boost tuning results

Minsearch boost weights were tuned by iterating 64 combinations of title/keywords/overview boosts on 500 ground truth questions. Best combination vs default:

| | title | keywords | overview | Hit Rate | MRR |
|---|---|---|---|---|---|
| Default | 3.0 | 2.0 | 1.5 | 0.334 | 0.163 |
| **Tuned** | **1.0** | **2.0** | **2.0** | **0.620** | **0.409** |

Overview and keywords matter more than title for movie retrieval — the tuned weights are used in production.

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
