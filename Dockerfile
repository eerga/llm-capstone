FROM python:3.12-slim

WORKDIR /app

# Install uv from official image
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Copy dependency files and install
COPY pyproject.toml uv.lock ./
RUN uv sync --locked --no-dev --no-install-project

COPY movie_assistant/ movie_assistant/
COPY data/movies_clean.csv data/movies_clean.csv
COPY data/faiss_index_all-MiniLM-L6-v2.bin data/faiss_index_all-MiniLM-L6-v2.bin

ENV PYTHONUNBUFFERED=1

CMD ["uv", "run", "gunicorn", "movie_assistant.app:app", "--bind", "0.0.0.0:5000", "--workers", "1", "--timeout", "120"]
