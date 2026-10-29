#!/bin/bash
# =============================================================================
# Unit 02 - one-shot job: import the data view + Lens charts + dashboard
# ("dashboard as code": the same objects can be built by hand in the UI).
# overwrite=true -> safe to run again (fixed ids, no duplicates).
# =============================================================================
set -euo pipefail
curl -sS --fail -u "elastic:${ELASTIC_PASSWORD}" -H 'kbn-xsrf: true' \
  -X POST "http://kibana:${KIBANA_PORT}/api/saved_objects/_import?overwrite=true" \
  --form file=@/init/kibana-dashboard.ndjson | grep -q '"success":true'
echo "dashboard imported: http://localhost:${KIBANA_HOST_PORT}/app/dashboards#/view/bookandride-dashboard"
