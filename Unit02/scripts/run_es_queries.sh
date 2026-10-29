#!/usr/bin/env bash
# =============================================================================
# Course Part A, exercises 2-4: run the queries of elk/queries/ and save the
# JSON outputs + the export of logs-demo into docs/es_outputs/ (deliverables).
#   ./scripts/run_es_queries.sh              -> index logs-demo (course dataset)
#   ./scripts/run_es_queries.sh logs-*       -> course dataset + API logs
# =============================================================================
source "$(dirname "$0")/_env.sh"
INDEX=${1:-logs-demo}
OUT=docs/es_outputs; mkdir -p "$OUT"
for q in elk/queries/*.json; do
  name=$(basename "$q" .json)
  ./scripts/es.sh POST "/${INDEX}/_search?pretty" "$q" > "$OUT/${INDEX//\*/all}_${name}.json"
  printf '%-22s hits=%-4s ' "$name" "$(python3 -c 'import json,sys;print(json.load(sys.stdin)["hits"]["total"]["value"])' < "$OUT/${INDEX//\*/all}_${name}.json")"
  python3 - "$OUT/${INDEX//\*/all}_${name}.json" <<'PY'
import json, sys
r = json.load(open(sys.argv[1]))
for agg in r.get("aggregations", {}).values():
    print(" ".join(f"{b['key']}={b['doc_count']}" for b in agg["buckets"]), end="")
print()
PY
done
# exercise 4: export the index (scroll not needed for a few hundred documents)
./scripts/es.sh GET "/logs-demo/_search?size=1000&sort=@timestamp:asc" > "$OUT/logs-demo-export.json"
echo "outputs saved in $OUT/"
