# Unit 04 – Réponses (DATOP2 U04 + DEVOP2 U04 + U05)

## 1. API Gateway (DATOP2 U04)

**Pourquoi une gateway ?**

- **Un seul point d'entrée.** Un seul port est publié, et il y a un seul endroit pour :
  - l'authentification ;
  - le rate limiting ;
  - les logs d'accès ;
  - TLS (en production).
- **Les services restent simples.**
  - `rentals` fait confiance à `X-User-Id` parce que **seule la gateway peut l'appeler** :
    aucun port n'est publié.
  - La gateway **écrase** la valeur envoyée par le client : le smoke test vérifie qu'un
    `X-User-Id: 2` envoyé avec la clé de l'utilisateur 1 donne bien `user_id = 1`.
- **Erreurs homogènes.** 401, 404, 429, 502 et 504 sont renvoyés en JSON, même quand
  c'est NGINX qui répond.

**Limites.**

- La gateway est un **point unique de défaillance** : en production, il en faut au moins
  deux, derrière un load balancer.
- Les clés API sont en clair dans la configuration NGINX. En production, on utiliserait
  des JWT ou OAuth2, et un *vault*.

## 2. Release Management – questions du lab (DEVOP2 U04b)

**Partie 1.**

- Un correctif après v2.0.0 donne **v2.0.1** (PATCH).
- Un nouvel endpoint qui ne modifie rien d'existant donne **v2.1.0** (MINOR).

**Partie 3.1 – blue/green.** Après le merge de `green` dans `main`, la production exécute
la version verte. Blue reste disponible pour revenir en arrière immédiatement.

Dans l'exemple :

```
blue/green switch: 100 % of /rentals -> green (1.1.0)
```

**Partie 3.2 – rolling.**

- **À vérifier entre deux lots :**
  - le healthcheck du nouveau serveur ;
  - le taux d'erreurs et la latence par version (Prometheus, label `version`) ;
  - les logs ERROR par version (MongoDB).
- **Si server1 renvoie des erreurs :** on **arrête** le déploiement (les lots suivants ne
  sont pas faits) et on remet server1 sur l'ancienne version. La commande
  `release.sh rolling` s'arrête si la version lue après un lot n'est pas la bonne.

**Partie 3.3 – canary.**

- **Métriques suivies :**
  - taux d'erreurs 5xx ;
  - latence p95 ;
  - retours utilisateurs ;
  - métrique métier (chiffre d'affaires par location).
- **Seuil d'arrêt :** taux d'erreurs du canary supérieur à **5 %**, ou plus de 2 fois celui
  de la version stable.
- Résultat de la démo : 2.0.0 atteint 20 à 40 % d’erreurs (tirage aléatoire, 30 % en moyenne), donc rollback. 2.0.1 reste à 0 %,
  donc promotion.

**Partie 4.** On utilise `git revert` et non `reset`, car l'historique partagé ne doit
jamais être réécrit. Le commit du canary reste visible, et son annulation est un nouveau
commit.

## 3. Debrief (U04b)

1. **Rollback le plus rapide : blue/green.** L'ancienne version tourne encore ; il suffit
   de rebasculer le trafic (`release.sh switch blue`, environ 10 s ici, moins d'une seconde
   avec un `reload`). Le canary est presque aussi rapide, et seuls 30 % des requêtes
   étaient touchées. Le rolling est le plus lent : il faut redéployer chaque lot.
2. **Si l'application ne supporte pas deux versions en même temps** pendant un rolling :
   - les clients voient alternativement deux contrats (`price_eur` puis `price_cents`) ;
   - les écritures d'une version peuvent être illisibles pour l'autre.

   Il faut alors du blue/green, avec une base compatible, ou une migration en deux temps
   (*expand/contract*).
3. **Le rollback du canary ne reçoit aucun nouveau tag.** On revient à une version déjà
   publiée (1.1.0). En revanche, le **correctif** est une nouvelle version : **2.0.1**.
   On ne re-tague jamais 2.0.0 (Unit 04a, immuabilité). 2.0.0 est marquée « retirée »
   dans les release notes.
4. **Ce que les release notes apportent de plus que l'historique Git :**
   - l'**impact pour l'utilisateur** (« `price_eur` est remplacé ») ;
   - les **ruptures de compatibilité** en évidence ;
   - les actions à faire (mettre à jour les clients) ;
   - le statut d'une version (« retirée »).

   L'historique dit *comment* le code a changé ; les notes disent *ce que cela change pour
   ceux qui l'utilisent*.

**Stratégie pour un service à 10 000 utilisateurs par jour.**

Je choisirais un **canary sticky par utilisateur** :

- 5 %, puis 25 %, puis 100 % ;
- piloté par des métriques par version (5xx, p95, CA par location) ;
- avec un seuil d'arrêt automatique.

L'environnement de blue/green reste prêt pour un rollback instantané. À ce volume,
5 % représentent environ 500 utilisateurs par jour : c'est assez pour détecter un défaut
en quelques heures, sans exposer tout le monde.

Pour une version MAJOR, il faut en plus :

- versionner l'API (`/v2/rentals`) ;
- garder `/v1` pendant une période de transition.

Ainsi, les anciens clients ne cassent pas, même pendant le canary.

## 4. Quiz Unit 05 (rollback)

1. **revert ou reset.**
   - `revert` ajoute un commit qui annule : l'historique est conservé, ce qui convient aux
     branches partagées.
   - `reset` déplace la branche : il réécrit l'historique et convient seulement en local.
2. **Pourquoi `reset --hard` est dangereux.** Il efface les modifications du répertoire de
   travail et de l'index, sans confirmation. Poussé avec `--force`, il casse le dépôt de
   tous ceux qui avaient récupéré les commits.
3. **Récupérer un commit après un `reset --hard`.** On utilise `git reflog`, on retrouve le
   hash, puis `git reset --hard <hash>`. Voir la démonstration dans
   [git_release_lab_output.txt](git_release_lab_output.txt).
4. **Restaurer un fichier suivi supprimé.** `git restore <fichier>`, ou
   `git checkout HEAD -- <fichier>`. Un fichier jamais commité ne peut pas être restauré
   par Git.
5. **Branche hotfix plutôt que reset.** Dès que la production ou une branche partagée est
   concernée : on corrige sur `hotfix/x.y.z`, on merge, on tague la PATCH. Personne ne
   perd son historique.
