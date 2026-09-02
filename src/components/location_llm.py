"""Stage 3: Location LLM — pick Mapbox search terms for the diagnosed system, then
orchestrate Mapbox MCP tool calls (geocode, category search, place details, static map)
to find, rank, and map nearby service stations for the user-supplied location.
"""

import base64
import json
import math
from typing import List, Optional, Tuple

from openai import OpenAI

from src.models import DiagnosisResult, LocationResult, ServiceStation
from src.components.mapbox_mcp_client import MapboxMCPClient, MapboxMCPError
from src.utils.constants import (
    LOCATION_MODEL,
    OPENROUTER_API_BASE_URL,
    OPENROUTER_API_KEY,
    QUERY_TIMEOUT_SECONDS,
    STATION_MAP_SIZE,
    STATION_MAP_ZOOM,
    STATION_SEARCH_LIMIT,
)
from src.utils.logger import setup_logger, log_event

logger = setup_logger(__name__)

_SYSTEM_PROMPT = """You help find a real-world auto repair shop for a diagnosed vehicle problem. \
Given the likely causes of the problem, choose the best Mapbox category search term and a plain \
free-text fallback search phrase for an auto repair shop.

Respond ONLY with JSON in this exact shape, with no extra commentary:
{"category": "car_repair", "fallback_query": "auto repair shop"}"""

_DEFAULT_CATEGORY = "car_repair"
_DEFAULT_FALLBACK_QUERY = "auto repair shop"
_MARKER_LABELS = "bcdefghij"


