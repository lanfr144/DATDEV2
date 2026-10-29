"""
Book&Ride - Unit 02 - REST client (same tour as Unit 01 + validation, search, Django).

Walks through the whole API and prints, for each call, the HTTP method,
the URL, the status code and the JSON body:
    1. json.dumps / json.loads  (Python dict <-> JSON text)
    2. POST, GET, PATCH, PUT, DELETE on /books   (201, 200, 204)
    3. the errors: 404, 409, 422
    4. POST /logs: sends the course dataset (logs.ndjson) line by line
    5. GET /logs/stats: the three MongoDB queries of DEVOP2 Unit 01
    6. Unit 02: 422 details, query parameters, /books/search (Elasticsearch)
    7. Unit 02: the same resource on the Django REST Framework service

Usage (the stack must be running: docker compose up -d --wait):
    pip install requests
    python client/rest_client.py              # URL built from API_HOST_PORT in .env
    API_URL=http://localhost:8101 python client/rest_client.py
"""
import json
import os
from pathlib import Path

import requests

UNIT_DIR = Path(__file__).resolve().parents[1]
TIMEOUT = 5  # seconds: never wait forever for a server


def read_env(name: str, default: str) -> str:
    """Tiny .env reader (python-dotenv would do the same, see Unit 03)."""
    env_file = UNIT_DIR / ".env"
    if name in os.environ:
        return os.environ[name]
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            if line.startswith(f"{name}="):
                return line.split("=", 1)[1].strip()
    return default


API = os.getenv("API_URL", f"http://localhost:{read_env('API_HOST_PORT', '8201')}")
DJANGO = os.getenv("DJANGO_URL", f"http://localhost:{read_env('DJANGO_HOST_PORT', '8202')}")
HEADERS = {"X-User-Id": "U-client"}   # appears as user_id in the JSON logs


def show(response: requests.Response) -> None:
    body = response.json() if response.content else "(no body)"
    print(f"{response.request.method:6} {response.request.path_url:40} -> {response.status_code}")
    if isinstance(body, (dict, list)):
        print("       " + json.dumps(body, ensure_ascii=False)[:150])


def main() -> None:
    print("== 1. JSON <-> Python ==")
    book = {"title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "978-0441013593",
            "price": 9.99, "tags": ["Sci-Fi", "classic"]}
    text = json.dumps(book)           # dict -> str (what travels on the network)
    print("json.dumps ->", text)
    print("json.loads -> year + 1 =", json.loads(text)["year"] + 1)

    print(f"\n== 2. CRUD on {API}/books ==")
    s = requests.Session()
    s.headers.update(HEADERS)
    r = s.post(f"{API}/books", json=book, timeout=TIMEOUT)
    if r.status_code == 409:          # already created by a previous run: start again
        old = [b for b in s.get(f"{API}/books", timeout=TIMEOUT).json() if b["isbn"] == book["isbn"]]
        s.delete(f"{API}/books/{old[0]['id']}", timeout=TIMEOUT)
        r = s.post(f"{API}/books", json=book, timeout=TIMEOUT)
    show(r)
    print("       Location:", r.headers.get("Location"))
    url = API + r.headers["Location"]
    show(s.get(url, timeout=TIMEOUT))
    show(s.patch(url, json={"year": 1966}, timeout=TIMEOUT))
    show(s.put(url, json={**book, "title": "Dune (Ace edition)"}, timeout=TIMEOUT))
    show(s.get(f"{API}/books", params={"author": "Frank Herbert"}, timeout=TIMEOUT))

    print("\n== 3. Errors ==")
    show(s.post(f"{API}/books", json={**book, "title": "Copy"}, timeout=TIMEOUT))  # 409 same ISBN
    show(s.post(f"{API}/books", json={"title": "No author"}, timeout=TIMEOUT))      # 422
    show(s.delete(url, timeout=TIMEOUT))                                           # 204
    show(s.get(url, timeout=TIMEOUT))                                              # 404

    print("\n== 4. Send the course logs (NDJSON) ==")
    lines = (UNIT_DIR / "mongo" / "logs.ndjson").read_text().splitlines()
    codes = [s.post(f"{API}/logs", json=json.loads(line), timeout=TIMEOUT).status_code
             for line in lines if line.strip()]
    print(f"POST /logs x{len(codes)} -> {sorted(set(codes))}")

    print("\n== 5. The three queries (NOW = 2025-09-18T10:00:00Z) ==")
    stats = s.get(f"{API}/logs/stats", params={"now": "2025-09-18T10:00:00Z"}, timeout=TIMEOUT).json()
    print(json.dumps(stats, indent=2))

    print("\n== 6. Unit 02: validation, query parameters, search ==")
    r = s.post(f"{API}/books", json={**book, "isbn": "123", "price": 0, "year": 2999}, timeout=TIMEOUT)
    print(f"POST invalid book -> {r.status_code}")
    for err in r.json()["detail"]:                       # one entry per invalid field
        print(f"       {'.'.join(map(str, err['loc']))}: {err['msg']}")
    for extra in [{"title": "Neuromancer", "author": "William Gibson", "year": 1984,
                   "isbn": "978-0441569595", "price": 8.5, "tags": ["cyberpunk"]},
                  {"title": "Foundation", "author": "Isaac Asimov", "year": 1951,
                   "isbn": "978-0553293357", "price": 7.99, "tags": ["sci-fi"]},
                  book]:
        s.post(f"{API}/books", json=extra, timeout=TIMEOUT)    # 409 if already there: fine
    show(s.get(f"{API}/books", params={"tag": "sci-fi", "sort": "-year"}, timeout=TIMEOUT))
    import time
    time.sleep(1.5)            # Elasticsearch refreshes its index every second
    r = s.get(f"{API}/books/search", params={"q": "nueromancer gibson"}, timeout=TIMEOUT)
    print(f"GET /books/search?q=nueromancer gibson (typo on purpose) -> {r.status_code}, "
          f"engine={r.json()['engine']}, first hit={r.json()['hits'][0]['title'] if r.json()['hits'] else None}")

    print(f"\n== 7. Unit 02: same resource with Django REST Framework ({DJANGO}) ==")
    r = s.post(f"{DJANGO}/books/", json={**book, "isbn": "979-1234567896"}, timeout=TIMEOUT)
    print(f"POST /books/ -> {r.status_code} (400 on 2nd run: ISBN already exists)")
    r = s.post(f"{DJANGO}/books/", json={**book, "year": 2999, "isbn": "1"}, timeout=TIMEOUT)
    print(f"POST invalid -> {r.status_code} (DRF answers 400, FastAPI 422) {r.json()}")
    show(s.get(f"{DJANGO}/books/", params={"search": "dune", "ordering": "-year"}, timeout=TIMEOUT))


if __name__ == "__main__":
    try:
        main()
    except requests.ConnectionError:
        print(f"API unreachable on {API}: is the stack running? (docker compose up -d --wait)")
