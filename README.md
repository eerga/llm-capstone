# 🎬 Movie Assistant

Still scrolling for over an hour on Netflix hoping to find something to watch? Your pursuit is over. Movie Assistant is a RAG-powered chatbot that knows what you're in the mood for — just describe it, and it'll find THE movie you'll actually watch and love.

Ask it things like _"mind-bending sci-fi like Inception"_, _"something funny but not stupid"_, or _"best Coen Brothers films"_ and it retrieves relevant movies from a 2000-title TMDB dataset and synthesises a grounded recommendation — no hallucinated titles, no generic lists.

> [!NOTE]
> This is a capstone project for the [LLM Zoomcamp 2026](https://github.com/DataTalksClub/llm-zoomcamp) course. It is not for profit and is open for testing. Try it out at [movie-recommend67.streamlit.app](https://movie-recommend67.streamlit.app)!

---

## Contents

**Data** · [The Data](#the-data) · [Ingestion Pipeline (Kestra)](#ingestion-pipeline-kestra)

**App** · [Architecture](#architecture) · [Local Setup (Path A)](#local-setup-path-a) · [🌐 Cloud Setup (Path B)](#-cloud-setup-path-b) · [Live Demo Links](#live-demo-links)

**Evaluation** · [Retrieval & Boost Tuning](#evaluation) · [Best Configuration (Full Chain)](#best-configuration-full-chain)

**Other** · [Demo Videos](#demo-videos) · [Makefile Targets](#makefile-targets) · [Cleanup](#cleanup) · [Future Work](#future-work)

---

## Demo Videos

| README Section | Video |
|---|---|
| [Local Setup (Path A)](#local-setup-path-a) | [📹 Local Testing Walkthrough](https://youtu.be/85XZs0N1xFc) |
| [Live Demo Links](#live-demo-links) | [📹 Cloud Testing Walkthrough](https://youtu.be/Np43HWALhf8) |
| [Ingestion Pipeline (Kestra)](#ingestion-pipeline-kestra) | [📹 Kestra Ingestion Pipeline](https://youtu.be/_YJ5kznu8gU) |
| [Local Setup → Step 3 (Fetch & Prepare Data)](#steps) | [📹 Fetch & Prepare Data](https://youtu.be/5dS3Tm3RWxo) |
| [Evaluation → Ground Truth](#how-ground-truth-was-generated) | [📹 Ground Truth Generation](https://youtu.be/GAjhQz4tDIQ) _(some brief black screen moments — no crucial info missed)_ |
| [Evaluation → Retrieval](#retrieval-evaluation) | [📹 Retrieval Evaluation](https://youtu.be/DtdneJh5ZfE) |
| [Evaluation → LLM-as-judge](#llm-as-judge-evaluation) | [📹 LLM-as-Judge Evaluation](https://youtu.be/YjVNnMFsH18) |

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

> [!NOTE]
> **💡 Future improvements:** Adding `cast` (lead actors) and `original_language` fields could further improve recommendation quality — cast helps match actor-specific queries ("movies with Tom Hanks"), and language enables filtering for non-English cinema.

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
| Storage | PostgreSQL 16 (local) or [Neon](https://neon.tech) (cloud) | Free serverless Postgres |
| Monitoring | Grafana (local Docker or [Grafana Cloud](https://grafana.com) free tier) | 7-panel dashboard |
| Ingestion | **Option A — Python script:** `data/fetch_movies.py` → `prep_scripts/01_data_prep.py` → `data/movies_clean.csv` ([📹 video](https://youtu.be/5dS3Tm3RWxo)) | Manual, run once |
| Ingestion | **Option B — Kestra:** automated weekly flow → `data/movies_clean_kestra.csv` ([📹 video](https://youtu.be/_YJ5kznu8gU), see [Ingestion Pipeline](#ingestion-pipeline-kestra)) | Scheduled, no manual steps |

---

## Makefile Targets

Instead of remembering long Docker and Python commands, this project uses a `Makefile` to wrap everything into simple `make` commands. Run `make help` to see all targets, or expand below for the full list.

<details>
<summary>Click to expand Makefile targets</summary>

| Target | What it does |
|---|---|
| `make up` | Build and start all Docker services (detached) |
| `make down` | Stop all services |
| `make streamlit` | Run Streamlit UI locally (http://localhost:8501) |
| `make streamlit-cloud` | Run Streamlit UI with Neon Postgres |
| `make grafana` | Bootstrap Grafana datasource + dashboard |
| `make kestra-up` | Start Kestra + its Postgres (http://localhost:8080) |
| `make kestra-ingest` | Trigger the movie ingestion flow |
| `make kestra-copy` | Download Kestra-generated CSV to `data/` |
| `make restart` | `down` + `up` + `grafana` |

</details>

## Ingestion Pipeline (Kestra)

> [!NOTE]
> 📹 Watch the [Kestra Ingestion Walkthrough](https://youtu.be/_YJ5kznu8gU) to see the pipeline in action.

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

> [!NOTE]
> **📁 CSV naming:** This project uses `movies_clean.csv` (generated via the Python script path). The Kestra pipeline outputs `movies_clean_kestra.csv` — all `make` targets and commands are valid, but if you want the app to use the Kestra-generated data, rename the output to `movies_clean.csv` or update the filename in `kestra/flows/movie_ingestion.yaml`.

---

## Evaluation

### How ground truth was generated

For each of 2000 movies, an LLM generated 3 natural user questions that would make that movie a relevant answer. This produced **6000 ground-truth pairs** per model, used to benchmark retrieval quality.

```
notebooks/03-evaluation-data-generation.ipynb  ┐
                                                ├→ ground-truth-retrieval-{model}.csv
prep_scripts/03_generate_ground_truth.py       ┘
```

### Retrieval evaluation

Hit Rate and MRR measured across 4 methods × 2 embedding models × 2 ground truth sources:

| GT model | Embedding | Method | Hit Rate | MRR |
|---|---|---|---|---|
| gpt-5.6-luna | all-MiniLM-L6-v2 | **rrf** | **0.609** | **0.381** |

<details>
<summary>Click to see all 12 combinations</summary>

| GT model | Embedding | Method | Hit Rate | MRR |
|---|---|---|---|---|
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

</details>

**Winner: RRF + `all-MiniLM-L6-v2`** — best hit rate (0.609); used as the production default.

### Boost tuning

Minsearch boost weights were tuned over 64 combinations on 500 ground truth questions:

| | title | keywords | overview | Hit Rate | MRR |
|---|---|---|---|---|---|
| Default | 3.0 | 2.0 | 1.5 | 0.334 | 0.163 |
| **Tuned** | **1.0** | **2.0** | **2.0** | **0.620** | **0.409** |

Overview and keywords matter more than title for movie retrieval.

> [!NOTE]
> **Boost tuning applies to the minsearch component only.** The 0.620 hit rate above is for tuned minsearch on a 500-question sample. The **0.609 hit rate in the table above** is for the full RRF method on all 6000 questions — RRF uses the tuned minsearch internally alongside FAISS, which is why it outperforms both alone.

### LLM-as-judge evaluation

200 questions evaluated per combination (2 models × 2 prompts = 800 RAG calls):

| Model | Prompt | RELEVANT% | PARTLY_RELEVANT% | NON_RELEVANT% | Cost |
|---|---|---|---|---|---|
| gpt-5.6-luna | A | **82.0%** | 18.0% | 0.0% | $0.28 |
| gpt-5.6-luna | B | 81.5% | 18.0% | 0.5% | $0.27 |
| gpt-5.4-mini | A | 79.0% | 20.0% | 1.0% | $0.18 |
| gpt-5.4-mini | B | 76.5% | 22.5% | 1.0% | $0.17 |

**`gpt-5.6-luna + Prompt B`** was chosen for this project — friendlier tone and consistently returns 2-3 movie recommendations instead of just 1. While Prompt A scored marginally higher (82% vs 81.5% RELEVANT) in the latest run, the gap is within noise (~0.5%) and the user experience with Prompt B is noticeably better. `gpt-5.4-mini + Prompt A` offers the best cost/quality trade-off at 79% RELEVANT for $0.18.

> [!NOTE]
> Results can vary slightly between evaluation runs depending on the LLM judge's responses. In a previous run, Prompt B outperformed Prompt A — the scores are close enough that either is a valid choice.

---

### Best configuration (full chain)

| Component | Winner | Why |
|---|---|---|
| Ground truth model | `gpt-5.6-luna` | Generated higher quality, more natural questions |
| Embedding model | `all-MiniLM-L6-v2` | Better semantic matching than multi-qa variant |
| Search method | RRF | Hybrid beats either minsearch or FAISS alone |
| Boost weights | title=1.0, keywords=2.0, overview=2.0 | Overview and keywords matter more than title for movie retrieval |

Combined result: **hit_rate=0.620, MRR=0.409** (on 500-question tuning sample). All four settings are baked into the production app.

---

## Local Setup (Path A)

> [!NOTE]
> 📹 Don't want to run the code? Watch the [Local Testing Walkthrough](https://youtu.be/85XZs0N1xFc) instead.

> [!WARNING]
> ⚠️ Older OS / Intel Mac issues? I tried my best to support older platforms, but if your local setup fails, the easiest fallback is [GitHub Codespaces](https://github.com/features/codespaces) — open the repo, click **Code → Codespaces → New codespace**, and run the same steps there (Linux, no platform issues).

Everything runs on your machine via Docker Compose.

### Prerequisites

- Python 3.12+
- [uv](https://docs.astral.sh/uv/getting-started/installation/)
- Docker + Docker Compose

> [!TIP]
> **Prerequisites**: Make sure Docker is installed and running on your machine before starting!

✅ **Verify Docker installation**
```bash
docker run hello-world
```

### Steps

**1. Clone and install**
```bash
git clone https://github.com/eerga/llm-capstone.git
uv lock && uv sync
```
> [!CAUTION]
> If the movie-assistant environment did not activate automatically, run: `source .venv/bin/activate`

**2. Configure environment**
```bash
cp .envrc_template .envrc
# Fill in OPENAI_API_KEY and TMDB_API_KEY
source .envrc
```

**3. Optional — Fetch and prepare data** _(`movies_clean.csv` is already in the repo)_

> [!TIP]
> 💡 Skip this step if you just want to run the app.

| Script | What it does | Video |
|---|---|---|
| `python data/fetch_movies.py` | Fetch ~2000 movies from TMDB API | [📹](https://youtu.be/5dS3Tm3RWxo) |
| `python prep_scripts/01_data_prep.py` | Clean raw data → `movies_clean.csv` | ↑ same video |

**4. Optional — Reproduce evaluation results** _(result CSVs and FAISS index files are already in the repo)_

> [!TIP]
> 📹 Videos are linked in each row below.

| Script | What it does | Video |
|---|---|---|
| `python prep_scripts/03_generate_ground_truth.py` | Generate 6000 Q&A pairs per model (~$2, ~30 min) | [📹](https://youtu.be/GAjhQz4tDIQ) |
| `python prep_scripts/02_rag_test.py` | Retrieval eval + boost tuning (needs step above) | [📹](https://youtu.be/DtdneJh5ZfE) |
| `python prep_scripts/04_rag_eval.py` | LLM-as-judge eval (~$1, ~10 min, needs step above) | [📹](https://youtu.be/YjVNnMFsH18) |

**5. Start all services**
```bash
make up
```

**6. Bootstrap Grafana** _(first time only)_
```bash
make grafana
# Open http://localhost:3000 — login: admin / admin
```
> [!CAUTION]
> After `make grafana`, the dashboard may show "No data" on first load. This is a Grafana quirk — go to **Connections → Data Sources → MovieAssistantDB → Save & Test**, then reload the dashboard tab. This is a one-time step per fresh Grafana volume.

![Grafana Dashboard (local)](img/Grafana_dashboard.png)

**7. Run the UI**
```bash
make streamlit
# Open http://localhost:8501
```

![Streamlit UI](img/streamlit.png)

---

## 🌐 Cloud Setup (Path B)

> [!NOTE]
> 📹 See it in action? Watch the [Cloud Testing Walkthrough](https://youtu.be/Np43HWALhf8) — shows the live demo rather than deployment steps.

Run the UI on Streamlit Community Cloud, store data in Neon Postgres, and monitor via Grafana Cloud — all free tiers.

> [!WARNING]
> ⚠️ The live demo links below are running on free trial tiers (set up 2026-07-27) and are intended for demonstration purposes only. They may stop working after approximately 14 days or when free tier limits are reached. This is a capstone project and is not maintained as a production service.

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

> [!CAUTION]
> The Neon database password is intentionally exposed in `.envrc_template` to allow evaluators to connect quickly and see a complete history of requests. I will rotate this secret after evaluation is complete.

1. Sign up at [grafana.com](https://grafana.com) → free tier
2. **Connections → Data Sources → Add → PostgreSQL**:
   - Host: `<your-neon-host>:5432`
   - Database: `neondb` / User: `neondb_owner`
   - Password: your Neon password / SSL Mode: `require`
   - Name: `MovieAssistantDB` (must match exactly)
3. **Save & Test** → green ✓
4. **Dashboards → Import → Upload JSON** → select `grafana/dashboard.json`

The dashboard has **7 panels**:

| Panel | What it shows |
|---|---|
| Last 5 Conversations | Recent questions, answers, model, relevance, cost |
| Response Time | Latency per request over time |
| Token Usage | Avg tokens per request over time |
| Cost Over Time | API spend over time |
| Model Usage | Breakdown of requests by model |
| Relevance Distribution | RELEVANT / PARTLY_RELEVANT / NON_RELEVANT pie chart |
| User Feedback | 👍 Positive vs 👎 Negative feedback pie chart |

User feedback (👍/👎) submitted via the Streamlit UI is stored in the `feedback` table and displayed in the **User Feedback** panel.

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

The app is already deployed at [movie-recommend67.streamlit.app](https://movie-recommend67.streamlit.app) — no need to redeploy unless you want your own instance.

---

## Live Demo Links [📹 Demo](https://youtu.be/Np43HWALhf8)

| Service | URL | Notes |
|---|---|---|
| Streamlit UI | [movie-recommend67.streamlit.app](https://movie-recommend67.streamlit.app) | Stays live as long as OpenAI tokens are available · works on mobile too |
| Grafana Dashboard | [wisemullet536.grafana.net](https://wisemullet536.grafana.net/d/movie-assistant/movie-assistant?orgId=1&from=now-6h&to=now&timezone=browser&refresh=30s) | Grafana Cloud free tier — expires ~14 days after 2026-07-27 · same dashboard available locally via `make grafana` |
| Database | [Neon Postgres](https://neon.tech) — `ep-steep-king-awasy5fu.c-12.us-east-1.aws.neon.tech` | Email [erikaergart@gmail.com](mailto:erikaergart@gmail.com) to request view access |

---

## Cleanup

Stops all Docker services (app, Postgres, Grafana, Kestra). Data in named volumes is preserved.
```bash
make down
```

To also wipe the local database and Grafana data:
```bash
docker volume rm llm-capstone_postgres_data llm-capstone_grafana_data
```

---

## Future Work

| Idea | What it takes |
|---|---|
| **Add cast & language fields** | Fetch `cast` and `original_language` from TMDB API, add to `movies_clean.csv` and minsearch/FAISS index |
| **Multilingual assistant** | Swap embedding model to `paraphrase-multilingual-MiniLM-L12-v2`, add language instruction to LLM prompt, regenerate ground truth in multiple languages |
| **Query rewriting** | Add a pre-RAG step that rewrites vague queries into more retrieval-friendly ones using an LLM |
| **Document re-ranking** | After retrieval, use a cross-encoder model to re-rank results before sending to the LLM |
| **Persistent public deployment** | Deploy Flask + Postgres to a permanent cloud service (Fly.io, Google Cloud Run) for a always-on demo |

---
