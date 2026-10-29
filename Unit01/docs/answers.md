# Unit 01 – Réponses (DATOP2 U01 + DEVOP2 U01)

## 1. Qu'est-ce qu'une API REST ?

Une API REST expose des **ressources** (`/books`, `/logs`) identifiées par des URL. On les
manipule avec les **méthodes HTTP** et des représentations **JSON**. Elle est **sans état**
(*stateless*) : chaque requête contient tout ce qu'il faut pour la traiter, comme l'en-tête
`X-User-Id` ici.

| Méthode | Sens | Idempotente | Exemple ici |
|---|---|---|---|
| GET | lire | oui | `GET /books/{id}` → 200 / 404 |
| POST | créer | non | `POST /books` → 201 + `Location` |
| PUT | remplacer entièrement | oui | `PUT /books/{id}` → 200 |
| PATCH | modifier partiellement | en général oui | `PATCH /books/{id}` `{"year":1966}` |
| DELETE | supprimer | oui | `DELETE /books/{id}` → 204, sans corps |

Codes d'erreur utilisés :

| Code | Cas dans l'API |
|---|---|
| 404 | ressource inconnue, y compris un id mal formé (pas 500) |
| 409 | conflit : ISBN déjà utilisé |
| 422 | JSON valide mais contenu invalide (Pydantic) |
| 503 | dépendance indisponible (MongoDB) |

## 2. REST vs GraphQL

| | REST | GraphQL |
|---|---|---|
| URL | une par ressource | une seule (`/graphql`) |
| Méthode | GET, POST, PUT… | POST |
| Forme de la réponse | décidée par le serveur | décidée par le client (liste de champs) |
| Erreurs | code HTTP (404, 422…) | souvent 200, avec `errors` dans le corps |
| Cache HTTP | simple (GET) | plus difficile |

`client/graphql_client.py` demande seulement `name, capital, currency, languages`. Il n'y a ni
*over-fetching* ni *under-fetching*, mais il faut lire `errors` même quand la réponse est 200.

## 3. Logs et métadonnées

Un log est un **événement horodaté**. Ses métadonnées permettent de le retrouver et de le
corréler :

- `timestamp` en UTC, au format ISO 8601 ;
- `level` ;
- `service` ;
- `user_id` ;
- `action` ;
- un contexte : `method`, `path`, `status`, `duration_ms`, `order_id`…

Une ligne JSON par log, au format NDJSON, est lisible à la fois par un humain et par une
machine. Elle s'importe telle quelle dans MongoDB, et dans Elasticsearch en Unit 02.

Types de logs vus dans le cours :

| Type | Exemple dans cet exemple |
|---|---|
| système | démarrage de mongod |
| application | `book_created` |
| audit | qui a supprimé quel livre : `user_id` + `book_deleted` |
| activité | `login_success` dans le jeu de données |

## 4. SQL ↔ MongoDB

| SQL | MongoDB |
|---|---|
| database | database (`bookandride`) |
| table | collection (`books`, `logs`) |
| row | document |
| column | field |
| index | index (unique ISBN, `timestamp`, `level+timestamp`) |
| `SELECT … WHERE level='ERROR'` | `find({level: "ERROR"})` |
| `SELECT DISTINCT service` | `distinct("service", …)` |
| `GROUP BY` | `aggregate([{$group: …}])` |
| JOIN | *linking* ou *embedding* |

## 5. Les trois requêtes (NOW = 2025-09-18T10:00Z)

| Requête | Résultat |
|---|---|
| Q1 – ERROR dans les 24 dernières heures | **3** : orders-api ×1, payment-api ×2 |
| Q2 – actions de U12345 | `create_order_retry` → `transaction_failed` → `transaction_retry` → `logout` → `transaction_latency_high` |
| Q3 – services avec au moins un WARN | `auth-api`, `orders-api`, `payment-api` (+ `books-api` une fois l'API utilisée) |

## 6. Ce que les logs disent du système (interprétation)

- **Paiement fragile.** `payment-api` concentre les erreurs : 2 `transaction_failed` en
  24 h, sur deux utilisateurs différents. Elle montre aussi une latence élevée
  (p95 = 910 ms).
- **Le parcours de U12345 est typique d'un incident en cascade.** La commande ORD-1001 est
  d'abord retentée, puis le paiement échoue, est retenté, et la latence reste haute.
  Le problème vient du paiement et non de l'utilisateur.
- **`orders-api` échoue aussi** pour ORD-1002 (U22222). C'est peut-être la même dépendance
  qui est en cause.
- **Sécurité.** Une tentative de force brute est détectée sur `auth-api` (U88888,
  7 essais). Il faut bloquer l'adresse ou ajouter un rate limit, ce que fera la gateway en
  Unit 04 (429).
- **Priorité.** Il faut instrumenter `payment-api` : temps de réponse par fournisseur et
  taux d'erreur. Ce sont les métriques Prometheus de l'Unit 04.
