# Unit 01 – Les quatre styles d'API du cours, sur le même exemple

DATOP2 U01 présente REST, SOAP, GraphQL et gRPC. Cette Unit les montre tous les quatre.

| Style | Nature | Transport / format | Contrat | Fichier de l'exemple |
|---|---|---|---|---|
| **REST** | style d'architecture | HTTP/1.1, JSON | OpenAPI (`/docs`) | [api/app/routers/books.py](../api/app/routers/books.py), [client/rest_client.py](../client/rest_client.py) |
| **GraphQL** | langage de requête + runtime | HTTP POST, un seul endpoint, JSON | schéma typé | [client/graphql_client.py](../client/graphql_client.py) (API publique *countries*) |
| **SOAP** | protocole strict | XML (Envelope/Header/Body) sur HTTP, SMTP, TCP | WSDL | [client/soap_client.py](../client/soap_client.py) (service public *NumberConversion*) |
| **gRPC** | RPC | HTTP/2, Protocol Buffers (binaire) | fichier `.proto` | [grpc/](../grpc) (serveur sur les mêmes livres MongoDB) |

## REST

Une URL par ressource, les méthodes HTTP portent l'action, la réponse est du JSON lisible.
Sans état : toute l'information est dans la requête (`X-User-Id`). Facile à mettre en cache
et à déboguer avec `curl`.

## SOAP

```xml
<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
  <soap:Header/>                       <!-- authentification, WS-Security -->
  <soap:Body>
    <NumberToWords xmlns="http://www.dataaccess.com/webservicesserver/">
      <ubiNum>42</ubiNum>
    </NumberToWords>
  </soap:Body>
</soap:Envelope>
```

- Toutes les opérations passent par **une seule URL** ; le nom de l'opération est dans le corps.
- Le **WSDL** décrit les opérations et les types : client et serveur ne peuvent pas diverger.
- Les erreurs reviennent dans un élément standard `<soap:Fault>`.
- Avantages : typage fort, sécurité intégrée (WS-Security), transactions. Inconvénients :
  verbeux, plus lent, moins intuitif. Usage : banque, télécoms, grands systèmes.

## GraphQL

Un seul endpoint ; le client écrit la requête et ne reçoit **que** les champs demandés
(pas d'*over-fetching* ni d'*under-fetching*). Le cache HTTP est plus difficile, car chaque
requête est différente.

## gRPC

```bash
docker compose up -d --wait            # MongoDB + API REST
./scripts/grpc_demo.sh                 # serveur gRPC (profil "grpc") + client
```

- Le contrat [grpc/books.proto](../grpc/books.proto) définit `BookService` avec un appel
  **unaire** (`GetBook`, l'équivalent de `GET /books/{id}`) et un appel en **streaming
  serveur** (`ListBooks`, sans équivalent en REST).
- Le code client et serveur est **généré** par `grpc_tools.protoc` dans le Dockerfile.
- Les messages sont binaires : un livre fait quelques dizaines d'octets au lieu d'un JSON
  lisible, mais `curl` ne suffit plus pour les lire.
- Les erreurs sont des **codes de statut gRPC** : `NOT_FOUND` (≈ 404), `INVALID_ARGUMENT`
  (≈ 400/422), `UNAVAILABLE` (≈ 503).
- Usage typique : appels nombreux entre microservices ; peu adapté au navigateur.

## Réponses aux questions du lab (exercice 3)

1. **gRPC vs REST** : gRPC appelle des *méthodes* d'un service (RPC) sur HTTP/2 avec des
   messages binaires ; REST manipule des *ressources* avec les méthodes HTTP et du JSON.
2. **Pourquoi Protocol Buffers ?** Plus compact et plus rapide à (dé)sérialiser que du JSON,
   typé par le contrat, et le code est généré pour chaque langage.
3. **Où gRPC est utile** : communication entre microservices, streaming, applications
   mobiles à faible bande passante, systèmes polyglottes.
4. **Vrai ou faux** : gRPC repose sur HTTP/2 → **vrai** ; les messages gRPC sont lisibles
   comme du JSON → **faux** ; gRPC est courant dans les microservices → **vrai**.
