# Unit 04 – API Gateway + microservices + stratégies de release

**Consolidation** de DATOP2 Unit 04 (*API Gateway*, *HTTP cheat sheet 04bis*) et DEVOP2
Unit 04 (*Release Management : semver, blue/green, rolling, canary*), avec en bonus
DEVOP2 Unit 05 (*Rollback*).

Le module `rentals` du monolithe de l'Unit 03 devient un **microservice** derrière une
**gateway NGINX**. Cette gateway sert aussi d'**aiguillage du trafic** pour les releases :
les stratégies du cours ne sont plus simulées avec des dossiers, elles sont appliquées à du
vrai trafic HTTP.

```
client ──:8401──► gateway NGINX ──/books (lecture libre, écriture : clé) ──► books ──► books-db
                    │ X-API-Key → X-User-Id                                    │
                    │ rate limit 10 r/s → 429 + Retry-After                    │ logs JSON
                    │ erreurs 401/404/429/502/504 en JSON                      ▼
                    └─/rentals (clé) ──► $rentals_pool ─┬─► rentals-blue  (v a.b.c) ─┐   logs (MongoDB)
                       bluegreen : 100 % ACTIVE_COLOR   └─► rentals-green (v x.y.z) ─┴─► rentals-db
                       canary    : N % CANARY_COLOR                 ▲ /metrics (label version)
                       rolling   : les deux                   prometheus :9491
release.env (versionné) = versions par slot + mode + couleur active + % canary
scripts/release.sh      = deploy | switch | canary | promote | rolling | rollback | status
```

## Ce que l'exemple reprend

| Cours | Notion | Où |
|---|---|---|
| DATOP2 U04 | point d'entrée unique, services non publiés | [docker-compose.yml](docker-compose.yml) |
| DATOP2 U04 | `X-API-Key` → `X-User-Id` (remplace la valeur envoyée par le client), 401 | [gateway/templates/default.conf.template](gateway/templates/default.conf.template) |
| DATOP2 U04 | rate limit + 429 `Retry-After`, 502/504 JSON, 404 JSON | idem |
| DATOP2 U04 | *database per service*, extraction de `rentals` | [rentals-service/](rentals-service), ADR-004 |
| DATOP2 U04 | métriques Prometheus, ici avec un label `version` | [rentals-service/app/main.py](rentals-service/app/main.py) |
| DATOP2 04bis | 201 + `Location`, 404 si la location appartient à un autre user, 409 | idem |
| DEVOP2 U04a | versions sémantiques, immuabilité (tag image = version, 2.0.0 jamais re-taguée) | [rentals-service/app/release.py](rentals-service/app/release.py), [release/CHANGELOG.md](release/CHANGELOG.md) |
| DEVOP2 U04b P1-2 | tags v1.0.0 / v1.1.0 / v2.0.0, release notes | [release/git_release_lab.sh](release/git_release_lab.sh) → [docs/git_release_lab_output.txt](docs/git_release_lab_output.txt) |
| DEVOP2 U04b P3 | **blue/green**, **canary**, **rolling**, sur du vrai trafic | [scripts/release.sh](scripts/release.sh), [scripts/release_demo.sh](scripts/release_demo.sh) |
| DEVOP2 U04b P3.3 | métriques du canary et seuil d'arrêt (5 %) | [scripts/canary_analysis.sh](scripts/canary_analysis.sh) |
| DEVOP2 U04b P4 | rollback : bascule de couleur, `release.sh rollback`, `git revert` | release.sh, git_release_lab.sh |
| DEVOP2 U05 | `restore`, `reset --soft/--mixed/--hard`, `reflog`, branche hotfix | git_release_lab.sh |
| Units 01-03 | logs JSON → MongoDB, config par environnement (books = bloc `prod`) | [books-service/](books-service) |

## Démarrer

```bash
cp .env.example .env                       # puis remplacer les PASSWORD_*
./scripts/compose.sh up -d --build --wait  # 8 services healthy
./scripts/smoke_test.sh                    # 15 vérifications gateway + observabilité
./scripts/release.sh status                # blue 1.0.0 actif, green 1.0.0 au repos
./scripts/release_demo.sh                  # scénario complet → docs/release_demo_output.txt
./release/git_release_lab.sh               # lab Git U04b + U05 dans un dépôt jetable
```

`compose.sh` est un raccourci pour `docker compose --env-file .env --env-file release.env …`.

