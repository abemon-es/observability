#!/bin/bash
set -e

# Start Grafana in background to initialize DB
grafana-server --homepath=/usr/share/grafana --config=/etc/grafana/grafana.ini cfg:default.paths.data=/var/lib/grafana cfg:default.paths.logs=/var/log/grafana cfg:default.paths.plugins=/var/lib/grafana/plugins &
GRAFANA_PID=$!

# Wait for Grafana to be ready
sleep 10

# Reset admin password
grafana-cli admin reset-admin-password "${GF_SECURITY_ADMIN_PASSWORD:-admin}" || true

# Stop background Grafana
kill $GRAFANA_PID 2>/dev/null || true
sleep 2

# Start Grafana properly
exec grafana-server --homepath=/usr/share/grafana --config=/etc/grafana/grafana.ini cfg:default.paths.data=/var/lib/grafana cfg:default.paths.logs=/var/log/grafana cfg:default.paths.plugins=/var/lib/grafana/plugins
