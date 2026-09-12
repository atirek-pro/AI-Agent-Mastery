"""
rag/vector_index.py
===================
Stage 1 of RAG: indexing.

Reads the curated `data/local_guides.json` corpus and (optionally) builds an
in-memory embedding index over it. Everything that knows about embeddings or
vector stores lives in this file.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import List, Optional

from langchain_community.vectorstores import InMemoryVectorStore
from langchain_core.documents import Document
from langchain_google_genai import GoogleGenerativeAIEmbeddings

from config import EMBED_MODEL, IS_TEST_MODE


def load_local_documents(path: Path) -> List[Document]:
    """Materialize curated local-guide blurbs as LangChain documents.

    Returns an empty list when the file is missing or malformed - the caller
    then falls back to keyword matching.
    """
    if not path.exists():
        return []

    try:
        raw = json.loads(path.read_text())
    except Exception:
        return []

    docs: List[Document] = []
    for row in raw:
        description = row.get("description")
        city = row.get("city")
        if not description or not city:
            continue

        interests = row.get("interests", []) or []
        metadata = {
            "city": city,
            "interests": interests,
            "source": row.get("source"),
        }

        # Prefix city + interests in the content so embeddings capture location
        # context even when the blurb itself does not mention the city.
        interest_text = ", ".join(interests) if interests else "general travel"
        content = f"City: {city}\nInterests: {interest_text}\nGuide: {description}"
        docs.append(Document(page_content=content, metadata=metadata))

    return docs


def build_vector_index(docs: List[Document]) -> Optional[InMemoryVectorStore]:
    """Embed `docs` and return a searchable in-memory vector store.

    Returns None (rather than raising) when embeddings are unavailable, e.g.
    in TEST_MODE or without an API key - the retriever handles that case.
    """
    if not docs or IS_TEST_MODE:
        return None

    try:
        embeddings = GoogleGenerativeAIEmbeddings(model=EMBED_MODEL)
        store = InMemoryVectorStore(embedding=embeddings)
        store.add_documents(docs)
        return store
    except Exception:
        return None