"""2-Stage Neural Cross-Encoder Reranker.

Reranks candidate passages from 1st-stage hybrid retrieval (BM25 + Bi-Encoder vector search)
using deep cross-attention over (query, document) pairs.
"""

import math
import re
from typing import List, Optional, Tuple

from src.models import Passage
from src.utils.constants import CROSS_ENCODER_MODEL, RERANKER_TOP_K
from src.utils.logger import setup_logger, log_event

logger = setup_logger(__name__)

# Regular expressions for technical DTC codes, connector IDs, and automotive metrics
_DTC_PATTERN = re.compile(r"\b[BCEPU][0-9]{4}\b", re.IGNORECASE)
_PART_NUM_PATTERN = re.compile(r"\b[0-9A-Z]{6,12}\b")


class CrossEncoderReranker:
    """Neural 2nd-stage reranker for candidate passages using Cross-Encoder models."""

    def __init__(self, model_name: str = CROSS_ENCODER_MODEL):
        self.model_name = model_name
        self._model = None
        self._model_loaded = False
        self._init_attempted = False

    def _load_model(self) -> None:
        """Lazy load the CrossEncoder model."""
        if self._init_attempted:
            return
        self._init_attempted = True

        try:
            from sentence_transformers import CrossEncoder
            logger.info(f"Loading CrossEncoder model: {self.model_name}")
            self._model = CrossEncoder(self.model_name)
            self._model_loaded = True
            logger.info(f"CrossEncoder '{self.model_name}' loaded successfully.")
        except Exception as e:
            logger.warning(
                f"Could not load neural CrossEncoder '{self.model_name}' ({e}). "
                "Using heuristic cross-attention scorer fallback."
            )
            self._model = None
            self._model_loaded = False

    def rerank(
        self,
        query: str,
        passages_with_scores: List[Tuple[Passage, float]],
        top_k: int = RERANKER_TOP_K,
    ) -> List[Tuple[Passage, float]]:
        """Rerank candidate passages based on deep query-passage cross-attention.

        Args:
            query: The user query or refined diagnostic search query.
            passages_with_scores: List of (Passage, initial_score) from 1st-stage retrieval.
            top_k: Maximum number of top reranked passages to return.

        Returns:
            List of (Passage, cross_encoder_score) sorted by descending score in [0.0, 1.0].
        """
        if not passages_with_scores:
            return []

        self._load_model()
        passages = [p for p, _ in passages_with_scores]

        if self._model_loaded and self._model is not None:
            try:
                pairs = [[query, p.text] for p in passages]
                raw_scores = self._model.predict(pairs)
                # Convert raw logits / scores to normalized probabilities [0.0, 1.0]
                normalized_scores = [self._sigmoid(float(s)) for s in raw_scores]
            except Exception as e:
                logger.warning(f"CrossEncoder prediction failed, falling back to heuristic: {e}")
                normalized_scores = [self._heuristic_score(query, p) for p in passages]
        else:
            normalized_scores = [self._heuristic_score(query, p) for p in passages]

        # Apply domain-specific DTC & technical keyword relevance boost
        boosted_scores = []
        for p, score in zip(passages, normalized_scores):
            boost = self._dtc_and_keyword_boost(query, p.text)
            final_score = min(1.0, score * boost)
            boosted_scores.append((p, final_score))

        # Sort by descending rerank score
        reranked = sorted(boosted_scores, key=lambda x: x[1], reverse=True)[:top_k]

        log_event(
            "cross_encoder_rerank",
            query=query[:60],
            candidates_in=len(passages_with_scores),
            reranked_out=len(reranked),
            top_score=reranked[0][1] if reranked else 0.0,
        )

        return reranked

    @staticmethod
    def _sigmoid(x: float) -> float:
        """Sigmoid activation to map unbounded logits to [0.0, 1.0]."""
        try:
            return 1.0 / (1.0 + math.exp(-max(min(x, 15.0), -15.0)))
        except OverflowError:
            return 0.0 if x < 0 else 1.0

    @staticmethod
    def _heuristic_score(query: str, passage: Passage) -> float:
        """High-precision lexical-semantic cross-scoring fallback.

        Evaluates token overlap, exact phrase alignment, header proximity, and term frequency.
        """
        q_tokens = set(re.findall(r"[a-z0-9]+", query.lower()))
        if not q_tokens:
            return 0.0

        p_text_lower = passage.text.lower()
        p_tokens = set(re.findall(r"[a-z0-9]+", p_text_lower))
        section_tokens = set(re.findall(r"[a-z0-9]+", passage.section.lower()))

        # Token overlap ratio
        overlap = len(q_tokens.intersection(p_tokens))
        overlap_ratio = overlap / len(q_tokens) if q_tokens else 0.0

        # Section header match bonus
        section_overlap = len(q_tokens.intersection(section_tokens))
        section_bonus = 0.15 if section_overlap > 0 else 0.0

        # Exact substring sequence match bonus
        query_clean = query.strip().lower()
        phrase_bonus = 0.20 if len(query_clean) > 4 and query_clean in p_text_lower else 0.0

        # Diagram bonus if query asks about diagram / schematic / relay / fuse
        visual_bonus = 0.10 if passage.is_diagram and any(t in query_clean for t in ["diagram", "schematic", "fuse", "relay", "wiring", "pin"]) else 0.0

        raw_score = (overlap_ratio * 0.65) + section_bonus + phrase_bonus + visual_bonus
        return min(1.0, max(0.05, raw_score))

    @staticmethod
    def _dtc_and_keyword_boost(query: str, text: str) -> float:
        """Boost score if specific Diagnostic Trouble Codes or exact part numbers match."""
        query_dtcs = set(_DTC_PATTERN.findall(query))
        if not query_dtcs:
            return 1.0

        text_dtcs = set(_DTC_PATTERN.findall(text))
        common_dtcs = query_dtcs.intersection(text_dtcs)
        if common_dtcs:
            return 1.35  # 35% boost for exact DTC code match
        return 1.0
