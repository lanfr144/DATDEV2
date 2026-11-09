# Jalon DevOps : Docker (2013)

*Livrable A de DEVOP2 Unit 01 : un jalon de l'histoire DevOps, environ 330 mots.*

## Vue d'ensemble

Docker est présenté en mars 2013 par Solomon Hykes, chez dotCloud, à la conférence PyCon.
Il ne crée pas les conteneurs : les *namespaces* et les *cgroups* du noyau Linux existaient
déjà. Il les rend **simples** : un fichier texte, le `Dockerfile`, décrit une image ; une
commande la construit (`docker build`) et une autre la lance (`docker run`). Les images se
partagent sur un registre public, Docker Hub.

## Impact

Avant Docker, une application dépendait de la machine qui l'hébergeait : version de Python,
bibliothèques, configuration. Le célèbre « ça marche sur ma machine » bloquait le passage
du développement à la production. L'image Docker emporte l'application **et** ses
dépendances : la même image tourne sur le portable du développeur, dans la CI et en
production.

Docker a ainsi rendu possibles plusieurs pratiques DevOps :

- **intégration et déploiement continus** : la CI construit une image testée, versionnée par
  un tag, puis la déploie telle quelle ;
- **microservices** : chaque service est une image indépendante, démarrée en quelques
  secondes ;
- **infrastructure décrite en code** : Docker Compose décrit tout un système dans un fichier
  YAML versionné ;
- **orchestration** : Kubernetes (2014) gère des milliers de conteneurs sur un cluster.

## Exemple réel

Ce projet Book&Ride en est la preuve : chaque Unit se lance avec une seule commande,
`docker compose up -d --wait`. En Unit 03, la **même image** tourne en dev, staging et prod ;
seule la variable `APP_ENV` change. En Unit 04, une version égale un tag d'image
(`datdev2/rentals:2.0.1`) : un rollback consiste à relancer une image déjà construite, sans
recompiler.

## Limites

Un conteneur partage le noyau de l'hôte : il isole moins qu'une machine virtuelle. Il faut
donc des images à jour, un utilisateur non root (`USER app` dans nos Dockerfiles) et aucun
secret dans l'image.

## Sources

- Solomon Hykes, *The future of Linux Containers*, PyCon 2013.
- Documentation officielle : <https://docs.docker.com/get-started/docker-overview/>