class LocationLLM:
    """Stage 3: diagnosis + user-entered address -> ranked nearby service stations."""

    def __init__(self):
        self.mapbox = MapboxMCPClient()
        self._openai_client: Optional[OpenAI] = None

    def find_service_stations(self, diagnosis: DiagnosisResult, address_text: str) -> LocationResult:
        """Geocode `address_text`, search for nearby repair shops relevant to the
        diagnosis, rank them by straight-line distance, and render a static map.
        """
        if not address_text.strip():
            return LocationResult(query_location=address_text, error_message="Please enter a location.")

        try:
            origin = self._geocode(address_text)
        except MapboxMCPError as e:
            logger.exception(f"Geocoding failed for '{address_text}': {e}")
            return LocationResult(query_location=address_text, error_message=f"Could not look up that location: {e}")
        if origin is None:
            return LocationResult(query_location=address_text, error_message="No location found for that address.")
        origin_lon, origin_lat = origin

        category, fallback_query = self._choose_search_terms(diagnosis)

        try:
            stations = self._category_search(category, origin_lon, origin_lat)
            if not stations:
                stations = self._text_search(fallback_query, origin_lon, origin_lat)
        except MapboxMCPError as e:
            logger.exception(f"Mapbox station search failed: {e}")
            return LocationResult(query_location=address_text, error_message=f"Station search failed: {e}")

        stations = self._rank_by_distance(stations, origin_lon, origin_lat)[:STATION_SEARCH_LIMIT]
        self._enrich_with_details(stations)

        map_image_bytes = None
        try:
            map_image_bytes = self._render_map(origin_lon, origin_lat, stations)
        except MapboxMCPError as e:
            logger.warning(f"Static map image failed (non-fatal): {e}")

        log_event("location_lookup", stations=len(stations), category=category)
        return LocationResult(query_location=address_text, stations=stations, map_image_bytes=map_image_bytes)

    def _choose_search_terms(self, diagnosis: DiagnosisResult) -> Tuple[str, str]:
        """Ask a small LLM to translate the diagnosis into a Mapbox category + fallback
        free-text query. Falls back to generic auto-repair terms on any failure."""
        try:
            if self._openai_client is None:
                if not OPENROUTER_API_KEY:
                    raise ValueError("OPENROUTER_API_KEY not set")
                self._openai_client = OpenAI(api_key=OPENROUTER_API_KEY, base_url=OPENROUTER_API_BASE_URL)

            causes = ", ".join(c.get("cause", "") for c in diagnosis.differential) or "unknown"
            response = self._openai_client.chat.completions.create(
                model=LOCATION_MODEL,
                messages=[
                    {"role": "system", "content": _SYSTEM_PROMPT},
                    {"role": "user", "content": f"Likely causes: {causes}"},
                ],
                temperature=0.2,
                max_tokens=100,
                timeout=QUERY_TIMEOUT_SECONDS,
            )
            parsed = self._parse_json(response.choices[0].message.content)
            category = parsed.get("category") or _DEFAULT_CATEGORY
            fallback_query = parsed.get("fallback_query") or _DEFAULT_FALLBACK_QUERY
            return category, fallback_query
        except Exception as e:
            logger.warning(f"Location LLM term selection failed, using defaults: {e}")
            return _DEFAULT_CATEGORY, _DEFAULT_FALLBACK_QUERY

    def _geocode(self, address_text: str) -> Optional[Tuple[float, float]]:
        result = self.mapbox.call_tool("search_and_geocode_tool", {"q": address_text, "limit": 1})
        feature = self._first_feature(result)
        if feature is None:
            return None
        lon, lat = feature["geometry"]["coordinates"]
        return lon, lat

    def _category_search(self, category: str, lon: float, lat: float) -> List[ServiceStation]:
        result = self.mapbox.call_tool(
            "category_search_tool",
            {
                "category": category,
                "proximity": {"longitude": lon, "latitude": lat},
                "limit": STATION_SEARCH_LIMIT,
                "format": "json_string",
            },
        )
        return [self._feature_to_station(f) for f in self._features(result)]

    def _text_search(self, query: str, lon: float, lat: float) -> List[ServiceStation]:
        result = self.mapbox.call_tool(
            "search_and_geocode_tool",
            {"q": query, "proximity": {"longitude": lon, "latitude": lat}, "limit": STATION_SEARCH_LIMIT},
        )
        return [self._feature_to_station(f) for f in self._features(result)]

    def _enrich_with_details(self, stations: List[ServiceStation]) -> None:
        """Best-effort phone/website lookup per station; failures are non-fatal."""
        for station in stations:
            if not station.mapbox_id:
                continue
            try:
                result = self.mapbox.call_tool("place_details_tool", {"mapbox_id": station.mapbox_id})
                details = result.get("structuredContent", {}) or {}
                station.phone = details.get("phone") or station.phone
                station.website = details.get("website") or station.website
            except MapboxMCPError as e:
                logger.warning(f"place_details_tool failed for {station.name}: {e}")

    def _render_map(self, lon: float, lat: float, stations: List[ServiceStation]) -> Optional[bytes]:
        overlays = [{"type": "marker", "longitude": lon, "latitude": lat, "color": "1a73e8", "label": "a"}]
        for i, station in enumerate(stations):
            if station.longitude is None or station.latitude is None:
                continue
            overlays.append({
                "type": "marker",
                "longitude": station.longitude,
                "latitude": station.latitude,
                "color": "d93025",
                "label": _MARKER_LABELS[i] if i < len(_MARKER_LABELS) else "",
            })
        width, height = STATION_MAP_SIZE
        result = self.mapbox.call_tool(
            "static_map_image_tool",
            {
                "center": {"longitude": lon, "latitude": lat},
                "zoom": STATION_MAP_ZOOM,
                "size": {"width": width, "height": height},
                "style": "mapbox/streets-v12",
                "overlays": overlays,
            },
        )
        for block in result.get("content", []):
            if block.get("type") == "image" and block.get("data"):
                return base64.b64decode(block["data"])
        return None

    @staticmethod
    def _rank_by_distance(stations: List[ServiceStation], lon: float, lat: float) -> List[ServiceStation]:
        def distance(station: ServiceStation) -> float:
            if station.distance_meters is not None:
                return station.distance_meters
            if station.longitude is None or station.latitude is None:
                return float("inf")
            return LocationLLM._haversine_meters(lat, lon, station.latitude, station.longitude)

        return sorted(stations, key=distance)

    @staticmethod
    def _haversine_meters(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        radius = 6371000
        phi1, phi2 = math.radians(lat1), math.radians(lat2)
        d_phi = math.radians(lat2 - lat1)
        d_lambda = math.radians(lon2 - lon1)
        a = math.sin(d_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
        return 2 * radius * math.asin(math.sqrt(a))

    @staticmethod
    def _features(result: dict) -> List[dict]:
        structured = result.get("structuredContent") or {}
        return structured.get("features") or []

    @staticmethod
    def _first_feature(result: dict) -> Optional[dict]:
        features = LocationLLM._features(result)
        return features[0] if features else None

    @staticmethod
    def _feature_to_station(feature: dict) -> ServiceStation:
        props = feature.get("properties", {}) or {}
        geometry = feature.get("geometry", {}) or {}
        coords = geometry.get("coordinates") or [None, None]
        return ServiceStation(
            name=props.get("name", "Unknown"),
            address=props.get("full_address") or props.get("place_formatted", ""),
            distance_meters=props.get("distance"),
            mapbox_id=props.get("mapbox_id", ""),
            longitude=coords[0],
            latitude=coords[1],
        )

    @staticmethod
    def _parse_json(content: str) -> dict:
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
