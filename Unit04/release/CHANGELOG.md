# Release Notes – Book&Ride rentals service

Les versions les plus récentes sont en haut.

Format : [Keep a Changelog](https://keepachangelog.com/) + [Semantic Versioning](https://semver.org/) :

| Partie | Quand elle augmente |
|---|---|
| MAJOR | changement incompatible |
| MINOR | ajout compatible |
| PATCH | correctif |

Une version publiée n'est **jamais modifiée**. Une erreur se corrige par une nouvelle
version.

## v2.0.2 – 2026-10-28 (PATCH)

- Correctif livré par **rolling update** : les deux slots sont mis à jour l'un après
  l'autre, sans interruption.

## v2.0.1 – 2026-10-28 (PATCH)

- **Corrige** les erreurs 500 intermittentes de `POST /rentals/stop` introduites en 2.0.0.
- Validée par un **canary à 30 %** (0 % d'erreurs), puis promue à 100 %.

## v2.0.0 – 2026-10-28 (MAJOR – breaking) – RETIRÉE

- **ATTENTION, rupture de compatibilité** :
  - `price_eur` (float, en euros) est **remplacé** par `price_cents` (entier, en centimes),
    dans `POST /rentals/stop` et `GET /rentals[/{id}]` ;
  - les clients qui lisent `price_eur` doivent être mis à jour.
- Base de données inchangée : elle stocke toujours des euros. 1.x et 2.x peuvent donc
  tourner en même temps (blue/green, canary).
- **Retirée** après le canary : 20 à 40 % d’erreurs (tirage aléatoire, 30 % en moyenne), au-dessus du seuil de 5 %. Rollback vers
  1.1.0.
- Le tag `v2.0.0` **n'est pas déplacé** : le correctif s'appelle 2.0.1.

## v1.1.0 – 2026-10-28 (MINOR)

- **Ajout** du champ `price_detail` dans `POST /rentals/stop` : jours complets, minutes
  restantes, plafond appliqué ou non.
- Compatible : les anciens clients ignorent ce champ.
- Déployée en **blue/green**, avec un test de rollback (retour instantané sur blue en 1.0.0).

## v1.0.0 – 2026-10-28

- Première version du service `rentals`, extrait du monolithe de l'Unit 03 :
  - sa propre base de données ;
  - derrière la gateway ;
  - `X-User-Id` fourni par la gateway.
- Tarif : 0,25 €/minute commencée, plafonné à 12 € **par jour**.
