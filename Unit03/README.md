# Unit 03 – Monolithe modulaire + configuration dev / staging / prod

**Consolidation** de DATOP2 Unit 03 (*Monolith vs Microservices*) et DEVOP2 Unit 03
(*Application Configuration*). Book&Ride devient une **application unique** (modules
`books` et `rentals`) avec **une base PostgreSQL**. La **même image** tourne dans
**trois environnements** : seuls `APP_ENV` et les secrets changent.

```
                 config/config.yaml (versionné, sans secret)
                 dev │ staging │ prod  ──► choisi par APP_ENV
                         │
 .env.<env> (secrets) ──►├──► app/settings.py : YAML + config.local.yaml + variables d'env
                         │                      → Settings (Pydantic) : types, clés requises, règles prod
                         ▼
 ┌──── projet datdev2-unit03-<env> ─────────────────────────────────────────────┐
 │ api  (image datdev2/bookandride:1.0.0)                                        │
 │   /books   (lecture publique, écriture : X-API-Key de l'environnement)        │
 │   /rentals (start/stop, prix : 0,25 €/min, plafond 12 €/jour)                 │
 │      │ SQLAlchemy                          │ logs JSON (+ env, version)       │
 │      ▼                                     ▼                                  │
 │ <env>-db : PostgreSQL 16              <env>-logs : MongoDB 7                  │
 └───────────────────────────────────────────────────────────────────────────────┘
   dev :8301      staging :8302      prod :8303   (les 3 peuvent tourner en même temps)
```

## Ce que l'exemple reprend

| Cours | Notion | Où |
|---|---|---|
| DATOP2 U03 | monolithe modulaire : 1 app, 2 routers, 1 BD, 1 conteneur | [api/app/main.py](api/app/main.py), [routers/](api/app/routers) |
| DATOP2 U03 | SQLAlchemy 2 + PostgreSQL 16, `create_all`, `pool_pre_ping` | [db.py](api/app/db.py), [models.py](api/app/models.py) |
| DATOP2 U03 | règle métier isolée et testée : 0,25 €/min, plafond 12 €/jour (stretch goal) | [pricing.py](api/app/pricing.py) |
| DATOP2 U03 | 201 + `Location`, 409 (vélo déjà loué, ISBN), `/rentals/me` avant `/{id}` | [routers/rentals.py](api/app/routers/rentals.py) |
| DATOP2 U03 | ADR « pourquoi un monolithe d'abord » | [docs/adr/ADR-003-monolith-postgresql.md](docs/adr/ADR-003-monolith-postgresql.md) |
| DEVOP2 U03 ex. 1 | `config.yaml` à 3 environnements, YAML valide | [api/config/config.yaml](api/config/config.yaml) |
| DEVOP2 U03 ex. 2 | `load_config()` : `APP_ENV`, dev par défaut, `ValueError`, clés requises | [api/app/settings.py](api/app/settings.py) |
| DEVOP2 U03 ex. 3 | 3 exécutions avec secrets masqués (livrable) | [scripts/run_3_envs.sh](scripts/run_3_envs.sh) → [docs/terminal_output_3_envs.txt](docs/terminal_output_3_envs.txt) |
| DEVOP2 U03 ext. | schéma Pydantic, `config.local.yaml`, log de l'environnement chargé | settings.py, [config.local.yaml.example](api/config/config.local.yaml.example) |
| DEVOP2 U03 | secrets hors Git : `.env.<env>` ignorés, `.env.<env>.example` versionnés | [.gitignore](.gitignore) |
| Units 01-02 | logs JSON → MongoDB, avec en plus `env` et `version` | [logs.py](api/app/logs.py) |

## Démarrer

```bash
cp .env.example .env
for e in dev staging prod; do cp .env.$e.example .env.$e; done   # puis remplacer les PASSWORD_*
./scripts/up.sh dev            # (staging, prod) : docker compose --env-file .env --env-file .env.dev …
./scripts/smoke_test.sh        # 20 vérifications sur les 3 environnements (les 3 doivent tourner)
./scripts/run_3_envs.sh        # livrable de l'exercice 3
./scripts/down.sh prod         # arrêter un environnement (-v : effacer ses données)
```

Sans Docker :
```bash
cd api && pip install -r requirements.txt && pytest -q     # 25 passed (SQLite, sans MongoDB)
cp config/config.local.yaml.example config/config.local.yaml
DB_PASSWORD=x API_KEY=dev-12345678 python -m app.settings  # affiche la config dev masquée
```

## Ce qui change selon l'environnement (même code, même image)

| | dev | staging | prod |
|---|---|---|---|
| `DEBUG` | true | true | **false** (refus de démarrer si `true`) |
| `/docs`, `/redoc`, `/config` | oui | oui | **404** |
| `LOG_LEVEL` | DEBUG | INFO | WARNING (les 2xx ne sont pas journalisés) |
| BD / logs | `dev-db/dev_db`, `logs_dev` | `staging-db/staging_db`, `logs_staging` | `prod-db/prod_db`, `logs_prod` |
| `API_KEY` | `dev-…` | `staging-…` | clé propre (une clé `dev-…` est refusée) |
| Port publié | 8301 | 8302 | 8303 |

## Healthchecks

| Service | Test | Défini dans |
|---|---|---|
| db | `pg_isready -U <env>_user -d <env>_db` | docker-compose.yml |
| logs | `mongosh --host $(hostname) … ping` | docker-compose.yml |
| api | `GET /health` (`SELECT 1` sur PostgreSQL, 503 sinon) | api/Dockerfile |

## Remarques

- **Ordre de priorité des sources de configuration** (de la plus forte à la plus faible) :
  1. variables d'environnement ;
  2. `config.local.yaml` ;
  3. `config.yaml`.

  C'est la règle 12-factor : Docker, la CI ou un vault peuvent tout surcharger sans
  modifier de fichier.
- **Convention de nommage partagée** entre `config.yaml` et compose : `<env>-db`,
  `<env>_user`, `<env>_db`. Les alias réseau Docker donnent ces noms aux conteneurs. Les
  valeurs du YAML fonctionnent donc telles quelles, et seuls les secrets viennent de
  `.env.<env>`.
- **Fail fast.** Une configuration invalide (clé manquante, mauvais type, `DEBUG=true` en
  prod) empêche l'application de démarrer. Le message liste les champs fautifs **sans
  afficher leur valeur**, pour ne pas faire fuiter un secret dans les logs.
- **Les paramètres de prix** (`PRICE_PER_MINUTE`, `DAILY_CAP`) sont dans la configuration :
  staging peut tester un autre tarif sans nouvelle release. Ils sont identiques dans les
  3 environnements ici.
- **Le modèle a changé** :
  - Le livre perd ses `tags` en passant au relationnel. Une liste demanderait une table de
    liaison, ce qui montre la différence entre document et SQL.
  - Il gagne `stock` (DATOP2 U03).
- **Clé API.** L'API vérifie elle-même `X-API-Key` (comparaison `hmac.compare_digest`).
  En Unit 04, ce contrôle part dans la gateway.
- Réponses aux questions : [docs/answers.md](docs/answers.md).
