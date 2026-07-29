"""
Retrieval evaluation and boost-tuning script.

Evaluates minsearch, FAISS, and RRF across 2 ground truth datasets and
2 embedding models. Then runs boost weight grid search on minsearch.
Saves results to data/retrieval-eval-results.csv and data/boost-tuning-results.csv.
"""

import sys
import os
import importlib
import itertools
from pathlib import Path

ROOT = Path(__file__).resolve().parent
while not (ROOT / 'pyproject.toml').exists():
    ROOT = ROOT.parent
sys.path.insert(0, str(ROOT))

import pandas as pd
from dotenv import load_dotenv
from tqdm.auto import tqdm

load_dotenv(ROOT / '.envrc')


def hit_rate_mrr(search_fn, ground_truth, num_results=10):
    hits = 0
    mrr_sum = 0.0
    for _, row in tqdm(ground_truth.iterrows(), total=len(ground_truth), leave=False):
        results = search_fn(row['question'], num_results=num_results)
        result_ids = [str(r['id']) for r in results]
        expected = str(row['movie_id'])
        if expected in result_ids:
            hits += 1
            rank = result_ids.index(expected) + 1
            mrr_sum += 1 / rank
    n = len(ground_truth)
    return round(hits / n, 4), round(mrr_sum / n, 4)


def main():
    GT_MODELS = ['gpt-5.4-mini', 'gpt-5.6-luna']
    EMBEDDING_MODELS = [
        'sentence-transformers/all-MiniLM-L6-v2',
        'sentence-transformers/multi-qa-MiniLM-L6-cos-v1',
    ]

    all_rows = []
    for gt_model in GT_MODELS:
        gt = pd.read_csv(ROOT / f'data/ground-truth-retrieval-{gt_model}.csv')
        print(f'\n=== Ground truth: {gt_model} ({len(gt)} pairs) ===')
        for emb_model in EMBEDDING_MODELS:
            print(f'  Loading indexes with {emb_model} ...')
            os.environ['EMBEDDING_MODEL'] = emb_model
            import movie_assistant.ingest as ingest
            importlib.reload(ingest)
            emb_short = emb_model.split('/')[-1]
            for method, fn in [('minsearch', ingest.search_minsearch), ('faiss', ingest.search_faiss), ('rrf', ingest.search_rrf)]:
                print(f'  {method} ...')
                hr, mrr = hit_rate_mrr(fn, gt)
                all_rows.append({'gt_model': gt_model, 'embedding': emb_short, 'method': method, 'hit_rate': hr, 'mrr': mrr})
                print(f'    hit_rate={hr}, mrr={mrr}')

    results_df = pd.DataFrame(all_rows)
    results_df.to_csv(ROOT / 'data/retrieval-eval-results.csv', index=False)
    print(results_df.sort_values('mrr', ascending=False).to_string())

    # Boost tuning
    os.environ['EMBEDDING_MODEL'] = 'sentence-transformers/all-MiniLM-L6-v2'
    import movie_assistant.ingest as ingest
    importlib.reload(ingest)
    gt_sample = pd.read_csv(ROOT / 'data/ground-truth-retrieval-gpt-5.6-luna.csv').sample(500, random_state=42).reset_index(drop=True)

    tune_rows = []
    total = 4 * 4 * 4
    for i, (tb, kb, ob) in enumerate(itertools.product([1.0,2.0,3.0,5.0], [0.5,1.0,2.0,3.0], [0.5,1.0,1.5,2.0])):
        boost = {'title': tb, 'keywords': kb, 'overview': ob, 'tagline': 0.5, 'genres': 0.5}
        print(f'[{i+1}/{total}] title={tb}, keywords={kb}, overview={ob}', end=' ... ')
        hr, mrr = hit_rate_mrr(lambda q, b=boost, **_: ingest.search_minsearch(q, boost=b, num_results=10), gt_sample)
        print(f'hit_rate={hr}, mrr={mrr}')
        tune_rows.append({'title': tb, 'keywords': kb, 'overview': ob, 'hit_rate': hr, 'mrr': mrr})

    tune_df = pd.DataFrame(tune_rows)
    tune_df.to_csv(ROOT / 'data/boost-tuning-results.csv', index=False)
    print(tune_df.sort_values('mrr', ascending=False).head(10).to_string())


if __name__ == '__main__':
    main()
