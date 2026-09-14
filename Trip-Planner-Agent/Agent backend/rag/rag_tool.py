import json
import os

import faiss
import numpy as np

from sentence_transformers import SentenceTransformer
from agno.tools import tool


# Configuration

GUIDES_FILE = "local_guides.json"

FAISS_DIR = "faiss_index"
FAISS_INDEX_FILE = os.path.join(
    FAISS_DIR,
    "local_guides.index"
)

METADATA_FILE = os.path.join(
    FAISS_DIR,
    "metadata.json"
)

EMBEDDING_MODEL = "all-MiniLM-L6-v2"
TOP_K = 3


# Initialize embedding model
embedding_model = SentenceTransformer(
    EMBEDDING_MODEL
)


# Load guides
with open(
    GUIDES_FILE,
    "r",
    encoding="utf-8"
) as f:
    guides = json.load(f)


# Prepare documents
documents = []
metadatas = []

for guide in guides:

    text = (
        f"City: {guide['city']}. "
        f"Interests: {', '.join(guide['interests'])}. "
        f"Experience: {guide['description']}"
    )

    documents.append(text)

    metadatas.append({
        "city": guide["city"],
        "interests": ", ".join(
            guide["interests"]
        ),
        "source": guide["source"],
        "description": guide["description"],
    })


# Create / Load FAISS index
def create_faiss_index():

    # Create directory if it doesn't exist
    os.makedirs(
        FAISS_DIR,
        exist_ok=True
    )

    # --------------------------------------------------------
    # Generate embeddings
    # --------------------------------------------------------

    embeddings = embedding_model.encode(
        documents,
        convert_to_numpy=True
    ).astype("float32")

    # Normalize for cosine similarity
    faiss.normalize_L2(embeddings)

    # Embedding dimension
    dimension = embeddings.shape[1]

    # Inner Product + normalized vectors
    # = cosine similarity
    index = faiss.IndexFlatIP(
        dimension
    )

    # Add vectors
    index.add(embeddings)

    # --------------------------------------------------------
    # Save FAISS index
    # --------------------------------------------------------

    faiss.write_index(
        index,
        FAISS_INDEX_FILE
    )

    # --------------------------------------------------------
    # Save documents + metadata
    # --------------------------------------------------------

    with open(
        METADATA_FILE,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            {
                "documents": documents,
                "metadatas": metadatas
            },
            f,
            indent=2,
            ensure_ascii=False
        )

    print(
        f"✅ Created FAISS index: "
        f"{FAISS_INDEX_FILE}"
    )

    print(
        f"✅ Saved metadata: "
        f"{METADATA_FILE}"
    )

    return index


def load_faiss_index():

    print(
        f"📂 Loading existing FAISS index..."
    )

    index = faiss.read_index(
        FAISS_INDEX_FILE
    )

    with open(
        METADATA_FILE,
        "r",
        encoding="utf-8"
    ) as f:

        data = json.load(f)

    loaded_documents = data["documents"]
    loaded_metadatas = data["metadatas"]

    print(
        f"✅ Loaded {index.ntotal} "
        f"vectors from FAISS"
    )

    return (
        index,
        loaded_documents,
        loaded_metadatas
    )


# Initialize RAG
if (
    os.path.exists(FAISS_INDEX_FILE)
    and os.path.exists(METADATA_FILE)
):

    index, documents, metadatas = (
        load_faiss_index()
    )

else:

    index = create_faiss_index()


# FAISS Retrieval
def search_faiss(
    query: str,
    top_k: int = TOP_K
):

    # Create query embedding
    query_embedding = (
        embedding_model.encode(
            [query],
            convert_to_numpy=True
        )
        .astype("float32")
    )

    # Normalize query
    faiss.normalize_L2(
        query_embedding
    )

    # Search
    scores, indices = index.search(
        query_embedding,
        top_k
    )

    results = []

    for score, idx in zip(
        scores[0],
        indices[0]
    ):

        if idx == -1:
            continue

        results.append({
            "score": float(score),
            "document": documents[idx],
            "metadata": metadatas[idx]
        })

    return results


# Agno Tool
@tool
def local_flavor_rag_powered(
    destination: str,
    interests: str = "local culture"
) -> str:
    """
    Suggest authentic local experiences using
    FAISS semantic retrieval.
    """

    # Construct query
    query_text = (
        f"{destination} "
        f"{interests} "
        f"authentic experiences"
    )

    # Retrieve relevant documents
    results = search_faiss(
        query=query_text,
        top_k=TOP_K
    )

    # No results
    if not results:

        return (
            f"Explore {destination}'s unique "
            f"{interests} through markets, "
            f"neighborhoods, and local eateries."
        )

    # Format results
    suggestions = []

    for result in results:

        meta = result["metadata"]

        suggestions.append(
            f"📍 **{meta['city']}** — "
            f"{meta['description']} "
            f"(Interests: {meta['interests']})"
        )

    return (
        f"Here are some authentic "
        f"{interests} experiences near "
        f"{destination}:\n\n"
        + "\n\n".join(suggestions)
    )