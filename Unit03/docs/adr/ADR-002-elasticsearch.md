# ADR-002 – Elasticsearch au-dessus de MongoDB (recherche et logs)

- **Statut** : accepté (Unit 02)
- **Date** : 2026-10-28

## Contexte

Deux besoins ne sont pas couverts par MongoDB seul :

- **Recherche de livres.** Les utilisateurs tapent « dune herbert » ou « nueromancer », avec
  des fautes. Une regex MongoDB ne classe pas les résultats par pertinence et ne tolère pas
  les fautes.
- **Exploitation des logs.** Il faut des agrégations et des tableaux de bord en quasi temps
  réel, consultables par une personne non développeuse.

## Décision

- **MongoDB reste le système de référence** pour les livres et les logs.
- **Elasticsearch 8** (TLS + authentification) indexe une **copie** des données :
  - **les livres** : indexés par l'API dans une `BackgroundTask` (PUT idempotent sur l'id
    MongoDB) ;
  - **les logs** : copiés par un **shipper** qui lit les nouveaux documents MongoDB et les
    envoie en un `_bulk`, avec un checkpoint sur l'`_id`.
- **Kibana** fournit l'exploration et le dashboard, livré « as code » sous forme d'un
  ndjson importé.
- **Moindre privilège** :
  - `kibana_system` pour Kibana ;
  - `bookandride_app` pour l'API et le shipper (rôle limité à `books` et `logs-*`).

## Conséquences

Avantages :

- recherche plein texte, *fuzziness* et score de pertinence ;
- agrégations rapides ;
- dashboards.

Inconvénients :

- **Cohérence à terme.** L'index a environ 1 s de retard (refresh), et le shipper environ
  `SHIP_INTERVAL` secondes.
- **Coût.** Il faut environ 2 Go de RAM de plus, des certificats à gérer et trois jobs
  d'initialisation.
- **Si ES tombe** : la recherche se rabat sur MongoDB (mode dégradé, journalisé en WARN) et
  aucune donnée n'est perdue.

## Alternatives écartées

| Alternative | Raison |
|---|---|
| Index texte de MongoDB (`$text`) | pas de *fuzziness*, pas de Kibana |
| Logstash ou Beats comme collecteur | plus lourd pour un lab ; c'est le bon choix en production |
| Écrire les logs directement dans ES depuis l'API | couple l'API à ES et perd des logs si ES est indisponible |
