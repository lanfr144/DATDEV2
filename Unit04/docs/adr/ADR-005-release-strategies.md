# ADR-005 – Versions sémantiques et stratégies de release pilotées par la gateway

- **Statut** : accepté (Unit 04)
- **Date** : 2026-10-28

## Contexte

Il faut livrer souvent sans casser la production, et pouvoir revenir en arrière en quelques
secondes. Le cours (DEVOP2 U04) compare blue/green, rolling et canary. Il faut choisir et
outiller.

## Décision

1. **SemVer + immuabilité**
   - `APP_VERSION` est inscrite dans l'image au build (`datdev2/rentals:<version>`).
   - Un tag n'est **jamais** reconstruit avec un autre contenu : un correctif reçoit un
     nouveau numéro (2.0.0 défectueuse → 2.0.1).
   - `CHANGELOG.md` signale les ruptures de compatibilité.
2. **État de release déclaratif et versionné** (`release.env`)
   - Il contient les versions par slot, le mode, la couleur active et le pourcentage du
     canary.
   - Les scripts le modifient et sauvegardent l'état précédent.
   - Le commit dans Git fournit l'historique et le rollback (GitOps).
3. **Stratégie par type de changement**

   | Changement | Stratégie |
   |---|---|
   | PATCH | rolling (pas d'infrastructure en plus) |
   | MINOR | blue/green (validation sur le slot au repos, bascule et retour instantanés) |
   | MAJOR ou risqué | canary avec analyse automatique (5xx par version) et seuil de 5 % |

4. **Observabilité par version**
   - en-têtes `X-App-Version` / `X-App-Color` ;
   - label `version` dans Prometheus ;
   - champs `version` / `color` dans les logs MongoDB.
5. **Schéma compatible (*expand/contract*).** Une version ne supprime ni ne renomme une
   colonne utilisée par la version précédente. Ici, 2.0.0 change le contrat JSON, pas la
   base.

## Conséquences

Avantages :

- rollback en une commande ;
- défaut limité à une fraction du trafic ;
- décisions basées sur des mesures.

Inconvénients :

- deux slots à faire tourner (coût) ;
- discipline de compatibilité des schémas ;
- un canary par requête mélange les versions pour un même utilisateur. En production, il
  faut le rendre *sticky* par utilisateur.
