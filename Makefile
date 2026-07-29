.PHONY: up down build streamlit streamlit-cloud grafana test kestra-up kestra-ingest kestra-copy restart help

help:
	@echo ""
	@echo "Movie Assistant — available targets:"
	@echo ""
	@echo "  make up             Build and start all Docker services (detached)"
	@echo "  make down           Stop all services"
	@echo "  make build          Rebuild Docker images without starting"
	@echo "  make restart        down + up + grafana"
	@echo ""
	@echo "  make streamlit      Run Streamlit UI locally (http://localhost:8501)"
	@echo "  make streamlit-cloud Run Streamlit UI with Neon Postgres (http://localhost:8501)"
	@echo "  make grafana        Bootstrap Grafana datasource + dashboard (http://localhost:3000)"
	@echo "  make test           Send a test question to the Flask API"
	@echo ""
	@echo "  make kestra-up      Start Kestra + its Postgres (http://localhost:8080)"
	@echo "  make kestra-ingest  Trigger the movie data ingestion flow via API"
	@echo "  make kestra-copy    Copy ingested movies_clean_kestra.csv to data/"
	@echo ""

up:
	docker compose --env-file .envrc up --build -d

down:
	docker compose down

build:
	docker compose build

streamlit:
	@echo "Starting Streamlit UI at http://localhost:8501 — press Ctrl+C to stop"
	uv run streamlit run streamlit_app.py

streamlit-cloud:
	@echo "Starting Streamlit UI with Neon Postgres at http://localhost:8501 — press Ctrl+C to stop"
	export $$(grep -v '^#' .envrc | sed 's/#.*//' | grep '=' | xargs) && \
	uv run streamlit run streamlit_app.py

grafana:
	uv run python grafana/init.py
	@echo ""
	@echo "Grafana dashboard: http://localhost:3000 (login: admin / admin)"
	@echo ""

test:
	curl -s -X POST http://localhost:5000/question \
	  -H 'Content-Type: application/json' \
	  -d '{"question": "mind-bending sci-fi like Inception"}' | python3 -m json.tool

kestra-up:
	export $$(grep -v '^#' .envrc | sed 's/#.*//' | grep '=' | xargs) && \
	SECRET_TMDB_API_KEY=$$(printf '%s' "$$TMDB_API_KEY" | base64) \
	docker compose up -d kestra_postgres kestra
	@echo "Waiting for Kestra to start..."
	@sleep 15
	@curl -s -X POST http://localhost:8080/api/v1/flows/import \
	  -u admin@kestra.io:Admin1234! \
	  -F fileUpload=@kestra/flows/movie_ingestion.yaml \
	  && echo "Flow imported successfully!" || echo "Flow import failed — try manually in the UI"
	@echo ""
	@echo "Open http://localhost:8080 (login: admin@kestra.io / Admin1234!)"
	@echo ""

kestra-copy:
	uv run python kestra/download_output.py

kestra-ingest:
	curl -s -X POST "http://localhost:8080/api/v1/executions/movie_assistant/movie_data_ingestion" \
	  -u admin@kestra.io:Admin1234! \
	  -H 'Content-Type: multipart/form-data' | python3 -m json.tool

restart: down up grafana
