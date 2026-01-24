#!/bin/bash
# Setup script for Railway Prometheus Exporter
# This script helps configure the railway-exporter service

set -e

echo "=========================================="
echo "Railway Prometheus Exporter Setup"
echo "=========================================="
echo ""

# Check if we're in the right project
PROJECT_ID="cb1723d3-f012-4a67-8c44-798d00f50c29"
ENVIRONMENT="production"

echo "1. Creating Railway API Token..."
echo "   Go to: https://railway.com/account/tokens"
echo "   Create a new token with read access"
echo "   Copy the token value"
echo ""
read -p "Paste your RAILWAY_API_TOKEN: " API_TOKEN

if [ -z "$API_TOKEN" ]; then
    echo "Error: No token provided"
    exit 1
fi

echo ""
echo "2. Creating railway-exporter service..."
echo ""

# Navigate to the observability project
cd "$(dirname "$0")/.."

# Try to create service
railway add --service railway-exporter 2>/dev/null || true

echo ""
echo "3. Linking and deploying..."
cd railway-exporter

# Link to the new service
railway link -p "$PROJECT_ID" -e "$ENVIRONMENT" --service railway-exporter

# Set the environment variable
railway variables --set "RAILWAY_API_TOKEN=$API_TOKEN"

# Deploy
railway up

echo ""
echo "=========================================="
echo "Setup Complete!"
echo "=========================================="
echo ""
echo "The exporter will be available at:"
echo "  Internal: railway-exporter.railway.internal:9090"
echo "  Metrics:  /metrics"
echo ""
echo "Prometheus is configured to scrape this endpoint."
echo "Check Grafana 'Railway Resources' dashboard for metrics."
echo ""
