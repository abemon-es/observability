#!/usr/bin/env python3
"""Railway → Loki Log Forwarder - Multi-project support"""
import os
import time
import json
import requests
from datetime import datetime

RAILWAY_API = "https://backboard.railway.app/graphql/v2"
RAILWAY_TOKEN = os.environ["LOCOMOTIVE_RAILWAY_API_KEY"]
LOKI_URL = os.environ.get("LOKI_URL", "http://loki.railway.internal:3100")

# All projects and their environments
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
]

headers = {"Authorization": f"Bearer {RAILWAY_TOKEN}", "Content-Type": "application/json"}

def get_services(env_id):
    """Get all services in an environment"""
    q = '''query($envId: String!) {
        environment(id: $envId) {
            serviceInstances { edges { node { serviceId serviceName latestDeployment { id } } } }
        }
    }'''
    try:
        r = requests.post(RAILWAY_API, json={"query": q, "variables": {"envId": env_id}}, headers=headers, timeout=10)
        edges = r.json().get("data", {}).get("environment", {}).get("serviceInstances", {}).get("edges", [])
        return [(e["node"]["serviceName"], e["node"]["serviceId"], 
                 e["node"]["latestDeployment"]["id"] if e["node"]["latestDeployment"] else None) 
                for e in edges]
    except Exception as e:
        print(f"Error getting services: {e}")
        return []

def get_logs(deployment_id, limit=50):
    """Fetch logs from a deployment"""
    q = '''query($did: String!, $lim: Int!) { 
        deploymentLogs(deploymentId: $did, limit: $lim) { message timestamp } 
    }'''
    try:
        r = requests.post(RAILWAY_API, json={"query": q, "variables": {"did": deployment_id, "lim": limit}}, headers=headers, timeout=10)
        return r.json().get("data", {}).get("deploymentLogs", [])
    except:
        return []

def push_to_loki(logs, labels):
    """Push logs to Loki"""
    if not logs:
        return None
    values = []
    for log in logs:
        ts = log.get("timestamp", "")
        msg = log.get("message", "")
        if not msg:
            continue
        try:
            dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
            ns = str(int(dt.timestamp() * 1e9))
        except:
            ns = str(int(time.time() * 1e9))
        # Clean message
        msg = msg.replace('\x00', '').strip()
        if msg:
            values.append([ns, msg])
    
    if not values:
        return None
    
    payload = {"streams": [{"stream": labels, "values": values}]}
    try:
        r = requests.post(f"{LOKI_URL}/loki/api/v1/push", json=payload, timeout=10)
        return r.status_code
    except Exception as e:
        return str(e)

def main():
    print("=" * 50)
    print("Railway → Loki Log Forwarder (Multi-Project)")
    print(f"Projects: {len(PROJECTS)}")
    print(f"Loki: {LOKI_URL}")
    print("=" * 50)
    
    seen = {}
    
    while True:
        total_logs = 0
        for project in PROJECTS:
            proj_name = project["name"]
            env_id = project["env"]
            
            services = get_services(env_id)
            for svc_name, svc_id, dep_id in services:
                if not dep_id:
                    continue
                
                key = f"{proj_name}:{svc_name}"
                if key not in seen:
                    seen[key] = set()
                
                logs = get_logs(dep_id, 100)
                new_logs = []
                for log in logs:
                    sig = (log.get("timestamp"), log.get("message", "")[:100])
                    if sig not in seen[key]:
                        seen[key].add(sig)
                        new_logs.append(log)
                
                if new_logs:
                    labels = {"project": proj_name, "service": svc_name, "env": "production"}
                    status = push_to_loki(new_logs, labels)
                    print(f"[{proj_name}/{svc_name}] {len(new_logs)} logs → {status}")
                    total_logs += len(new_logs)
                
                # Keep seen set manageable
                if len(seen[key]) > 500:
                    seen[key] = set(list(seen[key])[-250:])
        
        if total_logs > 0:
            print(f"--- Cycle complete: {total_logs} new logs ---")
        time.sleep(30)

if __name__ == "__main__":
    main()
