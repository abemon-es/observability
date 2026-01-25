#!/usr/bin/env python3
"""
Railway Prometheus Exporter
Queries Railway GraphQL API and exposes metrics for Prometheus.
"""

import os
import time
import requests
from prometheus_client import start_http_server, Gauge, Info

# Configuration
RAILWAY_API = "https://backboard.railway.app/graphql/v2"
RAILWAY_TOKEN = os.environ.get("RAILWAY_API_TOKEN", "")
PORT = int(os.environ.get("PORT", 9090))
SCRAPE_INTERVAL = int(os.environ.get("SCRAPE_INTERVAL", 60))

# Projects and environments (same as locomotive)
PROJECTS = [
    {"name": "abemon.es", "env": "b1901a72-177e-44fc-a676-df0337dd33be"},
    {"name": "BM Consulting", "env": "39710a9b-5818-4f1b-8aa5-5da54a821e66"},
    {"name": "foodplan.pro", "env": "1d8b9c3d-375c-4562-923f-aea9f2922593"},
    {"name": "codex.abemon.es", "env": "afb301e5-f182-4cfa-9e6e-e32966f70ec0"},
    {"name": "blue-mountain.es", "env": "a28d09c7-8d40-44af-98e2-dfca8417ae9e"},
    {"name": "Logistics Express", "env": "8c0cf65a-6b07-41a7-a8cb-bee88d0eb03b"},
    {"name": "app.logisticsexpress.es", "env": "ace99da7-959d-4d02-a258-d39259e869c0"},
    {"name": "trafico-dashboard", "env": "be69a746-d09a-4a4b-b9ca-3fd912718421"},
    {"name": "z.logisticsexpress.es", "env": "ccc1e76b-0bb9-450a-bc25-2209990a6449"},
    {"name": "observability", "env": "9038a29f-efed-4d61-9b6d-2f17c74cc8f1"},
]

# Prometheus metrics
cpu_usage = Gauge('railway_service_cpu_usage', 'CPU cores used', ['project_name', 'service_name', 'environment_name'])
memory_usage_gb = Gauge('railway_service_memory_usage_gb', 'Memory usage in GB', ['project_name', 'service_name', 'environment_name'])
cpu_utilization = Gauge('railway_service_cpu_utilization', 'CPU utilization (0-1)', ['project_name', 'service_name', 'environment_name'])
memory_utilization = Gauge('railway_service_memory_utilization', 'Memory utilization (0-1)', ['project_name', 'service_name', 'environment_name'])
network_rx_gb = Gauge('railway_service_network_rx_gb_total', 'Network received in GB', ['project_name', 'service_name', 'environment_name'])
network_tx_gb = Gauge('railway_service_network_tx_gb_total', 'Network transmitted in GB', ['project_name', 'service_name', 'environment_name'])
service_up = Gauge('railway_service_up', 'Service is running (1) or not (0)', ['project_name', 'service_name', 'environment_name'])
services_total = Gauge('railway_services_total', 'Total number of services', ['project_name'])
exporter_info = Info('railway_exporter', 'Railway Prometheus Exporter info')
scrape_duration = Gauge('railway_exporter_scrape_duration_seconds', 'Time taken to scrape metrics')
scrape_errors = Gauge('railway_exporter_scrape_errors_total', 'Number of scrape errors')

headers = {"Authorization": f"Bearer {RAILWAY_TOKEN}", "Content-Type": "application/json"}


def graphql_request(query, variables=None):
    """Execute GraphQL request to Railway API."""
    payload = {"query": query}
    if variables:
        payload["variables"] = variables

    try:
        response = requests.post(RAILWAY_API, json=payload, headers=headers, timeout=30)
        response.raise_for_status()
        data = response.json()
        if "errors" in data:
            print(f"GraphQL errors: {data['errors']}")
            return None
        return data.get("data")
    except Exception as e:
        print(f"API request failed: {e}")
        return None


def get_services(env_id):
    """Get all services in an environment."""
    query = '''query($envId: String!) {
        environment(id: $envId) {
            serviceInstances {
                edges {
                    node {
                        serviceId
                        serviceName
                        latestDeployment { id status }
                    }
                }
            }
        }
    }'''

    data = graphql_request(query, {"envId": env_id})
    if not data:
        return []

    try:
        edges = data.get("environment", {}).get("serviceInstances", {}).get("edges", [])
        return [
            {
                "service_id": e["node"]["serviceId"],
                "service_name": e["node"]["serviceName"],
                "deployment_id": e["node"]["latestDeployment"]["id"] if e["node"]["latestDeployment"] else None,
                "status": e["node"]["latestDeployment"]["status"] if e["node"]["latestDeployment"] else "UNKNOWN"
            }
            for e in edges
        ]
    except Exception as e:
        print(f"Error parsing services: {e}")
        return []


