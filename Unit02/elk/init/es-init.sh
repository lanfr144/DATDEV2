#!/bin/bash
# =============================================================================
# Unit 02 - one-shot job run once Elasticsearch is healthy. Idempotent.
#   1. password of kibana_system (Kibana must NOT use the elastic superuser)
#   2. role + user for the API and the shipper (least privilege: write on
#      books and logs-* only, no cluster administration)
#   3. index template logs-* (explicit mapping) + index books
#   4. course Part A: _bulk load of logs-demo (16 documents, 3+ services, 3 levels)
# =============================================================================
set -euo pipefail
# curl of this image is too old for --fail-with-body: --fail = exit code 22 on HTTP >= 400
ES="https://elasticsearch:${ES_PORT}"
CURL=(curl -sS --fail --cacert config/certs/ca/ca.crt -u "elastic:${ELASTIC_PASSWORD}")
JSON=(-H 'Content-Type: application/json')     # NDJSON for _bulk: ONE Content-Type only

echo "1. kibana_system password"
"${CURL[@]}" "${JSON[@]}" -X POST "$ES/_security/user/kibana_system/_password" \
  -d "{\"password\":\"${KIBANA_PASSWORD}\"}" > /dev/null

echo "2. role bookandride_writer + user ${ES_APP_USER}"
"${CURL[@]}" "${JSON[@]}" -X PUT "$ES/_security/role/bookandride_writer" -d '{
  "indices": [{ "names": ["books", "logs-*"],
                "privileges": ["create_index", "index", "delete", "read", "view_index_metadata"] }]
}' > /dev/null
"${CURL[@]}" "${JSON[@]}" -X PUT "$ES/_security/user/${ES_APP_USER}" \
  -d "{\"password\":\"${ES_APP_PASSWORD}\",\"roles\":[\"bookandride_writer\"]}" > /dev/null

echo "3. index template bookandride-logs and index books"
# NOT named "logs": that name belongs to a built-in template of Elasticsearch 8
"${CURL[@]}" "${JSON[@]}" -X PUT "$ES/_index_template/bookandride-logs" \
  --data-binary @/init/logs-template.json > /dev/null
code=$(curl -s -o /dev/null -w '%{http_code}' --cacert config/certs/ca/ca.crt \
       -u "elastic:${ELASTIC_PASSWORD}" "$ES/books")
if [ "$code" = 404 ]; then
  "${CURL[@]}" "${JSON[@]}" -X PUT "$ES/books" --data-binary @/init/books-index.json > /dev/null
fi

echo "4. _bulk load of logs-demo (course Part A)"
"${CURL[@]}" -H 'Content-Type: application/x-ndjson' -X POST "$ES/logs-demo/_bulk?refresh=true" \
  --data-binary @/init/logs-demo.bulk.ndjson | grep -q '"errors":false'
"${CURL[@]}" "$ES/logs-demo/_count"; echo
echo "es-init done"
