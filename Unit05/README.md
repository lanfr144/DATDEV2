# Unit 05 – Paquet Python, SSH, HTTPS et SFTP

**Consolidation** de DEVOP2 Unit 07 (*Structure of a Python Package*) et des fiches
DEVOP2 Unit 11 (*Arbeitsblätter 19 à 23* : OpenSSH, OpenSSL, Apache en HTTPS, redirection
HTTP → HTTPS, SFTP). Les fiches se font dans une VM Linux ; ici, les mêmes commandes sont
écrites dans des Dockerfiles, donc reproductibles en une commande.

```
pricing-package/   bookandride-pricing 1.0.0 : la règle de prix de Book&Ride en paquet (wheel)
web   :8580 ──301──► https://localhost:8543  site "test"      (Apache, certificat auto-signé)
      :8590          site "temporary" en HTTP                 (fiche 21, port 90)
ssh   :2251          OpenSSH + SFTP, utilisateur student, clé uniquement
```

## Ce que l'exemple reprend

| Cours | Notion | Où |
|---|---|---|
| U07 | dossier `src/`, `__init__.py` = API publique, tests hors du paquet | [pricing-package/](pricing-package) |
| U07 | `pyproject.toml` (remplace `setup.py`), dépendances `dev`, commande installée | [pyproject.toml](pricing-package/pyproject.toml) |
| U07 | `pip install -e ".[dev]"`, wheel testée **après installation** | [pricing-package/Dockerfile](pricing-package/Dockerfile), CI |
| U11 fiche 19 | `apt install openssh-server`, `sshd_config` durci, `ssh user@hôte`, empreinte de l'hôte | [ssh/](ssh) |
| U11 fiche 20 | `openssl genpkey` → CSR (`req -new`) → certificat X.509 auto-signé | [scripts/make_keys.sh](scripts/make_keys.sh) |
| U11 fiche 21 | site test sur 80, site temporary sur 90, puis HTTPS sur 443 | [web/bookride.conf](web/bookride.conf) |
| U11 fiche 22 | `a2enmod rewrite`, `RewriteCond %{HTTPS} !=on`, `RewriteRule … [R,L]` | idem |
| U11 fiche 23 | SFTP avec une **paire de clés SSH** (pas de mot de passe) | [scripts/smoke_test.sh](scripts/smoke_test.sh) |

## Démarrer

```bash
cp .env.example .env
./scripts/make_keys.sh                  # clé SSH de student + certificat d'Apache (une fois)
docker compose up -d --build --wait
./scripts/smoke_test.sh                 # HTTPS, redirection, SSH par clé, SFTP
./scripts/package_check.sh              # construit la wheel et teste le paquet installé
```

Sans Docker, pour le paquet :
```bash
cd pricing-package
python -m pip install -e ".[dev]"       # installation « éditable » + pytest
pytest -q                               # 7 passed
bookandride-price 1500                  # 12.25 : commande créée par [project.scripts]
```

Se connecter soi-même :
```bash
curl -i http://localhost:8580/                                 # 301 -> https://localhost:8543/
curl --cacert certs/web.crt https://localhost:8543/            # page "Test"
cp keys/student_ed25519 ~/.ssh/bookride && chmod 600 ~/.ssh/bookride
ssh -p 2251 -i ~/.ssh/bookride student@127.0.0.1               # 1re fois : empreinte à accepter
sftp -P 2251 -i ~/.ssh/bookride student@127.0.0.1              # put / get / ls dans upload/
```

## Explications

**Pourquoi `src/` ?** Sans lui, `import bookandride_pricing` dans les tests trouverait le
dossier local au lieu du paquet installé : un fichier oublié dans le paquet passerait
inaperçu. Le Dockerfile et la CI vont plus loin : ils construisent la **wheel**, l'installent
dans une image propre, puis lancent les tests contre elle. On teste ce qui serait publié.

**Version du paquet.** `version = "1.0.0"` dans `pyproject.toml` est lue au runtime par
`importlib.metadata` (`__version__`). Comme une image Docker taguée (Unit 04), une wheel
publiée est **immuable** : un correctif devient 1.0.1.

**Certificat (fiche 20).** Trois étapes : clé privée (`genpkey`), demande de signature
(CSR), puis certificat signé **par sa propre clé** (auto-signé). Le chiffrement est réel, mais
aucune autorité ne garantit l'identité : le navigateur avertit et `curl` exige `--cacert`.
Le `subjectAltName` (localhost, 127.0.0.1) est obligatoire pour les navigateurs modernes.

**Redirection (fiche 22).** Le port 80 ne sert plus de contenu : il répond `301` vers
`https://`. La fiche utilise `[R,L]` (302, temporaire) ; ici `R=301` (définitif). L'en-tête
**HSTS** demande en plus au navigateur d'aller directement en HTTPS la fois suivante.

**SSH durci (fiches 19 et 23).** `PasswordAuthentication no`, `PermitRootLogin no`,
`AllowUsers student`, `MaxAuthTries 3`. Le serveur n'annonce que `publickey` : impossible
de deviner un mot de passe. Les **clés d'hôte** sont créées au premier démarrage (jamais
dans l'image) et gardées dans un volume : l'empreinte acceptée par le client ne change pas
d'un redémarrage à l'autre. SFTP passe par la même connexion SSH chiffrée (port 22).

**Secrets.** `keys/` (clé privée SSH) et `certs/` (clé privée TLS) sont ignorés par Git ;
seules les parties publiques seraient partagées.
