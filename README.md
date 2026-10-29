# DATDEV2 – Consolidation DATOP2 + DEVOP2 (Units 01 à 04)

Un **seul fil rouge, Book&Ride**, qui grandit d'Unit en Unit. Chaque Unit réunit la
partie *développement d'API* de **DATOP2** et la partie *exploitation* de **DEVOP2** qui
lui correspond, comme sur le schéma « Architecture DATOP2 DEVOP2 » du cours. Chaque dossier
`UnitXX` est **autonome** : il se lance seul, avec ses propres `.env`, ports, volumes et
tests.

| Unit | DATOP2 (API) | DEVOP2 (Ops) | L'exemple consolidé |
|---|---|---|---|
| [Unit01](Unit01/README.md) | API Basics : HTTP, REST vs GraphQL, JSON | Logs et métadonnées, MongoDB en Docker | API REST `/books` (FastAPI) dont **chaque requête produit un log JSON dans MongoDB** ; les 3 requêtes du cours via `mongosh` et `GET /logs/stats` |
| [Unit02](Unit02/README.md) | FastAPI (validation, tests, BackgroundTasks) + Django REST | Elasticsearch 8 (TLS) + Kibana | Même ressource en **FastAPI et en Django** ; logs **MongoDB → shipper `_bulk` → Elasticsearch → dashboard Kibana** ; recherche plein texte des livres |
| [Unit03](Unit03/README.md) | Monolithe modulaire (books + rentals, PostgreSQL, plafond de 12 €/jour) | Configuration dev/staging/prod (`config.yaml`, loader, secrets) | **Même image, 3 environnements** lancés en parallèle ; configuration validée par Pydantic ; prod sans `/docs`, avec des logs minimaux |
| [Unit04](Unit04/README.md) | API Gateway NGINX, microservice `rentals`, Prometheus | Release management : semver, blue/green, rolling, canary (+ U05 rollback) | La **gateway sert d'aiguillage des releases** ; scénario réel 1.1.0 → 2.0.0 (canary raté, rollback) → 2.0.1 → 2.0.2 (rolling) ; lab Git (tags, revert, reflog, hotfix) |

## Comment le fil rouge évolue

```
U01  client ─► api ─► MongoDB (books + logs)
U02  client ─► api | django ─► MongoDB ─► shipper ─► Elasticsearch ─► Kibana
U03  client ─► monolithe (books + rentals) ─► PostgreSQL        ×3 env (dev/staging/prod)
                           └─ logs JSON (+env, +version) ─► MongoDB
U04  client ─► gateway ─► books ─► PostgreSQL
                       └► rentals-blue / rentals-green ─► PostgreSQL     (+ Prometheus, MongoDB)
```

Décisions d'architecture, cumulées d'une Unit à l'autre dans `docs/adr/` :

| ADR | Décision | Unit |
|---|---|---|
| ADR-001 | MongoDB pour les logs | U01 |
| ADR-002 | Elasticsearch au-dessus de MongoDB | U02 |
| ADR-003 | Monolithe sur PostgreSQL + configuration par environnement | U03 |
| ADR-004 | Gateway + microservice `rentals` | U04 |
| ADR-005 | Stratégies de release | U04 |

## Démarrage rapide (toutes les Units)

Prérequis : Docker Desktop (Compose v2), Python 3.12, et environ 3 Go de RAM libre pour
l'Unit 02 (Elasticsearch).

```bash
cd Unit01 && cp .env.example .env && docker compose up -d --build --wait && ./scripts/smoke_test.sh
cd Unit02 && cp .env.example .env && docker compose up -d --build --wait && ./scripts/smoke_test.sh
cd Unit03 && ./scripts/up.sh dev && ./scripts/up.sh staging && ./scripts/up.sh prod && ./scripts/smoke_test.sh
cd Unit04 && cp .env.example .env && ./scripts/compose.sh up -d --build --wait && ./scripts/smoke_test.sh
```

Les fichiers `.env` sont déjà présents, avec des mots de passe aléatoires générés le
2026-10-28. Les `cp` ne servent que pour un clone neuf. En Unit 03, il faut aussi copier
`.env.<env>.example` vers `.env.<env>`.

Les ports ne se chevauchent pas : les 4 Units peuvent tourner en même temps.

| Unit | API / gateway | Autres ports publiés (tous sur 127.0.0.1) |
|---|---|---|
| 01 | 8101 | mongo-express 8181, MongoDB 27101 |
| 02 | 8201 (FastAPI), 8202 (Django) | mongo-express 8281, MongoDB 27201, Elasticsearch 9221, Kibana 5621 |
| 03 | 8301 dev, 8302 staging, 8303 prod | MongoDB 27301 / 27302 / 27303 |
| 04 | 8401 (gateway) | Prometheus 9491, MongoDB 27401 |

