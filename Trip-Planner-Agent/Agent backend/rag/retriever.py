"""
rag/retriever.py
================
Stage 2 of RAG: retrieval.

Wraps the vector index behind a small class that always returns a list of
`{content, metadata, score}` dicts. If semantic search is unavailable it degrades
to keyword scoring over the raw documents, so the agent never gets nothing.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from langchain_core.documents import Document

from config import ENABLE_RAG, LOCAL_GUIDES_PATH
from rag.vector_index import build_vector_index, load_local_documents


class LocalGuideRetriever:
    """Embeds curated blurbs and returns the best matches for a request."""

    def __init__(self, data_path):
        # Load the corpus and try to build the index once, at construction time.
        self._docs = load_local_documents(data_path)
        self._vectorstore = (
            build_vector_index(self._docs) if ENABLE_RAG else None
        )

    @property
    def is_empty(self) -> bool:
        """True when the corpus could not be loaded at all."""
        return not self._docs

    def retrieve(
        self,
        destination: str,
        interests: Optional[str],
        *,
        k: int = 3,
    ) -> List[Dict[str, Any]]:
        """Return the top-k guide blurbs for a destination/interests pair."""
        if not ENABLE_RAG or self.is_empty:
            return []

        # No index (missing key, embeddings failed, ...) -> keyword matching.
        if not self._vectorstore:
            return self._keyword_fallback(destination, interests, k=k)

        query = destination
        if interests:
            query = f"{destination} with interests {interests}"

        try:
            # Using the LangChain retriever ensures query embeddings + searches
            # are traced automatically.
            retriever = self._vectorstore.as_retriever(search_kwargs={"k": max(k, 4)})
            docs = retriever.invoke(query)
        except Exception:
            return self._keyword_fallback(destination, interests, k=k)

        results = []
        for doc in docs[:k]:
            score_val: float = 0.0
            if isinstance(doc.metadata, dict):
                maybe_score = doc.metadata.get("score")
                if isinstance(maybe_score, (int, float)):
                    score_val = float(maybe_score)

            results.append(
                {
                    "content": doc.page_content,
                    "metadata": doc.metadata,
                    "score": score_val,
                }
            )

        if not results:
            return self._keyword_fallback(destination, interests, k=k)
        return results

    def _keyword_fallback(
        self,
        destination: str,
        interests: Optional[str],
        *,
        k: int,
    ) -> List[Dict[str, Any]]:
        """Score documents by city + interest keyword overlap.

        A crude but dependency-free ranking used when embeddings are not
        available.
        """
        dest_lower = destination.lower()
        interest_terms = [
            part.strip().lower() for part in (interests or "").split(",") if part.strip()
        ]

        def _score(doc: Document) -> int:
            score = 0
            city_match = doc.metadata.get("city", "").lower()
            if dest_lower and dest_lower.split(",")[0] in city_match:
                score += 2
            for term in interest_terms:
                if term and term in " ".join(doc.metadata.get("interests") or []).lower():
                    score += 1
                if term and term in doc.page_content.lower():
                    score += 1
            return score

        scored_docs = [(_score(doc), doc) for doc in self._docs]
        scored_docs.sort(key=lambda item: item[0], reverse=True)

        results = []
        for score, doc in scored_docs[:k]:
            city_value = doc.metadata.get("city", "").lower()
            # Drop clearly irrelevant hits unless the city itself matched.
            if score <= 0 and dest_lower not in city_value:
                continue
            results.append(
                {
                    "content": doc.page_content,
                    "metadata": doc.metadata,
                    "score": float(score),
                }
            )
        return results


# Singleton retriever keeps embeddings warm across requests.
LOCAL_GUIDE_RETRIEVER = LocalGuideRetriever(LOCAL_GUIDES_PATH)