def get_metrics(service_id, env_id):
    """Get metrics for a service using Railway's GraphQL API."""
    start_date = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(time.time() - 300))

    query = '''query($serviceId: String!, $envId: String!, $startDate: DateTime!) {
        metrics(
            serviceId: $serviceId
            environmentId: $envId
            measurements: [CPU_USAGE, MEMORY_USAGE_GB, NETWORK_RX_GB, NETWORK_TX_GB]
            startDate: $startDate
        ) {
            measurement
            values {
                ts
                value
            }
        }
    }'''

    data = graphql_request(query, {
        "serviceId": service_id,
        "envId": env_id,
        "startDate": start_date
    })

    metrics = {
        "cpu_usage": 0,
        "memory_usage_gb": 0,
        "network_rx_gb": 0,
        "network_tx_gb": 0
    }

    if not data:
        return metrics

    try:
        metrics_data = data.get("metrics", [])
        for item in metrics_data:
            measurement = item.get("measurement", "")
            values = item.get("values", [])

            # Get the latest value (last in the list)
            if values:
                latest_value = values[-1].get("value", 0)

                if measurement == "CPU_USAGE":
                    metrics["cpu_usage"] = float(latest_value) if latest_value else 0
                elif measurement == "MEMORY_USAGE_GB":
                    metrics["memory_usage_gb"] = float(latest_value) if latest_value else 0
                elif measurement == "NETWORK_RX_GB":
                    metrics["network_rx_gb"] = float(latest_value) if latest_value else 0
                elif measurement == "NETWORK_TX_GB":
                    metrics["network_tx_gb"] = float(latest_value) if latest_value else 0
    except Exception as e:
        print(f"Error parsing metrics for {service_id}: {e}")

    return metrics


def collect_metrics():
    """Collect metrics from all configured projects."""
    start_time = time.time()
    errors = 0

    print(f"Collecting metrics from {len(PROJECTS)} projects...")

    for project in PROJECTS:
        project_name = project["name"]
        env_id = project["env"]
        env_name = "production"

        services = get_services(env_id)

        if not services:
            errors += 1
            services_total.labels(project_name=project_name).set(0)
            continue

        services_total.labels(project_name=project_name).set(len(services))
        print(f"  {project_name}: {len(services)} services")

        for svc in services:
            service_name = svc["service_name"]
            service_id = svc["service_id"]
            status = svc["status"]

            labels = [project_name, service_name, env_name]

            # Set service status
            is_up = 1 if status == "SUCCESS" else 0
            service_up.labels(*labels).set(is_up)

            # Get resource metrics
            metrics = get_metrics(service_id, env_id)

            cpu_val = metrics["cpu_usage"]
            mem_val = metrics["memory_usage_gb"]

            cpu_usage.labels(*labels).set(cpu_val)
            memory_usage_gb.labels(*labels).set(mem_val)

            # Calculate utilization based on 2 vCPU / 2 GB limits
            cpu_utilization.labels(*labels).set(min(cpu_val / 2.0, 1.0) if cpu_val > 0 else 0)
            memory_utilization.labels(*labels).set(min(mem_val / 2.0, 1.0) if mem_val > 0 else 0)

            network_rx_gb.labels(*labels).set(metrics["network_rx_gb"])
            network_tx_gb.labels(*labels).set(metrics["network_tx_gb"])

    duration = time.time() - start_time
    scrape_duration.set(duration)
    scrape_errors.set(errors)
    print(f"Collection complete in {duration:.2f}s with {errors} errors")


def main():
    """Main entry point."""
    if not RAILWAY_TOKEN:
        print("ERROR: RAILWAY_API_TOKEN environment variable not set")
        return

    print(f"Starting Railway Prometheus Exporter on port {PORT}")
    print(f"Monitoring {len(PROJECTS)} projects")

    exporter_info.info({
        'version': '1.1.0',
        'scrape_interval': str(SCRAPE_INTERVAL),
        'projects_count': str(len(PROJECTS))
    })

    # Start HTTP server for Prometheus
    start_http_server(PORT)
    print(f"Metrics available at http://localhost:{PORT}/metrics")

    # Collect metrics on startup
    collect_metrics()

    # Collection loop
    while True:
        time.sleep(SCRAPE_INTERVAL)
        try:
            collect_metrics()
        except Exception as e:
            print(f"Error collecting metrics: {e}")


if __name__ == "__main__":
    main()
