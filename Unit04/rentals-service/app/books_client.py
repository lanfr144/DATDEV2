"""
Synchronous call to the books service (DATOP2 Unit 03, slide "In code: the same
call, two architectures").

In the Unit 03 monolith, rentals read a book with a FUNCTION call (~1 µs, cannot
fail because of the network). Now books is ANOTHER PROCESS: the same question
is an HTTP call, slower (ms) and it CAN fail -> the "fallacies of distributed
computing": the network is not reliable, latency is not zero.

So every call has:
    - a timeout          never wait forever for a slow service (BOOKS_TIMEOUT)
    - an error decision  books down or too slow -> 503 Service Unavailable,
                         book unknown -> 404 (the answer of books, passed on)
The call goes service to service on the private Docker network (http://books:8080),
NOT through the gateway: no API key needed, books stays unpublished.
"""
import os

import httpx


class BooksUnavailable(Exception):
    """books did not answer in time, or answered with a 5xx."""


def books_url() -> str:
    # read at call time: tests (and a new config) can change it without a restart
    return os.getenv("BOOKS_URL", "http://books:8080").rstrip("/")


def get_book(book_id: int) -> dict | None:
    """The book as JSON, None if books says 404, BooksUnavailable otherwise."""
    timeout = float(os.getenv("BOOKS_TIMEOUT", "2.0"))
    try:
        r = httpx.get(f"{books_url()}/books/{book_id}", timeout=timeout)
    except httpx.HTTPError as exc:            # connection refused, DNS error, timeout...
        raise BooksUnavailable(repr(exc)) from exc
    if r.status_code == 404:
        return None
    if r.status_code >= 500:
        raise BooksUnavailable(f"books answered {r.status_code}")
    r.raise_for_status()
    return r.json()
