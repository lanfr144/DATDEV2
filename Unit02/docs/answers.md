# Unit 02 – Réponses (DATOP2 U02 + DEVOP2 U02)

## 1. FastAPI ou Django REST Framework : la même ressource `/books`

| | FastAPI ([api/](../api)) | Django REST Framework ([django-books/](../django-books)) |
|---|---|---|
| Style | micro-framework, on assemble soi-même | « batteries incluses » : ORM, admin, migrations, auth |
| Contrat / validation | Pydantic (`BookIn`, `Field`, `field_validator`) | `ModelSerializer` + validateurs du modèle + `validate_year` |
| Erreur de validation | **422** + `loc` / `msg` / `type` | **400** + `{"champ": ["message"]}` |
| ISBN en double | **409** (code explicite) | 400 (`UniqueValidator` automatique) |
| CRUD | un handler par route | `ModelViewSet` + `DefaultRouter` : 5 actions en une classe |
| Filtres | `Query(...)` typés, validés (422 si `limit=0`) | `SearchFilter`, `OrderingFilter`, pagination déclarés dans settings |
| Base de données | MongoDB (pymongo) | SQLite (ORM + migration `0001_initial`) |
| Documentation | OpenAPI/Swagger automatique (`/docs`) | API navigable de DRF (`/`) |
| Asynchrone | natif (ASGI), `BackgroundTasks` | WSGI (gunicorn) ; Celery pour les tâches de fond |
| Tests | `TestClient` + pytest | `APITestCase` (`manage.py test`) |

**Conclusion.** FastAPI convient à un micro-service d'API typé et rapide. Django convient
quand on veut un back-office complet (admin, utilisateurs, ORM) sans tout réécrire. Les deux
journalisent dans le **même** format et vers la même chaîne de logs : le choix du framework
ne change rien côté exploitation.

### 404 ou 422 sur `/books/{id}` ?

- `GET /books/not-an-id` → **422** : la forme de l'identifiant est invalide. `Path(pattern=…)`
  rejette la requête avant le handler.
- `GET /books/0123456789abcdef01234567` → **404** : l'identifiant est valide mais la
  ressource n'existe pas.

En Unit 01, les deux renvoyaient 404. Les deux choix se défendent ; l'important est d'être
cohérent et de le documenter.

## 2. Requêtes Elasticsearch (Partie A) – sorties dans [es_outputs/](es_outputs)

| Requête | `logs-demo` (16 docs du cours) | `logs-*` (+ logs réels des API) |
|---|---|---|
| (a) plein texte `message: payment` | 6 | 10 |
| (b) filtre `level = ERROR` | 4 | 7 |
| (c) agrégation par niveau | INFO 7 · WARN 5 · ERROR 4 | INFO 36 · WARN 13 · ERROR 7 |
| (d) top 3 des services (requête personnelle) | payment-api 6 · auth-api 4 · orders-api 3 | books-api en tête |
| (e) ERROR sur 24 h, par service | payment-api 2 · orders-api 1 | ×2 |

Dans `logs-*`, le dataset du cours apparaît deux fois : une fois dans `logs-demo`, chargé par
`_bulk`, et une fois dans `logs-bookandride`, venu de MongoDB par le shipper. Les comptages
de (e) doublent donc. Pour éviter cela, il faut une seule source par donnée.

Les chiffres de `logs-*` dépendent du nombre de requêtes déjà faites sur les API.

## 3. Unit 01 ↔ Unit 02 : MongoDB ou Elasticsearch ? (4 à 6 phrases)

MongoDB reste le **système de référence**. Il stocke chaque document de façon fiable, avec
des mises à jour, des index uniques (ISBN) et des requêtes exactes ou par intervalle,
comme les 3 requêtes de l'Unit 01.

Elasticsearch est plus simple pour **chercher et agréger**. Son index inversé trouve
« nueromancer gibson » malgré la faute de frappe, et classe les résultats par pertinence.
Une agrégation `terms` remplace un `$group`. Kibana en fait un tableau de bord sans écrire de
code.

En revanche, Elasticsearch n'est pas une base transactionnelle : l'index est rafraîchi chaque
seconde (*near real-time*), il n'y a ni contrainte d'unicité ni transaction, et il consomme
beaucoup de mémoire (1 Go de heap minimum ici).

D'où l'architecture retenue : **écrire dans MongoDB, indexer dans Elasticsearch**. Si ES
tombe, aucune donnée n'est perdue : la recherche se dégrade vers MongoDB, et le shipper
rattrape son retard au redémarrage.

## 4. Sécurité de la stack ELK (checklist du cours)

- [x] Aucun mot de passe ni jeton dans `docker-compose.yml` ou dans ce document : tout est
  dans `.env`, ignoré par Git. `.env.example` contient des valeurs factices `PASSWORD_*`.
- [x] Kibana se connecte en `kibana_system`. L'API et le shipper utilisent `bookandride_app`
  (rôle `bookandride_writer` : `books` et `logs-*` seulement). Le superuser `elastic` sert
  uniquement à l'administration.
- [x] `ELASTICSEARCH_SSL_VERIFICATIONMODE=certificate`. `none` n'est acceptable qu'en lab
  local, parce qu'il désactive la protection contre l'interception (*man-in-the-middle*).
- [x] Ports 9221 et 5621 publiés sur `127.0.0.1` seulement, pas sur le réseau.