## Résultats des tests (2026-10-28)

| Unit | Tests unitaires (sans Docker) | Smoke test de bout en bout (Docker) |
|---|---|---|
| 01 | 6 passed (mongomock) | 9/9 OK, 3 conteneurs healthy |
| 02 | FastAPI 15 passed · Django 4 OK | 13/13 OK, 7 conteneurs healthy + 3 jobs terminés (exit 0) |
| 03 | 25 passed (monolithe + configuration) | 20/20 OK sur les 3 environnements |
| 04 | books 11 passed · rentals 17 passed | 15/15 OK, 8 conteneurs healthy ; scénario de release complet |

## Conventions communes

- **Secrets.** Tous les secrets sont dans `.env` (ou `.env.<env>`), ignorés par Git.
  - `.env.example` en est une copie où chaque mot de passe vaut `PASSWORD_<NOM>`.
  - Le `.gitignore` de chaque Unit accepte `!.env.example` et `!.env.*.example`.
- **Configuration.** Aucun port ni mot de passe n'est écrit en dur dans le code ou dans
  compose. Tout est en `${VARIABLE}`, et les ports sont publiés sur `127.0.0.1`.
- **Healthchecks partout.**
  - Les images construites ici l'ont dans leur **Dockerfile** (`HEALTHCHECK`).
  - Les images officielles l'ont dans compose : `mongosh ping`, `pg_isready`, Elasticsearch
    en HTTPS, `/api/status` pour Kibana, `/-/healthy` pour Prometheus, `/health` pour la
    gateway.
  - `docker compose up --wait` rend la main quand tout est *healthy*.
- **Un seul format de log JSON** dans toutes les Units : `timestamp`, `level`, `service`,
  `user_id`, `action` + contexte. On ajoute `env` en U03, puis `version` et `color` en U04.
- **Conteneurs non root** (`USER app`). Les codes HTTP suivent le cheat sheet 04bis :
  201 + `Location`, 204, 401, 404, 409, 422, 429 + `Retry-After`, 502/504 en JSON.

## Remarques et observations sur les cours

1. **DEVOP2 U01, `mongoimport`.** L'outil garde `timestamp` comme **chaîne de caractères** :
   une requête `$gte: ISODate(...)` ne trouve alors rien. Le script de seed convertit en
   vraies dates. De même, `NOW` doit être fixé à 2025-09-18T10:00Z, car le jeu de données
   date de 2025.
2. **DEVOP2 U02, `match message: "payment"`.** Cette requête du cours ne trouve rien dans
   le jeu de données du cours (les messages valent `transaction_failed`…). Ici, `message`
   inclut le service.
   - Le template d'index ne doit pas s'appeler `logs`, nom réservé par Elasticsearch 8.
   - Le `curl` de l'image ES 8.15 ne connaît pas `--fail-with-body`.
3. **DEVOP2 U03.** La sortie attendue par le cours affiche le `DB_URL` **avec le mot de
   passe**, ce qui contredit sa propre règle « never print a full DB_URL ». L'exemple le
   masque.
4. **DEVOP2 U04b.** La simulation par dossiers et branches est reprise telle quelle dans
   `git_release_lab.sh`. L'Unit 04 montre en plus ces stratégies **sur du vrai trafic**,
   ce qui fait apparaître deux pièges réels :
   - NGINX résout les noms DNS une seule fois (correctif : `resolve`) ;
   - `split_clients` refuse `0%`.
5. **Healthcheck MongoDB.** Un test sur `127.0.0.1` passe « healthy » trop tôt, pendant le
   mongod temporaire de l'init. Il faut tester via `--host $(hostname)`.
6. **Hors périmètre.**
   - DEVOP2 Units 06-12 (packaging, déploiement, SSH/TLS).
   - L'authentification bcrypt/JWT de GESTEL (DATOP2 U01) : remplacée ici par des clés
     API à la gateway.
   - Grafana.
   - Une CI qui construirait les images depuis les tags Git (les étapes sont décrites dans
     ADR-005).

## Arrêter et nettoyer

```bash
cd Unit01 && docker compose down        # -v efface aussi les volumes (données)
cd Unit02 && docker compose down
cd Unit03 && for e in dev staging prod; do ./scripts/down.sh $e; done
cd Unit04 && ./scripts/compose.sh down
```
