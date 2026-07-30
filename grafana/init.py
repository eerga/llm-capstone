"""
Bootstrap Grafana: create API key, register PostgreSQL datasource, POST dashboard.
Run once after `docker compose up`:
    python grafana/init.py

If DATABASE_URL is set, registers Neon as the datasource (SSL required).
Otherwise falls back to local Docker Postgres.
"""

import json
import os
import time
from pathlib import Path
from urllib.parse import urlparse

import requests
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".envrc")

GRAFANA_URL = os.getenv("GRAFANA_URL", "http://localhost:3000")
GRAFANA_USER = os.getenv("GRAFANA_USER", "admin")
GRAFANA_PASSWORD = os.getenv("GRAFANA_PASSWORD", "admin")

_DATABASE_URL = os.getenv("DATABASE_URL")

if _DATABASE_URL:
    _p = urlparse(_DATABASE_URL)
    POSTGRES_HOST = f"{_p.hostname}:{_p.port or 5432}"
    POSTGRES_DB = _p.path.lstrip("/")
    POSTGRES_USER = _p.username
    POSTGRES_PASSWORD = _p.password
    POSTGRES_SSL = "require"
    print(f"Using Neon Postgres: {_p.hostname}")
else:
    POSTGRES_HOST = f"{os.getenv('POSTGRES_HOST', 'postgres')}:{os.getenv('POSTGRES_PORT', '5432')}"
    POSTGRES_DB = os.getenv("POSTGRES_DB", "movie_assistant")
    POSTGRES_USER = os.getenv("POSTGRES_USER", "postgres")
    POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "postgres")
    POSTGRES_SSL = "disable"
    print("Using local Docker Postgres")

session = requests.Session()
session.auth = (GRAFANA_USER, GRAFANA_PASSWORD)
session.headers.update({"Content-Type": "application/json"})


def wait_for_grafana(retries=10):
    for i in range(retries):
        try:
            r = session.get(f"{GRAFANA_URL}/api/health")
            if r.status_code == 200:
                print("Grafana is up.")
                return
        except Exception:
            pass
        print(f"  waiting for Grafana ({i+1}/{retries}) ...")
        time.sleep(3)
    raise RuntimeError("Grafana did not become healthy in time")


def create_datasource():
    payload = {
        "name": "MovieAssistantDB",
        "type": "postgres",
        "url": POSTGRES_HOST,
        "database": POSTGRES_DB,
        "user": POSTGRES_USER,
        "secureJsonData": {"password": POSTGRES_PASSWORD},
        "jsonData": {"sslmode": POSTGRES_SSL, "postgresVersion": 1500},
        "access": "proxy",
        "isDefault": True,
    }
    # Delete existing datasource first to force password update
    existing = session.get(f"{GRAFANA_URL}/api/datasources/name/MovieAssistantDB")
    if existing.status_code == 200:
        ds_id = existing.json().get("id")
        session.delete(f"{GRAFANA_URL}/api/datasources/{ds_id}")
        print("Deleted existing datasource.")
    r = session.post(f"{GRAFANA_URL}/api/datasources", json=payload)
    if r.status_code == 200:
        print("Datasource registered.")
    else:
        print(f"Datasource error: {r.status_code} {r.text}")


def post_dashboard():
    dashboard_path = Path(__file__).parent / "dashboard.json"
    dashboard = json.loads(dashboard_path.read_text())
    payload = {"dashboard": dashboard, "overwrite": True, "folderId": 0}
    r = session.post(f"{GRAFANA_URL}/api/dashboards/db", json=payload)
    if r.status_code == 200:
        slug = r.json().get("slug", "")
        print(f"Dashboard posted: {GRAFANA_URL}/d/{slug}")
    else:
        print(f"Dashboard error: {r.status_code} {r.text}")


if __name__ == "__main__":
    wait_for_grafana()
    create_datasource()
    post_dashboard()
