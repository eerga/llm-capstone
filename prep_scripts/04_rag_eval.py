"""
LLM-as-judge RAG evaluation script.

Runs 200 questions through the RAG pipeline for 2 models x 2 prompts.
Saves results to data/rag-eval-results.csv and prints a RELEVANT% summary.
"""

import sys
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

from movie_assistant.rag import rag


def main():
    GT_MODEL = 'gpt-5.4-mini'
    gt = pd.read_csv(ROOT / f'data/ground-truth-retrieval-{GT_MODEL}.csv').sample(200, random_state=42).reset_index(drop=True)
    print(f'Evaluating on {len(gt)} questions (ground truth from {GT_MODEL})')

    MODELS = ['gpt-5.6-luna', 'gpt-5.4-mini']
    PROMPT_VERSIONS = ['a', 'b']
    all_results = []

    for model in MODELS:
        for pv in PROMPT_VERSIONS:
            print(f'\n--- model={model}  prompt={pv} ---')
            for _, row in tqdm(gt.iterrows(), total=len(gt)):
                try:
                    result = rag(row['question'], model=model, prompt_version=pv)
                    all_results.append({
                        'model': model, 'prompt_version': pv,
                        'question': row['question'], 'movie_id': row['movie_id'],
                        'answer': result.answer, 'relevance': result.relevance,
                        'tokens_prompt': result.tokens_prompt,
                        'tokens_completion': result.tokens_completion,
                        'cost': result.cost,
                    })
                    time.sleep(0.2)
                except Exception as e:
                    print(f'  error: {e}')

    eval_df = pd.DataFrame(all_results)
    eval_df.to_csv(ROOT / 'data/rag-eval-results.csv', index=False)
    print(f'\nSaved {len(eval_df)} rows')

    pivot = (
        eval_df.groupby(['model', 'prompt_version', 'relevance'])
        .size().unstack(fill_value=0)
        .assign(total=lambda d: d.sum(axis=1))
    )
    for col in ['RELEVANT', 'PARTLY_RELEVANT', 'NON_RELEVANT']:
        if col in pivot:
            pivot[f'{col}_pct'] = (pivot[col] / pivot['total'] * 100).round(1)
    print(pivot[['RELEVANT_pct', 'PARTLY_RELEVANT_pct', 'NON_RELEVANT_pct', 'total']].to_string())
    print(eval_df.groupby(['model', 'prompt_version'])['cost'].sum().round(4).to_string())


if __name__ == '__main__':
    main()
