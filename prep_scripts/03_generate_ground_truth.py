"""
Ground truth generation script.

For each movie in data/movies_clean.csv, generates 3 natural user questions
using gpt-5.4-mini and gpt-5.6-luna. Saves every CHUNK_SIZE movies — safe
to interrupt and resume.

Outputs:
  data/ground-truth-retrieval-gpt-5.4-mini.csv
  data/ground-truth-retrieval-gpt-5.6-luna.csv
"""

import sys
import json
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
while not (ROOT / 'pyproject.toml').exists():
    ROOT = ROOT.parent
sys.path.insert(0, str(ROOT))

import pandas as pd
from dotenv import load_dotenv
from tqdm.auto import tqdm

load_dotenv(ROOT / '.envrc')

from openai import OpenAI

CHUNK_SIZE = 100

PROMPT_TEMPLATE = """Given this movie:
Title: {title}
Genres: {genres}
Overview: {overview}

Generate exactly 3 natural user questions that someone might type into a movie recommendation
assistant that would make this movie a relevant answer.
Output as a JSON array of 3 strings and nothing else."""


def generate_openai(row, client, model):
    prompt = PROMPT_TEMPLATE.format(
        title=row['title'], genres=row['genres'], overview=str(row['overview'])[:400]
    )
    resp = client.responses.create(model=model, input=[{'role': 'user', 'content': prompt}])
    return json.loads(resp.output_text)


def generate_for_model(df, model_name, generate_fn, chunk_size=CHUNK_SIZE, delay=0.1):
    out_path = ROOT / f'data/ground-truth-retrieval-{model_name}.csv'
    if out_path.exists():
        done = set(pd.read_csv(out_path)['movie_id'].astype(str))
        print(f'Resuming — {len(done)} movie IDs already done')
    else:
        done = set()
    remaining = df[~df['id'].astype(str).isin(done)].reset_index(drop=True)
    print(f'{len(remaining)} movies left to process')
    records = []
    for i, (_, row) in enumerate(tqdm(remaining.iterrows(), total=len(remaining), desc=model_name)):
        try:
            questions = generate_fn(row)
            for q in questions:
                records.append({'movie_id': row['id'], 'question': q})
            time.sleep(delay)
        except Exception as e:
            print(f'  skipping {row["title"]}: {e}')
        if records and (len(records) >= chunk_size * 3 or i == len(remaining) - 1):
            pd.DataFrame(records).to_csv(out_path, mode='a', header=not out_path.exists(), index=False)
            records = []
            print(f'  chunk saved ({i+1}/{len(remaining)})')
    gt = pd.read_csv(out_path)
    print(f'Total: {len(gt)} pairs for {model_name}')
    return gt


def main():
    df = pd.read_csv(ROOT / 'data/movies_clean.csv')
    print(f'Loaded {len(df)} movies')
    client = OpenAI()

    generate_for_model(df, 'gpt-5.4-mini', lambda row: generate_openai(row, client, 'gpt-5.4-mini'))
    generate_for_model(df, 'gpt-5.6-luna', lambda row: generate_openai(row, client, 'gpt-5.6-luna'))

    for model in ['gpt-5.4-mini', 'gpt-5.6-luna']:
        path = ROOT / f'data/ground-truth-retrieval-{model}.csv'
        if path.exists():
            gt = pd.read_csv(path)
            print(f'{model}: {len(gt)} pairs, {gt["movie_id"].nunique()} unique movies')


if __name__ == '__main__':
    main()
