"""
Data preparation script — loads raw TMDB API data, cleans and flattens
fields, and writes data/movies_clean.csv.
"""

import json
from pathlib import Path

import pandas as pd


def main():
    ROOT = Path(__file__).resolve().parent
    while not (ROOT / 'pyproject.toml').exists():
        ROOT = ROOT.parent

    RAW = ROOT / 'data/movies_raw.json'
    OUT = ROOT / 'data/movies_clean.csv'

    with open(RAW) as f:
        raw = json.load(f)

    print(f'Loaded {len(raw)} movies')
    df = pd.DataFrame(raw)

    df['genres'] = df['genres'].apply(lambda x: ', '.join(x) if isinstance(x, list) else '')
    df['keywords'] = df['keywords'].apply(lambda x: ', '.join(x) if isinstance(x, list) else '')
    df['release_year'] = pd.to_datetime(df['release_date'], errors='coerce').dt.year.fillna(0).astype(int)

    def vote_bucket(v):
        if v >= 7.5: return 'high'
        if v >= 6.0: return 'medium'
        return 'low'

    df['vote_bucket'] = df['vote_average'].apply(vote_bucket)
    df = df[df['overview'].str.strip().str.len() > 20]

    cols = ['id', 'title', 'overview', 'tagline', 'genres', 'keywords',
            'vote_average', 'vote_count', 'release_year', 'runtime', 'vote_bucket']
    df = df[cols].reset_index(drop=True)

    print(f'Shape: {df.shape}')
    print('Vote bucket distribution:')
    print(df['vote_bucket'].value_counts().to_string())

    df.to_csv(OUT, index=False)
    print(f'Saved {len(df)} rows to {OUT}')


if __name__ == '__main__':
    main()
