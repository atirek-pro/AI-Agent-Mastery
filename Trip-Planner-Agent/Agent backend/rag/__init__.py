"""
rag
===
Retrieval-Augmented Generation for the local-guide agent, split by stage:

    vector_index.py  -> load the corpus and build the embedding index
    retriever.py     -> turn a request into ranked documents
    generation.py    -> turn ranked documents into an answer

Keeping the stages separate mirrors how RAG pipelines are usually reasoned
about (index -> retrieve -> generate) and makes each one independently testable.
"""

from rag.retriever import LOCAL_GUIDE_RETRIEVER

__all__ = ["LOCAL_GUIDE_RETRIEVER"]