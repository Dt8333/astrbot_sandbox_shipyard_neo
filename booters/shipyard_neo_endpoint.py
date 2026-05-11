from __future__ import annotations

from urllib.parse import urlparse, urlunparse

DEFAULT_SHIPYARD_NEO_ENDPOINT = "http://127.0.0.1:8114"
SHIPYARD_NEO_AUTO_ENDPOINT = "__auto__"
SHIPYARD_NEO_AUTO_START_HOSTS = {"127.0.0.1", "localhost"}


def normalize_shipyard_neo_endpoint(endpoint: str | None) -> str:
    raw = (endpoint or "").strip()
    if not raw or raw == SHIPYARD_NEO_AUTO_ENDPOINT:
        return DEFAULT_SHIPYARD_NEO_ENDPOINT

    parsed = urlparse(raw)
    if not parsed.scheme or not parsed.hostname:
        return raw
    try:
        port = parsed.port
    except ValueError:
        return raw

    if (
        parsed.scheme.lower() == "http"
        and (parsed.hostname or "").lower() in SHIPYARD_NEO_AUTO_START_HOSTS
        and port == 8114
        and parsed.path in {"", "/"}
        and not parsed.params
        and not parsed.query
        and not parsed.fragment
    ):
        return DEFAULT_SHIPYARD_NEO_ENDPOINT

    netloc = parsed.hostname
    if port is not None:
        netloc = f"{netloc}:{port}"
    path = "" if parsed.path == "/" else parsed.path.rstrip("/")
    return urlunparse(
        (
            parsed.scheme.lower(),
            netloc,
            path,
            parsed.params,
            parsed.query,
            parsed.fragment,
        )
    )


def is_shipyard_neo_auto_endpoint(endpoint: str | None) -> bool:
    return normalize_shipyard_neo_endpoint(endpoint) == DEFAULT_SHIPYARD_NEO_ENDPOINT
