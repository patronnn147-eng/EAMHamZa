#!/bin/bash
# Continuous Trivy scanner loop
# Runs every SCAN_INTERVAL seconds (default 6h = 21600s)
# Scans all images listed in IMAGES env var, pushes metrics to PUSHGATEWAY_URL
#
# Environment variables (set in docker-compose.monitoring.yml):
#   PUSHGATEWAY_URL  — e.g. http://pushgateway:9091
#   IMAGES           — space-separated image names, e.g. "eam-backend:latest eam-frontend:latest"
#   SCAN_INTERVAL    — seconds between full scan cycles (default 21600 = 6h)

set -euo pipefail

PUSHGATEWAY_URL="${PUSHGATEWAY_URL:-http://pushgateway:9091}"
SCAN_INTERVAL="${SCAN_INTERVAL:-21600}"

echo "[trivy-scanner] Starting continuous scan loop"
echo "[trivy-scanner] Pushgateway: ${PUSHGATEWAY_URL}"
echo "[trivy-scanner] Scan interval: ${SCAN_INTERVAL}s"
echo "[trivy-scanner] Images: ${IMAGES}"

while true; do
    echo ""
    echo "[trivy-scanner] === Scan cycle started at $(date -u '+%Y-%m-%dT%H:%M:%SZ') ==="

    for img in ${IMAGES}; do
        TAGNAME="${img%%:*}"
        JSON_FILE="/tmp/trivy-${TAGNAME}.json"

        echo "[trivy-scanner] Scanning ${img} ..."

        # Scan image — continue on failure (image may not exist yet locally)
        if trivy image \
            --format json \
            --output "${JSON_FILE}" \
            --severity CRITICAL,HIGH,MEDIUM,LOW \
            --quiet \
            "${img}" 2>&1; then

            echo "[trivy-scanner] Pushing metrics for ${img} ..."
            python3 /scripts/trivy_push_metrics.py \
                "${JSON_FILE}" \
                "${img}" \
                "${PUSHGATEWAY_URL}" || true

            rm -f "${JSON_FILE}"
        else
            echo "[trivy-scanner] WARN: Failed to scan ${img} — image may not exist locally. Skipping."
        fi
    done

    echo "[trivy-scanner] Cycle complete. Next scan in ${SCAN_INTERVAL}s ($(date -u -d "+${SCAN_INTERVAL} seconds" '+%Y-%m-%dT%H:%M:%SZ' 2>/dev/null || echo 'N/A'))."
    sleep "${SCAN_INTERVAL}"
done
