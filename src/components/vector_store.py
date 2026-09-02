"""ChromaDB-backed vector store for semantic (embedding) retrieval."""

import uuid
from typing import List, Tuple

import chromadb

from src.models import Passage
from src.utils.logger import setup_logger, log_event

logger = setup_logger(__name__)


class VectorStore:
    """Wrap an in-memory Chroma collection for per-session semantic search."""

    def __init__(self, collection_name: str):
        self._client = chromadb.EphemeralClient()
        self._collection = self._client.get_or_create_collection(name=collection_name)
        self.passages: List[Passage] = []
        self._id_to_passage = {}

    def build(self, passages: List[Passage], embeddings: List[List[float]]) -> None:
        """Populate the collection with chunk embeddings.

        Args:
            passages: Chunked passages to index.
            embeddings: Embedding vector per passage (same order/length).
        """
        self.passages = passages
        self._id_to_passage = {}
        if not passages or not embeddings:
            return

        ids = [str(uuid.uuid4()) for _ in passages]
        metadatas = [
            {"document_id": p.document_id, "section": p.section, "is_diagram": p.is_diagram}
            for p in passages
        ]
        documents = [p.text for p in passages]

        self._id_to_passage = dict(zip(ids, passages))
        self._collection.add(ids=ids, embeddings=embeddings, metadatas=metadatas, documents=documents)
        log_event("chroma_build", passage_count=len(passages))

    def search(self, query_embedding: List[float], top_k: int = 10) -> List[Tuple[Passage, float]]:
        """Search the collection for the top-k semantically similar chunks.

        Args:
            query_embedding: Embedding vector for the query.
            top_k: Number of results to return.

        Returns:
            List of (Passage, similarity_score) tuples, sorted by descending similarity.
        """
        if not self.passages:
            return []

        result = self._collection.query(
            query_embeddings=[query_embedding], n_results=min(top_k, len(self.passages))
        )
        ids = result.get("ids", [[]])[0]
        distances = result.get("distances", [[]])[0]

        results = []
        for _id, distance in zip(ids, distances):
            passage = self._id_to_passage.get(_id)
            if passage:
                similarity = 1.0 / (1.0 + distance)
                results.append((passage, similarity))

        return results
