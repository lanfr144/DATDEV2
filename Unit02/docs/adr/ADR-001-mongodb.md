# ADR-001 – MongoDB pour les logs (et le catalogue en Unit 01)

- **Statut** : accepté (Unit 01). Le catalogue est remplacé par PostgreSQL en Unit 03 (ADR-003) ; les logs restent dans MongoDB.
- **Date** : 2026-10-28

## Contexte

L'API doit garder une trace de chaque requête : quoi, qui, quand, avec quel résultat.

Les logs n'ont pas tous les mêmes champs. Selon l'événement, on trouve par exemple :

- `order_id` ;
- `amount` ;
- `attempts` ;
- `p95_ms`.

Le volume augmente vite.

## Décision

- Les logs sont des **documents JSON** dans une collection MongoDB `logs`.
- Ils sont écrits par un `logging.Handler` Python. Ils sont aussi écrits sur stdout, une
  ligne JSON par log.
- Des index sont posés sur `timestamp`, sur `level + timestamp` et sur `user_id`, pour les
  trois requêtes du cours.

## Conséquences

Avantages :

- **Schéma flexible** : un champ en plus ne demande aucune migration.
- **JSON de bout en bout** : on passe de Pydantic au document, puis à la réponse, sans
  conversion.
- **Requêtes riches** : filtres, `distinct` et agrégations.

Inconvénients :

- Pas de recherche plein texte efficace ni de tableau de bord. L'Unit 02 ajoute
  Elasticsearch et Kibana.
- Écrire chaque log directement en base ajoute de la latence. En production, on
  écrirait sur stdout et un collecteur (Logstash, Beats, Fluent Bit) ferait le transport.

## Alternatives écartées

- **Fichier texte** : impossible à interroger sans le parser à nouveau.
- **Table SQL** : le schéma est fixe, et chaque nouveau champ demande un `ALTER TABLE`.
