"""
Bootstrap Grafana: create API key, register PostgreSQL datasource, POST dashboard.
Run once after `docker compose up`:
    python grafana/init.py
"""

import json
import os
import time
from pathlib import Path

import requests

GRAFANA_URL = os.getenv("GRAFANA_URL", "http://localhost:3000")
GRAFANA_USER = os.getenv("GRAFANA_USER", "admin")
GRAFANA_PASSWORD = os.getenv("GRAFANA_PASSWORD", "admin")

POSTGRES_HOST = os.getenv("POSTGRES_HOST", "postgres")
POSTGRES_PORT = os.getenv("POSTGRES_PORT", "5432")
POSTGRES_DB = os.getenv("POSTGRES_DB", "movie_assistant")
POSTGRES_USER = os.getenv("POSTGRES_USER", "postgres")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "postgres")

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
        "url": f"{POSTGRES_HOST}:{POSTGRES_PORT}",
        "database": POSTGRES_DB,
        "user": POSTGRES_USER,
        "secureJsonData": {"password": POSTGRES_PASSWORD},
        "jsonData": {"sslmode": "disable", "postgresVersion": 1500},
        "access": "proxy",
        "isDefault": True,
    }
    r = session.post(f"{GRAFANA_URL}/api/datasources", json=payload)
    if r.status_code in (200, 409):
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
