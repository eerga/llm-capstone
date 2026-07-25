.PHONY: up down build streamlit grafana test

up:
	docker compose up --build -d

down:
	docker compose down

build:
	docker compose build

streamlit:
	uv run streamlit run streamlit_app.py

grafana:
	uv run python grafana/init.py

test:
	curl -s -X POST http://localhost:5000/question \
	  -H 'Content-Type: application/json' \
	  -d '{"question": "mind-bending sci-fi like Inception"}' | python3 -m json.tool

restart: down up grafana
