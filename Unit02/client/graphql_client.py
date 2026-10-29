"""
Book&Ride - Unit 01 - GraphQL vs REST (DATOP2 Unit 01, course example2.py).

REST  : one URL per resource, the server decides the shape of the answer
        (GET /books/{id} always returns all the fields of a book).
GraphQL: ONE URL, always POST; the client sends a query that lists exactly
        the fields it wants -> no over-fetching, no under-fetching.

This script queries the public countries API (no key needed):
    python client/graphql_client.py LU
"""
import json
import sys

import requests

GRAPHQL_URL = "https://countries.trevorblades.com/"
QUERY = """
query Country($code: ID!) {
  country(code: $code) { name capital currency languages { name } }
}
"""


def main(code: str) -> None:
    # the query and its variables travel as JSON in the body of a POST
    payload = {"query": QUERY, "variables": {"code": code.upper()}}
    r = requests.post(GRAPHQL_URL, json=payload, timeout=10)
    r.raise_for_status()
    data = r.json()
    # GraphQL answers 200 even for an error: the errors are in the body
    if data.get("errors"):
        print("GraphQL error:", data["errors"][0]["message"])
    elif data["data"]["country"] is None:
        print(f"Unknown country code: {code}")
    else:
        print(json.dumps(data["data"]["country"], indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "LU")
