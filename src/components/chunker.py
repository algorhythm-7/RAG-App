"""Header-aware chunking with overlap for the diagnostic retrieval pipeline."""

import re
from typing import List, Tuple

from src.models import Passage
from src.utils.logger import setup_logger, log_event
from src.utils.constants import CHUNK_MAX_CHARS, CHUNK_OVERLAP_CHARS

logger = setup_logger(__name__)

_HEADER_PATTERN = re.compile(r"^(#{1,4}\s+.+)$", re.MULTILINE)


class Chunker:
    """Split page-level passages into header-aware chunks with trailing overlap."""

    def chunk_passages(self, passages: List[Passage]) -> List[Passage]:
        """Chunk passages by markdown header, splitting oversized sections and
        carrying a small trailing overlap from the previous chunk into the next
        one so retrieval doesn't lose context at chunk boundaries.

        Diagram passages (VLM captions) are already atomic and pass through unchanged.

        Args:
            passages: Page-level passages (as produced by ingestion).

        Returns:
            List of chunked passages, ready for indexing.
        """
        chunks: List[Passage] = []

        for passage in passages:
            if passage.is_diagram:
                chunks.append(self._clone(passage, passage.text, len(chunks)))
                continue

            for header, body in self._split_by_headers(passage.text):
                section_text = f"{header}\n{body}".strip() if header else body.strip()
                if not section_text:
                    continue

                section_label = f"{passage.section} > {header}" if header else passage.section
                # Overlap only carries between sub-chunks of the SAME header section
                # (i.e. when a section is too large and had to be split); it resets
                # at each new header so unrelated sections don't bleed into each other.
                prev_tail = ""
                for sub in self._split_to_max(section_text):
                    combined = f"{prev_tail}\n\n{sub}".strip() if prev_tail else sub
                    chunks.append(self._clone(passage, combined, len(chunks), section=section_label))
                    prev_tail = sub[-CHUNK_OVERLAP_CHARS:] if len(sub) > CHUNK_OVERLAP_CHARS else sub

        log_event("chunk_passages", input_passages=len(passages), output_chunks=len(chunks))
        return chunks if chunks else passages

    def _split_by_headers(self, text: str) -> List[Tuple[str, str]]:
        """Split text into (header, body) sections based on markdown headers."""
        matches = list(_HEADER_PATTERN.finditer(text))
        if not matches:
            return [("", text)]

        sections = []
        if matches[0].start() > 0:
            sections.append(("", text[:matches[0].start()]))

        for i, match in enumerate(matches):
            header = match.group(1).strip()
            start = match.end()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
            sections.append((header, text[start:end]))

        return sections

    def _split_to_max(self, text: str) -> List[str]:
        """Split text into chunks no larger than CHUNK_MAX_CHARS, on paragraph boundaries."""
        if len(text) <= CHUNK_MAX_CHARS:
            return [text]

        paragraphs = text.split("\n\n")
        chunks, current = [], ""
        for para in paragraphs:
            if current and len(current) + len(para) + 2 > CHUNK_MAX_CHARS:
                chunks.append(current)
                current = para
            else:
                current = f"{current}\n\n{para}" if current else para
        if current:
            chunks.append(current)

        return chunks

    def _clone(self, passage: Passage, text: str, index: int, section: str = None) -> Passage:
        return Passage(
            text=text,
            section=section or passage.section,
            document_id=passage.document_id,
            passage_index=index,
            image_bytes=passage.image_bytes,
            is_diagram=passage.is_diagram,
        )
