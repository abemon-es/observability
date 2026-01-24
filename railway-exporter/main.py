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

# Prometheus metrics
cpu_usage = Gauge('railway_service_cpu_usage', 'CPU cores used', ['project_name', 'service_name', 'environment_name'])
memory_usage_gb = Gauge('railway_service_memory_usage_gb', 'Memory usage in GB', ['project_name', 'service_name', 'environment_name'])
cpu_utilization = Gauge('railway_service_cpu_utilization', 'CPU utilization (0-1)', ['project_name', 'service_name', 'environment_name'])
memory_utilization = Gauge('railway_service_memory_utilization', 'Memory utilization (0-1)', ['project_name', 'service_name', 'environment_name'])
network_rx_gb = Gauge('railway_service_network_rx_gb_total', 'Network received in GB', ['project_name', 'service_name', 'environment_name'])
network_tx_gb = Gauge('railway_service_network_tx_gb_total', 'Network transmitted in GB', ['project_name', 'service_name', 'environment_name'])
service_up = Gauge('railway_service_up', 'Service is running (1) or not (0)', ['project_name', 'service_name', 'environment_name'])
exporter_info = Info('railway_exporter', 'Railway Prometheus Exporter info')

# GraphQL Queries
PROJECTS_QUERY = """
query {
  me {
    workspaces {
      edges {
        node {
          id
          name
          projects {
            edges {
              node {
                id
                name
                environments {
                  edges {
                    node {
                      id
                      name
                    }
                  }
                }
                services {
                  edges {
                    node {
                      id
                      name
                    }
                  }
                }
              }
            }
          }
        }
      }
    }
  }
}
"""

METRICS_QUERY = """
query ServiceMetrics($serviceId: String!, $envId: String!) {
  metrics(
    serviceId: $serviceId
    environmentId: $envId
    measurements: [CPU_USAGE, MEMORY_USAGE_GB, NETWORK_RX_GB, NETWORK_TX_GB]
    startDate: "%s"
  ) {
    measurements
    values
    tags
  }

  service(id: $serviceId) {
    id
    name
    serviceInstances(environmentId: $envId) {
      edges {
        node {
          healthStatus
        }
      }
    }
  }
}
"""

DEPLOYMENT_QUERY = """
query DeploymentStatus($serviceId: String!, $envId: String!) {
  deployments(
    first: 1
    input: {
      serviceId: $serviceId
      environmentId: $envId
    }
  ) {
    edges {
      node {
        id
        status
        staticUrl
      }
    }
  }
}
"""


def graphql_request(query, variables=None):
    """Execute GraphQL request to Railway API."""
    headers = {
        "Authorization": f"Bearer {RAILWAY_TOKEN}",
        "Content-Type": "application/json"
    }
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


def get_projects_and_services():
    """Get all projects, services, and environments."""
    data = graphql_request(PROJECTS_QUERY)
    if not data:
        return []

    result = []
    try:
        for ws_edge in data.get("me", {}).get("workspaces", {}).get("edges", []):
            workspace = ws_edge.get("node", {})
            for proj_edge in workspace.get("projects", {}).get("edges", []):
                project = proj_edge.get("node", {})
                project_id = project.get("id")
                project_name = project.get("name")

                environments = []
                for env_edge in project.get("environments", {}).get("edges", []):
                    env = env_edge.get("node", {})
                    environments.append({"id": env.get("id"), "name": env.get("name")})

                for svc_edge in project.get("services", {}).get("edges", []):
                    service = svc_edge.get("node", {})
                    result.append({
                        "project_id": project_id,
                        "project_name": project_name,
                        "service_id": service.get("id"),
                        "service_name": service.get("name"),
                        "environments": environments
                    })
    except Exception as e:
        print(f"Error parsing projects: {e}")

    return result


def collect_metrics():
    """Collect metrics from all services."""
    print("Collecting metrics...")
    services = get_projects_and_services()

    if not services:
        print("No services found")
        return

    print(f"Found {len(services)} services")

    # Use timestamp from 5 minutes ago for metrics query
    start_date = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(time.time() - 300))

    for svc in services:
        project_name = svc["project_name"]
        service_name = svc["service_name"]
        service_id = svc["service_id"]

        for env in svc["environments"]:
            env_id = env["id"]
            env_name = env["name"]

            labels = [project_name, service_name, env_name]

            # Get deployment status
            deploy_data = graphql_request(DEPLOYMENT_QUERY, {
                "serviceId": service_id,
                "envId": env_id
            })

            is_up = 0
            if deploy_data:
                deployments = deploy_data.get("deployments", {}).get("edges", [])
                if deployments:
                    status = deployments[0].get("node", {}).get("status", "")
                    is_up = 1 if status == "SUCCESS" else 0

            service_up.labels(*labels).set(is_up)

            # Get resource metrics
            query = METRICS_QUERY % start_date
            metrics_data = graphql_request(query, {
                "serviceId": service_id,
                "envId": env_id
            })

            if not metrics_data or not metrics_data.get("metrics"):
                # Set zero values if no metrics
                cpu_usage.labels(*labels).set(0)
                memory_usage_gb.labels(*labels).set(0)
                cpu_utilization.labels(*labels).set(0)
                memory_utilization.labels(*labels).set(0)
                network_rx_gb.labels(*labels).set(0)
                network_tx_gb.labels(*labels).set(0)
                continue

            # Parse metrics
            for metric in metrics_data.get("metrics", []):
                measurements = metric.get("measurements", [])
                values = metric.get("values", [])

                # Get latest value (last in array)
                for i, measurement in enumerate(measurements):
                    if values and len(values) > i:
                        latest_values = values[i] if isinstance(values[i], list) else [values[i]]
                        value = latest_values[-1] if latest_values else 0
                    else:
                        value = 0

                    if measurement == "CPU_USAGE":
                        cpu_usage.labels(*labels).set(value)
                        # Assume 2 vCPU limit for utilization calculation
                        cpu_utilization.labels(*labels).set(min(value / 2.0, 1.0))
                    elif measurement == "MEMORY_USAGE_GB":
                        memory_usage_gb.labels(*labels).set(value)
                        # Assume 2 GB limit for utilization calculation
                        memory_utilization.labels(*labels).set(min(value / 2.0, 1.0))
                    elif measurement == "NETWORK_RX_GB":
                        network_rx_gb.labels(*labels).set(value)
                    elif measurement == "NETWORK_TX_GB":
                        network_tx_gb.labels(*labels).set(value)

    print("Metrics collection complete")


def main():
    """Main entry point."""
    if not RAILWAY_TOKEN:
        print("ERROR: RAILWAY_API_TOKEN environment variable not set")
        return

    print(f"Starting Railway Prometheus Exporter on port {PORT}")
    exporter_info.info({
        'version': '1.0.0',
        'scrape_interval': str(SCRAPE_INTERVAL)
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
