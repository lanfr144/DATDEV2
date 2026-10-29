"""
Book&Ride - Unit 01 - REST client (DATOP2 Unit 01: HTTP + JSON with requests).

Walks through the whole API and prints, for each call, the HTTP method,
the URL, the status code and the JSON body:
    1. json.dumps / json.loads  (Python dict <-> JSON text)
    2. POST, GET, PATCH, PUT, DELETE on /books   (201, 200, 204)
    3. the errors: 404, 409, 422
    4. POST /logs: sends the course dataset (logs.ndjson) line by line
    5. GET /logs/stats: the three MongoDB queries of DEVOP2 Unit 01

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


API = os.getenv("API_URL", f"http://localhost:{read_env('API_HOST_PORT', '8101')}")
HEADERS = {"X-User-Id": "U-client"}   # appears as user_id in the JSON logs


def show(response: requests.Response) -> None:
    body = response.json() if response.content else "(no body)"
    print(f"{response.request.method:6} {response.request.path_url:40} -> {response.status_code}")
    if isinstance(body, (dict, list)):
        print("       " + json.dumps(body, ensure_ascii=False)[:150])


def main() -> None:
    print("== 1. JSON <-> Python ==")
    book = {"title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "978-0441013593"}
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


if __name__ == "__main__":
    try:
        main()
    except requests.ConnectionError:
        print(f"API unreachable on {API}: is the stack running? (docker compose up -d --wait)")