Tests sans Docker :
```bash
cd books-service   && pytest -q     # 11 passed (configuration + CRUD)
cd rentals-service && pytest -q     # 17 passed (prix, versions, injection de panne, métriques)
```

## Le scénario de release ([docs/release_demo_output.txt](docs/release_demo_output.txt))

| Étape | Version | Stratégie | Résultat |
|---|---|---|---|
| 1 | **1.1.0** MINOR (champ `price_detail` ajouté) | blue/green : déployée sur green au repos, testée par `/internal/green/...`, bascule | rollback instantané vers blue (1.0.0), puis re-bascule |
| 2 | **2.0.0** MAJOR (`price_eur` → `price_cents`), défaut simulé à 30 % | canary 30 % | 20 à 40 % d’erreurs (tirage aléatoire, 30 % en moyenne) sur 2.0.0, au-dessus du seuil de 5 % → **rollback** |
| 3 | **2.0.1** PATCH (le correctif ; 2.0.0 n'est pas re-taguée) | canary 30 % → 0 % d'erreurs → `promote` | 100 % sur 2.0.1 |
| 4 | **2.0.2** PATCH | rolling : blue, vérification, puis green | les deux slots en 2.0.2, sans coupure |

Ce que le client voit change avec la version :

| Version | Champs de prix renvoyés |
|---|---|
| 1.0.0 | `price_eur` |
| 1.1.0 | `price_eur` + `price_detail` |
| 2.x | `price_cents` + `price_detail` |

## Healthchecks

| Service | Test | Défini dans |
|---|---|---|
| gateway | `wget /health` (renvoie aussi l'état de release) | docker-compose.yml |
| books | `GET /health` (PostgreSQL) | books-service/Dockerfile |
| rentals-blue, rentals-green | `GET /rentals/health` (PostgreSQL) | rentals-service/Dockerfile |
| books-db, rentals-db | `pg_isready` | docker-compose.yml |
| logs | `mongosh --host $(hostname) … ping` | docker-compose.yml |
| prometheus | `/-/healthy` | docker-compose.yml |

La gateway attend que `books`, `rentals-blue` et `rentals-green` soient *healthy*.
`release.sh switch` refuse aussi d'envoyer du trafic vers un slot qui ne répond pas.

## Remarques

- **Bug trouvé pendant les tests : la résolution DNS de NGINX.** Par défaut, NGINX résout
  `rentals-green` **une seule fois**, au démarrage.
  - Après la recréation d'un conteneur, qui prend une nouvelle IP, la gateway envoyait le
    trafic « green » à l'ancienne adresse, désormais occupée par blue.
  - Correctif : `resolver 127.0.0.11 valid=5s` + `server … resolve` + `zone`, disponibles
    dans NGINX open source depuis la 1.27.3. L'image est épinglée en `nginx:1.27.5-alpine`.
- **NGINX refuse `0%`** dans `split_clients`. `CANARY_PERCENT` vaut donc de 1 à 99, et le
  script le vérifie.
- **Durée d'une bascule.** La gateway est recréée (`envsubst` au démarrage), ce qui prend
  environ 10 s avec l'attente du healthcheck. Un `nginx -s reload` sur une configuration
  régénérée ferait la même chose en moins d'une seconde, sans couper les connexions.
  `rollback` dure environ 45 s, car il recrée les deux slots, mais **sans reconstruire
  d'image** : les tags existent déjà.
- **Une seule base pour blue et green.** C'est indispensable pour basculer sans perdre de
  locations, mais le schéma doit être compatible entre deux versions (*expand/contract*).
  C'est pourquoi la 2.0.0 change le **contrat JSON** et pas la **colonne** : la base stocke
  toujours des euros.
- **Canary par requête (`$request_id`).** C'est pratique pour la démo avec 2 utilisateurs.
  En production, on découperait par utilisateur (`$api_user`), pour qu'un client voie
  toujours la même version ; c'est crucial avec un changement MAJOR comme la 2.0.0.
- **GitOps.** `release.env` est **versionné** : committer chaque changement fait de
  l'historique Git l'historique des déploiements, et `git revert` devient un rollback
  (U04b partie 4).
- **Les fonctionnalités par version** (`release.py`) simulent des tags Git dans un seul
  code. Dans un vrai projet, chaque image est construite par la CI à partir du tag
  correspondant.
- Réponses aux questions du lab et quiz U05 : [docs/answers.md](docs/answers.md).
  Architecture : [ADR-004](docs/adr/ADR-004-gateway-microservice.md),
  [ADR-005](docs/adr/ADR-005-release-strategies.md).
