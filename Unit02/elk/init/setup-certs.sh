#!/bin/bash
# =============================================================================
# Unit 02 - one-shot job: TLS certificates of the cluster (Elasticsearch 8.x)
# Runs once (the files stay in the `certs` volume), then exits with code 0.
# =============================================================================
set -euo pipefail
cd /usr/share/elasticsearch
if [ ! -f config/certs/ca/ca.crt ]; then
  echo "creating the certificate authority (CA)"
  bin/elasticsearch-certutil ca --silent --pem -out config/certs/ca.zip
  unzip -qo config/certs/ca.zip -d config/certs
fi
if [ ! -f config/certs/elasticsearch/elasticsearch.crt ]; then
  echo "creating the certificate of the node (DNS: elasticsearch, localhost)"
  printf 'instances:\n  - name: elasticsearch\n    dns: [elasticsearch, localhost]\n    ip: [127.0.0.1]\n' \
    > config/certs/instances.yml
  bin/elasticsearch-certutil cert --silent --pem -out config/certs/certs.zip \
    --in config/certs/instances.yml --ca-cert config/certs/ca/ca.crt --ca-key config/certs/ca/ca.key
  unzip -qo config/certs/certs.zip -d config/certs
fi
# uid 1000 = elasticsearch, kibana and the "app" user of our Python images
chown -R 1000:0 config/certs
find config/certs -type d -exec chmod 750 {} \;
find config/certs -type f -exec chmod 640 {} \;
echo "certificates ready"
