"""BM25 lexical index for exact-match retrieval (DTC codes, part numbers, connector IDs)."""

import re
from typing import List, Tuple

from rank_bm25 import BM25Plus

from src.models import Passage
from src.utils.logger import setup_logger, log_event

logger = setup_logger(__name__)

_TOKEN_PATTERN = re.compile(r"[A-Za-z0-9]+")


def _tokenize(text: str) -> List[str]:
    return [t.lower() for t in _TOKEN_PATTERN.findall(text)]


class BM25Index:
    """Build and query a BM25 index over chunk text."""

    def __init__(self):
        self._bm25 = None
        self.passages: List[Passage] = []

    def build(self, passages: List[Passage]) -> None:
        """Build the BM25 index from a list of chunks.

        Args:
            passages: Chunked passages to index.
        """
        self.passages = passages
        if not passages:
            self._bm25 = None
            return

        corpus = [_tokenize(p.text) for p in passages]
        # BM25Plus (rather than BM25Okapi) avoids zero/negative scores for terms
        # that appear in a large share of a small corpus - important for short,
        # DTC/part-number-heavy manual chunks.
        self._bm25 = BM25Plus(corpus)
        log_event("bm25_build", passage_count=len(passages))

    def search(self, query: str, top_k: int = 10) -> List[Tuple[Passage, float]]:
        """Search the index for the top-k lexical matches.

        Args:
            query: Search query text.
            top_k: Number of results to return.

        Returns:
            List of (Passage, bm25_score) tuples, sorted by descending score.
        """
        if not self._bm25 or not self.passages:
            return []

        scores = self._bm25.get_scores(_tokenize(query))
        ranked_indices = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)

        return [
            (self.passages[i], float(scores[i]))
            for i in ranked_indices[:top_k]
            if scores[i] > 0
        ]
