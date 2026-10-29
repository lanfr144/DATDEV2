# ADR-003 – Monolithe modulaire sur PostgreSQL, configuré par environnement

- **Statut** : accepté (Unit 03). Partiellement remplacé par ADR-004 en Unit 04 (extraction de `rentals`).
- **Date** : 2026-10-28

## Contexte

Book&Ride ajoute la location de vélos, avec démarrage, arrêt, calcul du prix et vélo
indisponible pendant une location. Ces données sont **transactionnelles** : deux personnes
ne doivent pas pouvoir louer le même vélo.

L'équipe est petite, et l'application doit tourner en dev, en staging et en prod.

## Décisions

1. **Monolithe modulaire**
   - Une application FastAPI avec deux routers (`books`, `rentals`).
   - Une image Docker et une base de données.
   - La règle de prix est isolée dans `pricing.py`.
2. **PostgreSQL pour les données métier** (livres, locations) :
   - schéma fixe ;
   - `UNIQUE(isbn)` ;
   - transactions ;
   - types numériques exacts (`NUMERIC(7,2)`).

   MongoDB est **conservé pour les logs** (ADR-001), là où le schéma flexible est utile.
3. **Configuration externalisée (12-factor)**
   - `APP_ENV` choisit un bloc de `config.yaml` (versionné, sans secret).
   - Les secrets arrivent par l'environnement.
   - L'ensemble est validé par Pydantic **au démarrage** (*fail fast*), avec des règles
     propres à la prod.
4. **Une image pour les trois environnements** (*build once, deploy many*), et un projet
   Compose par environnement (réseaux, volumes et ports séparés).

## Conséquences

Avantages :

- Déploiement simple.
- Les transactions et les jointures restent possibles.
- Staging se comporte comme la prod, à `DEBUG` près.
- Impossible de lancer la prod avec `DEBUG=true` ou une clé de dev.

Inconvénients :

- Tout se déploie ensemble : une erreur dans `rentals` redémarre aussi `books`.
- Deux bases (PostgreSQL et MongoDB) à exploiter.

**Signal pour découper** : `rentals` doit évoluer ou monter en charge indépendamment.
C'est ce qui se passe en Unit 04.
