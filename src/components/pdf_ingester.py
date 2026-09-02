"""PDF ingestion using PyMuPDF4LLM (markdown text) + PyMuPDF (embedded diagram images)."""

from typing import Any, Dict, List

import pymupdf
import pymupdf4llm

from src.utils.logger import setup_logger, log_event

logger = setup_logger(__name__)


class PdfIngester:
    """Ingest a PDF into per-page markdown text and embedded diagram images."""

    def ingest(self, file_bytes: bytes) -> Dict[str, Any]:
        """Extract per-page markdown text and embedded images with page metadata.

        Args:
            file_bytes: Raw PDF bytes.

        Returns:
            Dict with:
                "pages": [{"page": int, "markdown": str}, ...]
                "images": [{"page": int, "index": int, "bytes": bytes}, ...]
        """
        doc = pymupdf.open(stream=file_bytes, filetype="pdf")
        try:
            page_chunks = pymupdf4llm.to_markdown(doc, page_chunks=True)

            pages = []
            for i, chunk in enumerate(page_chunks):
                page_number = chunk.get("metadata", {}).get("page_number", i + 1)
                pages.append({"page": page_number, "markdown": chunk.get("text", "")})

            images = []
            for page_index in range(len(doc)):
                page = doc[page_index]
                for img_idx, img in enumerate(page.get_images(full=True), start=1):
                    xref = img[0]
                    try:
                        base_image = doc.extract_image(xref)
                        images.append({
                            "page": page_index + 1,
                            "index": img_idx,
                            "bytes": base_image["image"],
                        })
                    except Exception as e:
                        logger.warning(f"Failed to extract image xref {xref} on page {page_index + 1}: {e}")

            log_event("pdf_ingest", pages=len(pages), images=len(images))
            return {"pages": pages, "images": images}
        finally:
            doc.close()
