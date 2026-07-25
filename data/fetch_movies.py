"""
Fetches movie data from the TMDB API and writes data/movies_raw.json.

Usage:
    python data/fetch_movies.py

Reads TMDB_API_KEY from .envrc (or .env) in the project root.
Fetches up to MAX_PAGES pages of popular movies (~20 per page), then enriches
each with runtime and tagline via a follow-up /movie/{id} call.
"""

import json
import os
import time
from pathlib import Path

import requests
from dotenv import load_dotenv
from tqdm import tqdm

# Load .envrc or .env from project root
_ROOT = Path(__file__).parent.parent
load_dotenv(_ROOT / ".envrc")
load_dotenv(_ROOT / ".env")

BASE_URL = "https://api.themoviedb.org/3"
MAX_PAGES = 100  # 100 pages × 20 movies = 2000 movies
OUTPUT = Path(__file__).parent / "movies_raw.json"


def get(endpoint: str, params: dict) -> dict:
    params["api_key"] = os.environ["TMDB_API_KEY"]
    resp = requests.get(f"{BASE_URL}{endpoint}", params=params, timeout=10)
    resp.raise_for_status()
    return resp.json()


def fetch_discover(page: int) -> list[dict]:
    data = get("/discover/movie", {
        "sort_by": "vote_count.desc",
        "vote_count.gte": 100,
        "page": page,
    })
    return data.get("results", [])


def fetch_details(movie_id: int) -> dict:
    return get(f"/movie/{movie_id}", {"append_to_response": "keywords"})


def main():
    if "TMDB_API_KEY" not in os.environ:
        raise EnvironmentError("TMDB_API_KEY not set")

    movies = []
    print(f"Fetching {MAX_PAGES} pages from /discover/movie ...")
    for page in tqdm(range(1, MAX_PAGES + 1)):
        results = fetch_discover(page)
        movies.extend(results)
        time.sleep(0.05)  # stay well under 50 req/s

    print(f"Fetched {len(movies)} movies. Enriching with details ...")
    enriched = []
    seen = set()
    for m in tqdm(movies):
        if m["id"] in seen:
            continue
        seen.add(m["id"])
        try:
            details = fetch_details(m["id"])
            enriched.append({
                "id": m["id"],
                "title": details.get("title", ""),
                "overview": details.get("overview", ""),
                "tagline": details.get("tagline", ""),
                "genres": [g["name"] for g in details.get("genres", [])],
                "keywords": [k["name"] for k in details.get("keywords", {}).get("keywords", [])],
                "vote_average": details.get("vote_average", 0),
                "vote_count": details.get("vote_count", 0),
                "release_date": details.get("release_date", ""),
                "runtime": details.get("runtime", 0),
            })
            time.sleep(0.05)
        except Exception as e:
            print(f"  skipping {m['id']}: {e}")

    OUTPUT.write_text(json.dumps(enriched, indent=2, ensure_ascii=False))
    print(f"Wrote {len(enriched)} movies to {OUTPUT}")


if __name__ == "__main__":
    main()
