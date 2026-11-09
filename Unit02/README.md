# Unit 02 – FastAPI + Django REST, logs dans Elasticsearch et Kibana

**Consolidation** de DATOP2 Unit 02 (*Frameworks : FastAPI 02a/02b, Django 02c*) et
DEVOP2 Unit 02 (*Logs in practice : Elasticsearch + Kibana*).
Le Book&Ride de l'Unit 01 évolue de trois façons :

- l'API valide complètement ses données ;
- la même ressource existe aussi en **Django REST Framework**, pour comparer ;
- les logs suivent maintenant la chaîne ELK complète :
  **MongoDB (stockage) → shipper (`_bulk`) → Elasticsearch (index) → Kibana (dashboard)**.

```
 api (FastAPI :8201) ─┐ books + logs JSON  ┌──────────► mongo :27201 ◄── mongo-express :8281
 django (DRF  :8202) ─┘───────────────────►┘                │
        │ BackgroundTask : PUT /books/_doc/{id}             │ shipper : nouveaux logs → POST /_bulk
        ▼                                                   ▼
 elasticsearch :9221 (HTTPS + auth) ◄───────────────────────┘ ◄── kibana :5621 (dashboard)
   index books  (recherche plein texte, tolérance aux fautes)
   index logs-demo (dataset du cours)  +  logs-bookandride (logs réels des 2 API)
```

## Ce que l'exemple reprend

| Cours | Notion | Où |
|---|---|---|
| DATOP2 02a | paramètres de chemin et de requête, `/docs`, uvicorn | [routers/books.py](api/app/routers/books.py) |
| DATOP2 02b | POST + Pydantic `Field(...)`, `field_validator`, 422 détaillé | [schemas.py](api/app/schemas.py) |
| DATOP2 02b | `BackgroundTasks` (indexation ES après la réponse) | `create_book` dans books.py |
| DATOP2 02b | tests `TestClient` + `pytest.mark.parametrize` | [api/tests/](api/tests) (15 tests) |
| DATOP2 02c | Django : model, migration, `ModelSerializer`, `validate_<champ>` | [django-books/catalog/](django-books/catalog) |
| DATOP2 02c | `ModelViewSet` + router, `SearchFilter`, `OrderingFilter`, pagination | [views.py](django-books/catalog/views.py), [settings.py](django-books/booksite/settings.py) |
| DATOP2 02c | les autres écritures du lab : `@api_view` (`/hello/`, 405 sinon), vue générique `ListCreateAPIView` (`/v1/books/`), vue fonction PUT vs PATCH (`/v1/books/<id>/`) | fin de [views.py](django-books/catalog/views.py), tests `OtherViewStylesTests` |
| DEVOP2 U02 | Elasticsearch 8 avec TLS + authentification, réseau Docker, volume | [docker-compose.yml](docker-compose.yml) |
| DEVOP2 U02 | `kibana_system` (pas le superuser `elastic`), comptes à moindre privilège | [elk/init/es-init.sh](elk/init/es-init.sh) |
| DEVOP2 U02 | Kibana par **jeton de compte de service** (aucun mot de passe stocké) | [docker-compose.token.yml](docker-compose.token.yml), étape 5 de es-init.sh |
| DEVOP2 U02 | ingestion `_doc` (unitaire) et `_bulk` (NDJSON) | search.py, [shipper/ship_logs.py](shipper/ship_logs.py) |
| DEVOP2 U02 | recherche plein texte, filtre `level=ERROR`, agrégation par niveau, top 3 des services | [elk/queries/](elk/queries) |
| DEVOP2 U02 | export de l'index, data view, Lens, dashboard à 2 panneaux | [scripts/run_es_queries.sh](scripts/run_es_queries.sh), [elk/init/kibana-dashboard.ndjson](elk/init/kibana-dashboard.ndjson) |
| DEVOP2 U02 | comparaison MongoDB ↔ Elasticsearch | [docs/answers.md](docs/answers.md) |

## Démarrer

Prévoir environ 3 Go de RAM libre, et environ 2 minutes au premier démarrage.

```bash
cp .env.example .env                    # puis remplacer les valeurs PASSWORD_*
docker compose up -d --build --wait     # 7 services healthy + 3 jobs terminés (exit 0)
./scripts/smoke_test.sh                 # 13 vérifications de bout en bout
python client/rest_client.py            # tour complet (Unit 01 + validation, recherche, Django)
./scripts/run_es_queries.sh             # requêtes du cours → docs/es_outputs/*.json
./scripts/run_es_queries.sh 'logs-*'    # mêmes requêtes sur dataset du cours + logs réels
curl -s localhost:8202/hello/           # vue @api_view du lab Django (exercice 1)
```

