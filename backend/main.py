from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
import uuid
from datetime import datetime, timedelta
import random

app = FastAPI(title="CloudOps Sentinel", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory database
db: Dict[str, Any] = {
    "services": {},
    "metrics": {},
    "incidents": {},
}

# Pydantic Models
class ServiceCreate(BaseModel):
    name: str = Field(..., min_length=3, max_length=100)
    endpoint_url: str = Field(..., min_length=1, max_length=500)
    check_interval_sec: int = Field(..., ge=5, le=3600)

class ServiceResponse(BaseModel):
    id: str
    name: str
    endpoint_url: str
    status: str
    uptime_pct: float
    check_interval_sec: int

class MetricResponse(BaseModel):
    id: str
    service_id: str
    latency_ms: float
    status_code: int
    timestamp: datetime

class IncidentCreate(BaseModel):
    service_id: str
    severity: str = Field(..., pattern="^(critical|high|medium|low)$")
    summary: str = Field(..., min_length=10, max_length=500)

class IncidentResponse(BaseModel):
    id: str
    service_id: str
    severity: str
    summary: str
    status: str
    created_at: datetime
    resolved_at: Optional[datetime]

class IncidentResolveRequest(BaseModel):
    resolution_notes: str = Field(..., min_length=1, max_length=1000)

# Seed Data Initialization
def seed_data():
    now = datetime.utcnow()
    
    # Services
    service_ids = []
    services_data = [
        {"name": "Payment Gateway", "endpoint_url": "https://api.payments.example.com/health", "status": "Healthy", "uptime_pct": 99.99, "check_interval_sec": 30},
        {"name": "Auth Service", "endpoint_url": "https://auth.example.com/health", "status": "Healthy", "uptime_pct": 99.95, "check_interval_sec": 15},
        {"name": "Notification Hub", "endpoint_url": "https://notify.example.com/health", "status": "Degraded", "uptime_pct": 98.50, "check_interval_sec": 10},
        {"name": "Search API", "endpoint_url": "https://search.example.com/health", "status": "Healthy", "uptime_pct": 99.90, "check_interval_sec": 20},
    ]
    
    for svc in services_data:
        svc_id = str(uuid.uuid4())
        service_ids.append(svc_id)
        db["services"][svc_id] = {
            "id": svc_id,
            "name": svc["name"],
            "endpoint_url": svc["endpoint_url"],
            "status": svc["status"],
            "uptime_pct": svc["uptime_pct"],
            "check_interval_sec": svc["check_interval_sec"],
        }
        
        # Generate metrics history for each service (last 24 hours, 15 min intervals)
        for i in range(96):
            ts = now - timedelta(minutes=15 * (96 - i))
            base_latency = 50 if svc["status"] == "Healthy" else 250
            latency = base_latency + random.uniform(-10, 50)
            status_code = 200 if svc["status"] == "Healthy" else (503 if random.random() > 0.7 else 200)
            
            metric_id = str(uuid.uuid4())
            db["metrics"][metric_id] = {
                "id": metric_id,
                "service_id": svc_id,
                "latency_ms": round(latency, 2),
                "status_code": status_code,
                "timestamp": ts,
            }

    # Incidents
    # Incident 1: Notification Hub Degraded (Active)
    inc1_id = str(uuid.uuid4())
    db["incidents"][inc1_id] = {
        "id": inc1_id,
        "service_id": service_ids[2], # Notification Hub
        "severity": "high",
        "summary": "Elevated latency detected on Notification Hub. P95 latency exceeded 500ms threshold.",
        "status": "active",
        "created_at": now - timedelta(hours=2),
        "resolved_at": None,
    }
    
    # Incident 2: Payment Gateway Timeout (Resolved)
    inc2_id = str(uuid.uuid4())
    db["incidents"][inc2_id] = {
        "id": inc2_id,
        "service_id": service_ids[0], # Payment Gateway
        "severity": "critical",
        "summary": "Payment Gateway experiencing intermittent 504 Gateway Timeouts during peak load.",
        "status": "resolved",
        "created_at": now - timedelta(days=1, hours=4),
        "resolved_at": now - timedelta(days=1, hours=2),
    }

seed_data()

# Endpoints

@app.get("/api/health")
def health_check():
    return {
        "status": "healthy",
        "service": "cloudops-sentinel",
        "timestamp": datetime.utcnow().isoformat()
    }

@app.get("/api/services", response_model=List[ServiceResponse])
def list_services():
    return list(db["services"].values())

@app.post("/api/services", response_model=ServiceResponse, status_code=201)
def create_service(service: ServiceCreate):
    service_id = str(uuid.uuid4())
    new_service = {
        "id": service_id,
        "name": service.name,
        "endpoint_url": service.endpoint_url,
        "status": "Unknown",
        "uptime_pct": 100.0,
        "check_interval_sec": service.check_interval_sec,
    }
    db["services"][service_id] = new_service
    return new_service

@app.get("/api/services/{service_id}/metrics", response_model=List[MetricResponse])
def get_service_metrics(
    service_id: str,
    limit: int = Query(100, ge=1, le=1000),
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None
):
    if service_id not in db["services"]:
        raise HTTPException(status_code=404, detail="Service not found")
    
    metrics = [m for m in db["metrics"].values() if m["service_id"] == service_id]
    
    if start_time:
        metrics = [m for m in metrics if m["timestamp"] >= start_time]
    if end_time:
        metrics = [m for m in metrics if m["timestamp"] <= end_time]
        
    # Sort by timestamp descending
    metrics.sort(key=lambda x: x["timestamp"], reverse=True)
    return metrics[:limit]

@app.post("/api/incidents", response_model=IncidentResponse, status_code=201)
def create_incident(incident: IncidentCreate):
    if incident.service_id not in db["services"]:
        raise HTTPException(status_code=404, detail="Service not found")
        
    incident_id = str(uuid.uuid4())
    new_incident = {
        "id": incident_id,
        "service_id": incident.service_id,
        "severity": incident.severity,
        "summary": incident.summary,
        "status": "active",
        "created_at": datetime.utcnow(),
        "resolved_at": None,
    }
    db["incidents"][incident_id] = new_incident
    
    # Update service status to reflect incident
    service = db["services"][incident.service_id]
    if incident.severity in ["critical", "high"]:
        service["status"] = "Down"
    else:
        service["status"] = "Degraded"
        
    return new_incident

@app.get("/api/incidents", response_model=List[IncidentResponse])
def list_incidents(
    status: Optional[str] = Query(None, pattern="^(active|resolved|all)$"),
    service_id: Optional[str] = None
):
    incidents = list(db["incidents"].values())
    
    if status and status != "all":
        incidents = [i for i in incidents if i["status"] == status]