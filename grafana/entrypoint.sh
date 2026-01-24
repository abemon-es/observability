#!/bin/sh
set -e

echo "Starting Grafana with password reset..."

# Use grafana-cli to reset password
# This runs before the main server starts
if [ -n "$GF_SECURITY_ADMIN_PASSWORD" ]; then
    echo "Resetting admin password from env var..."
    grafana-cli --homepath=/usr/share/grafana \
                --config=/etc/grafana/grafana.ini \
                admin reset-admin-password "$GF_SECURITY_ADMIN_PASSWORD" || echo "Password reset failed (may be first run)"
fi

echo "Starting Grafana server..."
exec /run.sh
