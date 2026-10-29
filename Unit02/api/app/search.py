"""
Elasticsearch = search engine ON TOP of MongoDB (DEVOP2 Unit 02).

    MongoDB       : system of record, the reference copy of each book
    Elasticsearch : inverted index of the same books -> full-text search with
                    relevance ranking ("dune herbert" finds "Dune" by Herbert)

The API talks to Elasticsearch through its REST API with `requests`, exactly
like the curl commands of the course (no extra client library):
    PUT    /books/_doc/{id}   index (or re-index) one book
    DELETE /books/_doc/{id}   remove it from the index
    POST   /books/_search     full-text query (multi_match)

Indexing runs in a FastAPI BackgroundTask: the client gets its 201 without
waiting for Elasticsearch. If Elasticsearch is down, MongoDB stays correct and
the search falls back to a MongoDB regex (degraded mode, logged as WARN).
"""
import logging

import requests

from . import config
from .logs import log_event

TIMEOUT = 3  # seconds


def enabled() -> bool:
    return bool(config.ES_URL)


def _request(method: str, path: str, **kwargs) -> requests.Response:
    return requests.request(
        method, f"{config.ES_URL}{path}", timeout=TIMEOUT,
        auth=(config.ES_USER, config.ES_PASSWORD),
        # verify the server certificate with the CA of the cluster (TLS on)
        verify=config.ES_CA_CERT or True, **kwargs)


def index_book(book_id: str, book: dict) -> None:
    """BackgroundTask: idempotent (PUT with the MongoDB id as document id)."""
    if not enabled():
        return
    try:
        _request("PUT", f"/{config.BOOKS_INDEX}/_doc/{book_id}", json=book).raise_for_status()
    except requests.RequestException as exc:
        log_event(logging.WARNING, "es_index_failed", book_id=book_id, error=str(exc))


def delete_book(book_id: str) -> None:
    if not enabled():
        return
    try:
        r = _request("DELETE", f"/{config.BOOKS_INDEX}/_doc/{book_id}")
        if r.status_code not in (200, 404):
            r.raise_for_status()
    except requests.RequestException as exc:
        log_event(logging.WARNING, "es_delete_failed", book_id=book_id, error=str(exc))


def search_books(q: str, size: int) -> list[dict] | None:
    """Returns [{id, score, ...book}] or None if Elasticsearch is unavailable."""
    if not enabled():
        return None
    query = {"size": size, "query": {"multi_match": {
        "query": q,
        "fields": ["title^3", "author^2", "tags"],   # ^3: a match in the title counts more
        "fuzziness": "AUTO",                           # tolerates typos: "dnue" -> "dune"
    }}}
    try:
        r = _request("POST", f"/{config.BOOKS_INDEX}/_search", json=query)
        r.raise_for_status()
    except requests.RequestException as exc:
        log_event(logging.WARNING, "es_search_failed", error=str(exc))
        return None
    return [{"id": hit["_id"], "score": round(hit["_score"], 3), **hit["_source"]}
            for hit in r.json()["hits"]["hits"]]
