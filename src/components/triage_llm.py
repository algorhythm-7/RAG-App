"""Stage 1: Triage LLM — map a driver's symptom description to candidate vehicle
systems and targeted search queries for hybrid retrieval."""

import json

from openai import OpenAI

from src.models import TriageResult
from src.utils.constants import OPENROUTER_API_BASE_URL, OPENROUTER_API_KEY, QUERY_TIMEOUT_SECONDS, TRIAGE_MODEL
from src.utils.logger import setup_logger, log_event

logger = setup_logger(__name__)

_SYSTEM_PROMPT = """You are a vehicle diagnostic triage assistant. Given a driver's description of a \
symptom, identify the vehicle systems likely involved (e.g. "brakes", "HVAC", "electrical", "engine") \
and produce 2-4 targeted search queries to look up relevant sections of the service manual, wiring \
diagrams, and body repair guides.

Respond ONLY with JSON in this exact shape, with no extra commentary:
{"systems": ["..."], "search_queries": ["...", "..."]}"""


class TriageLLM:
    """Stage 1 triage: symptom -> candidate systems + search queries."""

    def __init__(self):
        if not OPENROUTER_API_KEY:
            raise ValueError("OPENROUTER_API_KEY not set in environment or secrets")
        self.client = OpenAI(api_key=OPENROUTER_API_KEY, base_url=OPENROUTER_API_BASE_URL)

    def triage(self, symptom_text: str) -> TriageResult:
        """Identify likely systems and search queries for a symptom description.

        Falls back to using the raw symptom text as the sole search query if the
        LLM call or JSON parsing fails, so retrieval can still proceed.
        """
        try:
            response = self.client.chat.completions.create(
                model=TRIAGE_MODEL,
                messages=[
                    {"role": "system", "content": _SYSTEM_PROMPT},
                    {"role": "user", "content": symptom_text},
                ],
                temperature=0.2,
                max_tokens=300,
                timeout=QUERY_TIMEOUT_SECONDS,
            )
            parsed = self._parse_json(response.choices[0].message.content)
            systems = parsed.get("systems", [])
            search_queries = parsed.get("search_queries") or [symptom_text]

            log_event("triage", systems=len(systems), queries=len(search_queries))
            return TriageResult(systems=systems, search_queries=search_queries)
        except Exception as e:
            logger.exception(f"Triage LLM failed, falling back to raw symptom query: {e}")
            return TriageResult(systems=[], search_queries=[symptom_text])

    def _parse_json(self, content: str) -> dict:
        content = content.strip()
        if content.startswith("```"):
            content = content.strip("`")
            content = content.split("json", 1)[-1] if content.lower().startswith("json") else content
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            start, end = content.find("{"), content.rfind("}")
            if start != -1 and end != -1:
                try:
                    return json.loads(content[start:end + 1])
                except json.JSONDecodeError:
                    pass
            return {}
