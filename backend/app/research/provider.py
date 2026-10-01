from abc import ABC, abstractmethod
from ipaddress import ip_address
from urllib.parse import urlsplit

from app.research.models import ResearchBatch, ResearchQuery, ResearchResult


class ResearchProviderError(RuntimeError):
    """A provider could not complete source discovery or retrieval."""


class ResearchProvider(ABC):
    """Provider boundary for source search and source retrieval.

    Implementations should also set a timeout on their network client. Cancelling
    a timed-out synchronous Python worker cannot interrupt an in-flight socket call.
    """

    name = "provider"
    mode = "external"
    timeout_seconds = 30.0

    @abstractmethod
    def search(self, query: ResearchQuery) -> ResearchBatch:
        """Search for sources and return only source records actually received."""

    @abstractmethod
    def fetch(self, url: str, query: ResearchQuery) -> ResearchResult:
        """Retrieve one source. Implementations must validate URLs before fetching."""


class UnconfiguredResearchProvider(ResearchProvider):
    """Honest local fallback: generate queries but do not invent source records."""

    name = "unconfigured"
    mode = "local_demo"

    def search(self, query: ResearchQuery) -> ResearchBatch:
        return ResearchBatch(query=query, results=[])

    def fetch(self, url: str, query: ResearchQuery) -> ResearchResult:
        raise ResearchProviderError("External source retrieval is not configured")


def validate_fetch_url(value: str) -> str:
    """Reject non-public HTTP destinations before a provider fetches a URL."""
    try:
        parts = urlsplit(value)
        if parts.scheme not in {"http", "https"} or not parts.hostname:
            raise ValueError
        if parts.username or parts.password:
            raise ValueError
        host = parts.hostname.rstrip(".").lower()
        if host in {"localhost", "localhost.localdomain"} or host.endswith(".localhost"):
            raise ValueError
        try:
            address = ip_address(host)
        except ValueError:
            address = None
        if address is not None and (
            address.is_private or address.is_loopback or address.is_link_local
            or address.is_reserved or address.is_unspecified
        ):
            raise ValueError
        return value
    except ValueError as exc:
        raise ResearchProviderError("Provider URL is not a safe public HTTP URL") from exc
