"""
minsearch — lightweight TF-IDF in-memory search.
Copied verbatim from alexeygrigorev/fitness-assistant.
"""

import re
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np


class Index:
    def __init__(self, text_fields, keyword_fields, vectorizer_params=None):
        self.text_fields = text_fields
        self.keyword_fields = keyword_fields
        self.vectorizer_params = vectorizer_params or {}
        self.vectorizers = {}
        self.keyword_df = None
        self.records = []

    def fit(self, records):
        self.records = records
        for field in self.text_fields:
            texts = [str(r.get(field, "")) for r in records]
            v = TfidfVectorizer(**self.vectorizer_params)
            v.fit(texts)
            self.vectorizers[field] = v
        if self.keyword_fields:
            import pandas as pd
            self.keyword_df = pd.DataFrame([
                {f: r.get(f, "") for f in self.keyword_fields}
                for r in records
            ])
        return self

    def search(self, query, filter_dict=None, boost_dict=None, num_results=10):
        scores = np.zeros(len(self.records))
        for field, v in self.vectorizers.items():
            q_vec = v.transform([query])
            d_vecs = v.transform([str(r.get(field, "")) for r in self.records])
            sim = cosine_similarity(q_vec, d_vecs)[0]
            boost = (boost_dict or {}).get(field, 1.0)
            scores += boost * sim

        if filter_dict and self.keyword_df is not None:
            mask = np.ones(len(self.records), dtype=bool)
            for field, value in filter_dict.items():
                if field in self.keyword_df.columns:
                    mask &= (self.keyword_df[field] == value).values
            scores[~mask] = -1

        top_idx = np.argsort(-scores)[:num_results]
        return [self.records[i] for i in top_idx if scores[i] > 0]
