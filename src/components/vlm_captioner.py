"""Diagram captioning using a vision-language model (VLM), via the OpenRouter chat API."""

import base64

from openai import OpenAI

from src.utils.logger import setup_logger
from src.utils.constants import OPENROUTER_API_KEY, OPENROUTER_API_BASE_URL, VLM_MODEL

logger = setup_logger(__name__)

_PROMPT = (
    "Describe this vehicle service manual diagram for a technician: identify the component, "
    "connectors, wiring colors, part numbers, and any labels visible. Be concise but complete."
)


class VLMCaptioner:
    """Generate text captions for diagram images extracted from service manuals."""

    def __init__(self):
        if not OPENROUTER_API_KEY:
            raise ValueError("OPENROUTER_API_KEY not set in environment or secrets")
        self.client = OpenAI(api_key=OPENROUTER_API_KEY, base_url=OPENROUTER_API_BASE_URL)

    def caption(self, image_bytes: bytes) -> str:
        """Caption a single diagram image.

        Args:
            image_bytes: Raw image bytes (e.g. PNG/JPEG extracted from a PDF page).

        Returns:
            Generated caption text, or an empty string if captioning fails.
        """
        try:
            b64 = base64.b64encode(image_bytes).decode("utf-8")
            response = self.client.chat.completions.create(
                model=VLM_MODEL,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": _PROMPT},
                            {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64}"}},
                        ],
                    }
                ],
                max_tokens=300,
                timeout=30,
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            logger.warning(f"VLM captioning failed: {e}")
            return ""
