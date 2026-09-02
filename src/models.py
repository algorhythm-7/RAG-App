"""Data models for the application."""

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class Passage:
    """A text passage extracted from a document.
    
    Attributes:
        text: The extracted text content.
        section: The document section or page reference.
        document_id: ID of the source document.
        passage_index: Sequential index within the document.
        image_bytes: Optional raw image bytes (for diagram passages).
        is_diagram: Whether this passage contains an embedded image.
    """
    text: str
    section: str
    document_id: str
    passage_index: int = 0
    image_bytes: Optional[bytes] = None
    is_diagram: bool = False


@dataclass
class Document:
    """A document that has been uploaded and parsed.
    
    Attributes:
        document_id: Unique identifier for this document.
        filename: Original filename.
        file_format: Format type (pdf, image, excel, etc.).
        file_hash: SHA-256 hash for deduplication.
        parsed_successfully: Whether parsing succeeded.
        passages: List of extracted passages.
        parse_error_message: Error message if parsing failed.
    """
    document_id: str
    filename: str
    file_format: str
    file_hash: str
    parsed_successfully: bool
    passages: List[Passage] = field(default_factory=list)
    parse_error_message: Optional[str] = None


@dataclass
class QueryResult:
    """Result of a query against the documents.
    
    Attributes:
        status: success, no_results, out_of_scope, or error.
        answer: The generated answer or error message.
        sources: List of source attributions (document + passage).
        confidence: Confidence score (0-1).
        response_time_ms: Time taken to process query.
    """
    status: str
    answer: str
    sources: List[dict] = field(default_factory=list)
    confidence: float = 0.0
    response_time_ms: int = 0


@dataclass
class SourceAttribution:
    """Attribution for a source passage used in an answer.
    
    Attributes:
        document_id: ID of the source document.
        document_name: Filename of the source document.
        section: Section/page reference in the document.
        passage: The exact text passage used.
    """
    document_id: str
    document_name: str
    section: str
    passage: str


class ParseError(Exception):
    """Raised when document parsing fails."""
    pass


@dataclass
class TriageResult:
    """Stage 1 output: candidate vehicle systems and targeted search queries for a symptom.

    Attributes:
        systems: Vehicle systems likely involved (e.g. "brakes", "HVAC").
        search_queries: Targeted queries used to drive hybrid retrieval.
    """
    systems: List[str] = field(default_factory=list)
    search_queries: List[str] = field(default_factory=list)


@dataclass
class DiagnosisResult:
    """Stage 2 output: differential diagnosis produced from hybrid-retrieved context.

    Attributes:
        thinking: The reasoning LLM's internal reasoning trace (shown in the UI's thinking pane).
        steps: Ordered diagnostic steps for the technician/owner to follow.
        differential: Ranked list of candidate causes, each a dict with cause/likelihood/evidence.
        cited_pages: Manual page/section references backing the diagnosis.
        diagrams: Diagram passages (section + image_bytes) relevant to the diagnosis.
        confidence: Confidence score (0-1).
        response_time_ms: Time taken to process the diagnosis.
    """
    thinking: str = ""
    steps: List[str] = field(default_factory=list)
    differential: List[dict] = field(default_factory=list)
    cited_pages: List[str] = field(default_factory=list)
    diagrams: List[dict] = field(default_factory=list)
    confidence: float = 0.0
    response_time_ms: int = 0


@dataclass
class ServiceStation:
    """A candidate repair/service station returned by the Mapbox location lookup.

    Attributes:
        name: Business name.
        address: Full or formatted address.
        distance_meters: Straight-line distance from the user's location, if known.
        phone: Phone number, if available.
        website: Website URL, if available.
        longitude: Station longitude.
        latitude: Station latitude.
        mapbox_id: Mapbox feature ID (used to fetch place details).
    """
    name: str
    address: str = ""
    distance_meters: Optional[float] = None
    phone: str = ""
    website: str = ""
    longitude: Optional[float] = None
    latitude: Optional[float] = None
    mapbox_id: str = ""


@dataclass
class LocationResult:
    """Stage 3 output: ranked service stations near a user-supplied location.

    Attributes:
        query_location: The address/place text the user entered.
        stations: Candidate stations, nearest first.
        map_image_bytes: Optional static map image (PNG/JPEG) with station markers.
        error_message: Set if the lookup failed (e.g. couldn't geocode the address).
    """
    query_location: str = ""
    stations: List[ServiceStation] = field(default_factory=list)
    map_image_bytes: Optional[bytes] = None
    error_message: Optional[str] = None
