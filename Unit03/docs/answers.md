# Unit 03 – Réponses (DATOP2 U03 + DEVOP2 U03)

## 1. Monolithe ou microservices ?

| | Monolithe (cette Unit) | Microservices (Unit 04) |
|---|---|---|
| Déploiement | 1 image, 1 conteneur | 1 image par service + une gateway |
| Base de données | 1 seule (jointures et transactions faciles) | 1 par service (pas de jointure entre services) |
| Appel entre modules | appel de fonction (ns) | appel HTTP (ms, peut échouer) |
| Montée en charge | tout ou rien | service par service |
| Équipe | idéal pour 1 petite équipe | plusieurs équipes autonomes |
| Exploitation | simple : 1 log, 1 healthcheck | complexe : logs à corréler, réseau, versions |

**Choix pour Book&Ride : monolithe modulaire d'abord** (ADR-003). Les modules `books` et
`rentals` sont déjà séparés (routers, modèles, règle `pricing.py` isolée) : on pourra les
extraire le jour où un besoin réel l'exige. C'est ce que fait l'Unit 04 avec `rentals`.

## 2. La règle de prix (plafond par jour)

| Durée | Calcul | Prix |
|---|---|---|
| 40 min | 40 × 0,25 | 10,00 € |
| 100 min | 25,00 plafonné | 12,00 € |
| 24 h | 1 jour complet | 12,00 € |
| 24 h + 1 min | 12 + 0,25 | 12,25 € |
| 2 jours + 2 h | 2 × 12 + min(30, 12) | 36,00 € |

## 3. Configuration (checklists du cours)

**Exercice 1 – config.yaml**
- [x] `config.yaml` contient les 3 environnements, sous `environments:`.
- [x] Les booléens sont en minuscules (`true` / `false`).
- [x] Le YAML est valide : 2 espaces d'indentation, chaînes entre guillemets.
- [x] Aucun secret dans le fichier : il est versionné.

**Exercice 2 – loader**
- [x] Sans `APP_ENV`, la configuration chargée est dev.
- [x] `APP_ENV=staging` et `APP_ENV=prod` chargent le bon bloc.
- [x] `DEBUG` est un booléen Python, même si la valeur arrive en `"false"` depuis
  l'environnement.
- [x] Un nom d'environnement inconnu lève `ValueError` ; une clé manquante donne une erreur
  au démarrage.

**Exercice 3 – trois exécutions** (voir [terminal_output_3_envs.txt](terminal_output_3_envs.txt))
- [x] Chaque environnement affiche un `DB_URL` différent.
- [x] Prod a `DEBUG = False` ; dev et staging ont `DEBUG = True`.
- [x] Les clés et les mots de passe sont masqués (`dev-... (masked)`, `user:****@host`).

**Le cours affiche le `DB_URL` complet, mot de passe compris.** Cela contredit sa propre
règle d'or n° 2 (« never print a full DB_URL or key »). Ici le mot de passe est remplacé
par `****`.

## 4. Pourquoi les secrets ne vont pas dans `config.yaml`

1. **Git n'oublie rien.** Un secret commité reste dans l'historique même après
   suppression. Il faut alors le changer partout (cf. DEVOP2 P01 : mot de passe publié dans
   `todo.sh`).
2. **Chaque environnement a ses propres secrets**, et chaque personne n'a accès qu'à ceux de
   son périmètre. Un développeur n'a pas besoin de la clé de prod.
3. **En production**, les secrets viennent d'un *vault* (HashiCorp Vault, AWS Secrets
   Manager) ou des secrets de la CI. Ils sont injectés en variables d'environnement, ce qui
   est exactement ce que lit `settings.py` (priorité 1).
