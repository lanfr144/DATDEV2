# Unit 01 – API REST + logs JSON dans MongoDB

**Consolidation** de DATOP2 Unit 01 (*API Basics*) et DEVOP2 Unit 01 (*DevOps, logs & MongoDB*).
Première version du fil rouge **Book&Ride** : un catalogue de livres en REST
dont chaque requête produit un **log JSON** stocké dans **MongoDB**.

```
client (requests, json.dumps)          ┌──────────── docker compose ─────────────┐
  │  POST/GET/PUT/PATCH/DELETE /books  │  api (FastAPI) ──► mongo:7 ◄── mongo-express
  │  POST /logs  GET /logs/stats  ───► │   │ books + logs        volume mongo_data   │
  ▼                                    │   └─► stdout : 1 log JSON par ligne         │
réponse JSON + code HTTP               └─────────────────────────────────────────────┘
```

## Ce que l'exemple reprend

| Cours | Notion | Où |
|---|---|---|
| DATOP2 U01 | méthodes HTTP GET/POST/PUT/PATCH/DELETE | [api/app/routers/books.py](api/app/routers/books.py) |
| DATOP2 U01 | codes 200, 201 + `Location`, 204, 404, 409, 422, 503 | idem + [main.py](api/app/main.py) |
| DATOP2 U01 | JSON : `json.dumps` / `json.loads`, `requests` avec timeout | [client/rest_client.py](client/rest_client.py) |
| DATOP2 U01 | REST vs GraphQL (exemple du cours, API pays) | [client/graphql_client.py](client/graphql_client.py) |
| DATOP2 U01 | documentation automatique (`/docs`), Pydantic | [schemas.py](api/app/schemas.py) |
| DEVOP2 U01 | log JSON + métadonnées (timestamp, level, service, user_id, action) | [api/app/logs.py](api/app/logs.py) |
| DEVOP2 U01 | handler Python `logging` → MongoDB | `MongoHandler` dans logs.py |
| DEVOP2 U01 | MongoDB en Docker, volume persistant, mongo-express | [docker-compose.yml](docker-compose.yml) |
| DEVOP2 U01 | chargement de `logs.ndjson` avec de vraies dates | [mongo/init/01-seed-logs.js](mongo/init/01-seed-logs.js) |
| DEVOP2 U01 | les 3 requêtes (ERROR 24 h, actions d'un user, services en WARN) | [mongo/queries.js](mongo/queries.js) et `GET /logs/stats` |
| DEVOP2 U01 | SQL ↔ MongoDB (table/collection, row/document) | commentaires de queries.js, [docs/answers.md](docs/answers.md) |

## Démarrer

```bash
cp .env.example .env                    # puis remplacer les valeurs PASSWORD_*
docker compose up -d --build --wait     # rend la main quand les 3 services sont healthy
./scripts/smoke_test.sh                 # 9 vérifications de bout en bout
python client/rest_client.py            # tour complet de l'API (pip install requests)
./scripts/run_queries.sh                # les 3 requêtes du cours dans mongosh
python client/graphql_client.py LU      # GraphQL (Internet requis)
```

| URL (ports de `.env`) | Contenu |
|---|---|
| http://localhost:8101/docs | Swagger UI de l'API |
| http://localhost:8181 | mongo-express (login `EXPRESS_USER` / `EXPRESS_PASSWORD`) |
| `mongodb://admin:…@localhost:27101` | MongoDB pour Compass ou mongosh |

Tests unitaires sans Docker (MongoDB simulé par **mongomock**) :
```bash
cd api && pip install -r requirements.txt && pytest -q     # 6 passed
```

## Healthchecks

| Service | Test | Défini dans |
|---|---|---|
| mongo | `mongosh --host $(hostname) … ping` | docker-compose.yml |
| mongo-express | `wget http://127.0.0.1:${EXPRESS_PORT}/status` | docker-compose.yml |
| api | `GET /health` (ping MongoDB, 503 sinon) | api/Dockerfile |

## Remarques

- **Piège corrigé pendant les tests.** Au premier démarrage, l'image `mongo` lance un mongod
  temporaire (localhost seulement) pour les scripts d'init, puis le redémarre.
  - Un healthcheck sur `127.0.0.1` était donc « healthy » trop tôt : l'API se connectait
    pendant le redémarrage et l'index unique ISBN n'était pas créé, si bien que le doublon
    renvoyait 201 au lieu de 409.
  - Correctifs :
    - le healthcheck passe par l'adresse réseau du conteneur (`--host $(hostname)`) ;
    - l'API recrée les index au premier `/health` réussi.
- **`POST /logs` est idempotent.** Il fait un upsert sur (timestamp, service, user_id, action),
  comme le script de seed. Renvoyer le jeu de données répond 200, pas 201, et ne double pas
  les comptages.
- **`Q3` contient aussi `books-api`.** Les 404 et 409 de l'API sont journalisés en `WARN`,
  donc l'API apparaît elle-même dans ses propres logs. C'est voulu : c'est le principe
  de l'observabilité.
- **Pourquoi `NOW` est fixé.** `NOW = 2025-09-18T10:00Z` est imposé par l'exercice, car le
  jeu de données date de septembre 2025. `GET /logs/stats` sans `?now=` utilise l'heure
  réelle.
- **Livres dans MongoDB.** Les livres sont dans MongoDB, et pas en MySQL comme GESTEL
  (DATOP2 U01), pour rester sur une seule base dans cette Unit. Le passage à une base
  relationnelle est fait en Unit 03 (ADR-003). L'authentification bcrypt/JWT de GESTEL n'est
  pas reprise : l'identité arrive par `X-User-Id` (ici libre ; vérifiée par la gateway en
  Unit 04).
- Réponses aux questions du cours : [docs/answers.md](docs/answers.md). Choix d'architecture :
  [docs/adr/ADR-001-mongodb.md](docs/adr/ADR-001-mongodb.md).
