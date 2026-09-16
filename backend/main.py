from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, HttpUrl
from typing import List, Optional, Dict, Any
import uuid
from datetime import datetime, timedelta
import random

app = FastAPI(
    title="CloudOps Sentinel",
    description="Real-Time Infrastructure Health & Incident Monitor",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory database
services_db: Dict[str, Dict[str, Any]] = {}
metrics_db: Dict[str, Dict[str, Any]] = {}
incidents_db: Dict[str, Dict[str, Any]] = {}

# Pydantic Models
class ServiceCreate(BaseModel):
    name: str = Field(..., min_length=3, max_length=100)
    endpoint_url: str = Field(..., min_length=10, max_length=500)
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
    resolution_notes: Optional[str] = Field(None, max_length=1000)

class HealthResponse(BaseModel):
    status: str
    service: str
    timestamp: datetime

# Seed Data Initialization
def seed_data():
    now = datetime.utcnow()
    
    # Service 1: Payment Gateway
    svc1_id = str(uuid.uuid4())
    services_db[svc1_id] = {
        "id": svc1_id,
        "name": "Payment Gateway",
        "endpoint_url": "https://api.payments.example.com/health",
        "status": "Healthy",
        "uptime_pct": 99.99,
        "check_interval_sec": 30
    }
    
    # Service 2: Auth Service
    svc2_id = str(uuid.uuid4())
    services_db[svc2_id] = {
        "id": svc2_id,
        "name": "Auth Service",
        "endpoint_url": "https://auth.example.com/health",
        "status": "Healthy",
        "uptime_pct": 99.95,
        "check_interval_sec": 15
    }
    
    # Service 3: Notification Hub
    svc3_id = str(uuid.uuid4())
    services_db[svc3_id] = {
        "id": svc3_id,
        "name": "Notification Hub",
        "endpoint_url": "https://notify.example.com/health",
        "status": "Degraded",
        "uptime_pct": 97.50,
        "check_interval_sec": 10
    }
    
    # Service 4: Search API
    svc4_id = str(uuid.uuid4())
    services_db[svc4_id] = {
        "id": svc4_id,
        "name": "Search API",
        "endpoint_url": "https://search.example.com/health",
        "status": "Healthy",
        "uptime_pct": 99.90,
        "check_interval_sec": 20
    }
    
    # Generate Metrics History (last 1 hour, 10 min intervals)
    for svc_id in [svc1_id, svc2_id, svc3_id, svc4_id]:
        for i in range(6):
            ts = now - timedelta(minutes=i * 10)
            if svc_id == svc3_id:
                latency = random.uniform(450, 1200)
                status_code = random.choice([200, 503, 500])
            else:
                latency = random.uniform(20, 150)
                status_code = 200
            
            metric_id = str(uuid.uuid4())
            metrics_db[metric_id] = {
                "id": metric_id,
                "service_id": svc_id,
                "latency_ms": round(latency, 2),
                "status_code": status_code,
                "timestamp": ts
            }
    
    # Incident 1: Active Critical
    inc1_id = str(uuid.uuid4())
    incidents_db[inc1_id] = {
        "id": inc1_id,
        "service_id": svc3_id,
        "severity": "critical",
        "summary": "High latency detected on Notification Hub, error rate above 5%",
        "status": "active",
        "created_at": now - timedelta(minutes=15),
        "resolved_at": None
    }
    
    # Incident 2: Resolved High
    inc2_id = str(uuid.uuid4())
    incidents_db[inc2_id] = {
        "id": inc2_id,
        "service_id": svc1_id,
        "severity": "high",
        "summary": "Transient timeout spike on Payment Gateway during peak load",
        "status": "resolved",
        "created_at": now - timedelta(hours=2),
        "resolved_at": now - timedelta(hours=1, minutes=45)
    }

seed_data()

# Endpoints

@app.get("/api/health", response_model=HealthResponse)
def get_health():
    return {
        "status": "healthy",
        "service": "cloudops-sentinel",
        "timestamp": datetime.utcnow()
    }

@app.get("/api/services", response_model=List[ServiceResponse])
def list_services():
    return list(services_db.values())

@app.post("/api/services", response_model=ServiceResponse, status_code=201)
def create_service(service: ServiceCreate):
    new_id = str(uuid.uuid4())
    new_service = {
        "id": new_id,
        "name": service.name,
        "endpoint_url": service.endpoint_url,
        "status": "Unknown",
        "uptime_pct": 100.0,
        "check_interval_sec": service.check_interval_sec
    }
    services_db[new_id] = new_service
    return new_service

@app.get("/api/services/{service_id}/metrics", response_model=List[MetricResponse])
def get_service_metrics(
    service_id: str,
    limit: int = Query(50, ge=1, le=1000),
    since: Optional[datetime] = None
):
    if service_id not in services_db:
        raise HTTPException(status_code=404, detail="Service not found")
    
    service_metrics = [
        m for m in metrics_db.values() 
        if m["service_id"] == service_id
    ]
    
    if since:
        service_metrics = [m for m in service_metrics if m["timestamp"] >= since]
    
    service_metrics.sort(key=lambda x: x["timestamp"], reverse=True)
    return service_metrics[:limit]

@app.post("/api/incidents", response_model=IncidentResponse, status_code=201)
def create_incident(incident: IncidentCreate):
    if incident.service_id not in services_db:
        raise HTTPException(status_code=404, detail="Service not found")
    
    new_id = str(uuid.uuid4())
    new_incident = {
        "id": new_id,
        "service_id": incident.service_id,
        "severity": incident.severity,
        "summary": incident.summary,
        "status": "active",
        "created_at": datetime.utcnow(),
        "resolved_at": None
    }
    incidents_db[new_id] = new_incident
    
    # Update service status if critical
    if incident.severity in ["critical", "high"]:
        services_db[incident.service_id]["status"] = "Degraded" if incident.severity == "high" else "Down"
    
    return new_incident

@app.get("/api/incidents", response_model=List[IncidentResponse])
def list_incidents(
    status: Optional[str] = Query(None, pattern="^(active|resolved)$"),
    service_id: Optional[str] = None
):
    incidents = list(incidents_db.values())
    
    if status:
        incidents = [i for i in incidents if i["status"] == status]
    
    if service_id:
        incidents = [i for i in incidents if i["service_id"] == service_id]
        
    return incidents

@app.patch("/api/incidents/{incident_id}/resolve", response_model=IncidentResponse)
def resolve_incident(incident_id: str, request: IncidentResolveRequest):
    if incident_id not in incidents_db:
        raise HTTPException(status_code=404, detail="Incident not found")
    
    incident = incidents_db[incident_id]
    
    if incident["status"] == "resolved":
        raise HTTPException(status_code=400, detail="Incident is already resolved")
        
    incident["status"] = "resolved"
    incident["resolved_at"] = datetime.utcnow()
    if request.resolution_notes:
        incident["resolution_notes"] = request.resolution_notes
        
    return incident