Variante du cours (partie B, dernière étape) : Kibana s'authentifie avec un **jeton de
compte de service** au lieu du mot de passe de `kibana_system`.

```bash
docker compose down
docker compose -f docker-compose.yml -f docker-compose.token.yml up -d --build --wait
docker compose logs es-init | grep token          # "5. service-account token elastic/kibana/bookandride"
```

`es-init` crée le jeton `elastic/kibana/bookandride` (l'équivalent de
`elasticsearch-service-tokens create`, mais par l'API REST), l'écrit dans un volume partagé,
et Kibana le lit au démarrage dans `ELASTICSEARCH_SERVICEACCOUNTTOKEN`. Les variables
`ELASTICSEARCH_USERNAME`/`PASSWORD` sont vidées : Kibana refuse un jeton **et** un mot de passe.

| URL | Contenu |
|---|---|
| http://localhost:8201/docs | Swagger de l'API FastAPI |
| http://localhost:8202/ | API navigable de Django REST Framework |
| http://localhost:5621/app/dashboards#/view/bookandride-dashboard | dashboard Kibana (login `elastic` / `ELASTIC_PASSWORD`) |
| https://localhost:9221 | Elasticsearch (certificat auto-signé ; Elasticvue : Basic auth) |
| http://localhost:8281 | mongo-express |

Tests sans Docker :
```bash
cd api && pytest -q                         # 15 passed (mongomock, ES désactivé)
cd django-books && python manage.py test    # 6 tests OK (SQLite en mémoire)
```

## Healthchecks

| Service | Test | Défini dans |
|---|---|---|
| mongo, mongo-express | ping, `/status` | docker-compose.yml |
| elasticsearch | HTTPS répond « missing authentication credentials » (donc TLS et sécurité actifs) | docker-compose.yml |
| kibana | `/api/status` → `"level":"available"` | docker-compose.yml |
| api | `GET /health` | api/Dockerfile |
| django | `GET /health/` (`SELECT 1` sur SQLite) | django-books/Dockerfile |
| shipper | fichier *heartbeat* touché il y a moins de 30 s (la boucle tourne vraiment) | shipper/Dockerfile |
| setup, es-init, kibana-init | jobs ponctuels : `service_completed_successfully` | docker-compose.yml |

## Remarques

- **Le dataset du cours ne trouve pas « payment »** avec `match message: "payment"`, car les
  messages valent `transaction_failed`… Ici, le champ `message` est construit comme
  `"<service> <action> user=<id>"`. L'analyseur standard découpe `payment-api` en
  `payment` + `api`, et la requête du cours trouve alors 6 documents.
- **Mapping explicite** (template `bookandride-logs`). `level`, `service` et `user_id` sont en
  `keyword`, donc les agrégations utilisent `level` et non `level.keyword` comme dans le
  cours, où le mapping est dynamique.
  - Le template ne doit pas s'appeler `logs` : c'est le nom d'un template intégré d'ES 8.
    Découvert pendant les tests.
- **Le shipper est idempotent** : `_id` ES = `_id` MongoDB, et le checkpoint n'est sauvegardé
  qu'après confirmation d'ES. Un redémarrage ne perd ni ne duplique aucun log.
  - En production, ce rôle serait tenu par Logstash, Beats ou Elastic Agent, ou par le
    *connector* MongoDB d'Elastic présenté dans le cours.
- **`ELASTICSEARCH_SSL_VERIFICATIONMODE=certificate`** et non `none` : la CA générée par
  `setup` est montée partout. Python fait de même avec `verify=ES_CA_CERT`, sans `-k`.
- **422 (FastAPI) ou 400 (DRF)**, pour la même faute. Et le doublon d'ISBN donne 409 dans
  notre FastAPI mais 400 avec le `UniqueValidator` de DRF.
  [docs/answers.md](docs/answers.md) compare les deux frameworks.
- **Dégradation contrôlée** : sans `ES_URL`, ou si ES tombe, `/books/search` répond quand
  même, via une regex MongoDB (`"engine": "mongodb"`, sans score).
- **Le curl de l'image Elasticsearch 8.15** ne connaît pas `--fail-with-body` : les scripts
  utilisent `--fail`.
- `ES_JAVA_OPTS="-Xms1g -Xmx1g"` est **entre guillemets** dans `.env` : sinon `source .env`
  (utilisé par les scripts) casse sur l'espace. Docker Compose, lui, retire les guillemets.
- **Capture d'écran du dashboard** demandée par le cours : à faire à la main, sur l'URL
  Kibana ci-dessus.
