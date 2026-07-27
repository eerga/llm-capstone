"""Download the latest successful Kestra ingestion output to data/movies_clean_kestra.csv."""

import sys
import requests

BASE = "http://localhost:8080"
AUTH = ("admin@kestra.io", "Admin1234!")
OUT  = "data/movies_clean_kestra.csv"

# Find latest successful execution
resp = requests.get(
    f"{BASE}/api/v1/executions/search",
    auth=AUTH,
    params={"namespace": "movie_assistant", "flowId": "movie_data_ingestion", "state": "SUCCESS"},
)
resp.raise_for_status()
results = resp.json().get("results", [])
if not results:
    print("No successful executions found. Run 'make kestra-ingest' first.")
    sys.exit(1)

exec_id = results[0]["id"]
print(f"Latest successful execution: {exec_id}")

# Get output file URI from clean_movies task
exec_data = requests.get(f"{BASE}/api/v1/executions/{exec_id}", auth=AUTH).json()
file_uri = None
for task in exec_data.get("taskRunList", []):
    if task.get("taskId") == "clean_movies":
        file_uri = task.get("outputs", {}).get("outputFiles", {}).get("movies_clean_kestra.csv")
        break

if not file_uri:
    print("Could not find movies_clean_kestra.csv in task outputs.")
    sys.exit(1)

# Download file
dl = requests.get(
    f"{BASE}/api/v1/executions/{exec_id}/file",
    auth=AUTH,
    params={"path": file_uri},
)
dl.raise_for_status()

with open(OUT, "wb") as f:
    f.write(dl.content)

lines = dl.content.count(b"\n")
print(f"Saved {lines} rows to {OUT}")
