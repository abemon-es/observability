#!/bin/sh
set -e

echo "[ENTRYPOINT] Starting Grafana with password reset..." >&2

# Use grafana-cli to reset password
# This runs before the main server starts
if [ -n "$GF_SECURITY_ADMIN_PASSWORD" ]; then
    echo "[ENTRYPOINT] Resetting admin password from env var..." >&2
    grafana-cli --homepath=/usr/share/grafana \
                --config=/etc/grafana/grafana.ini \
                admin reset-admin-password "$GF_SECURITY_ADMIN_PASSWORD" 2>&1 || echo "[ENTRYPOINT] Password reset failed (may be first run or db not ready)" >&2
else
    echo "[ENTRYPOINT] GF_SECURITY_ADMIN_PASSWORD not set, skipping reset" >&2
fi

echo "[ENTRYPOINT] Starting Grafana server via /run.sh..." >&2
exec /run.sh
