import pytest
from fastapi.testclient import TestClient
from main import app
import uuid
from datetime import datetime, timedelta

client = TestClient(app)


def test_health_endpoint_returns_200():
    """Test that the health endpoint returns a 200 status code and expected payload."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert data["status"] == "healthy"
    assert "version" in data
    assert data["version"] == "1.0.0"


def test_get_services_returns_populated_list():
    """Test that GET /services returns a list of services after creating some."""
    # Create a service first
    service_data = {
        "name": "Test Service",
        "endpoint_url": "https://example.com/health",
        "check_interval_sec": 30
    }
    create_response = client.post("/services", json=service_data)
    assert create_response.status_code == 201

    # Now fetch all services
    response = client.get("/services")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 1
    # Check that the created service is in the list
    service_ids = [s["id"] for s in data]
    created_id = create_response.json()["id"]
    assert created_id in service_ids


def test_create_service_validation_success():
    """Test that creating a valid service returns 201 and correct data."""
    service_data = {
        "name": "Valid Service",
        "endpoint_url": "https://api.example.com/status",
        "check_interval_sec": 60
    }
    response = client.post("/services", json=service_data)
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Valid Service"
    assert data["endpoint_url"] == "https://api.example.com/status"
    assert data["check_interval_sec"] == 60
    assert "id" in data
    assert data["status"] in ["healthy", "degraded", "down"]
    assert "uptime_pct" in data
    assert isinstance(data["uptime_pct"], float)


def test_create_service_invalid_url_fails():
    """Test that creating a service with an invalid URL (too short) returns 422."""
    service_data = {
        "name": "Bad Service",
        "endpoint_url": "",  # Empty string, min_length=1
        "check_interval_sec": 30
    }
    response = client.post("/services", json=service_data)
    assert response.status_code == 422
    data = response.json()
    assert "detail" in data


def test_get_service_metrics_returns_time_series():
    """Test that GET /services/{id}/metrics returns a list of metric data points."""
    # Create a service
    service_data = {
        "name": "Metrics Service",
        "endpoint_url": "https://metrics.example.com",
        "check_interval_sec": 10
    }
    create_response = client.post("/services", json=service_data)
    assert create_response.status_code == 201
    service_id = create_response.json()["id"]

    # Fetch metrics
    response = client.get(f"/services/{service_id}/metrics")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    # Each metric should have expected fields
    if len(data) > 0:
        metric = data[0]
        assert "id" in metric
        assert metric["service_id"] == service_id
        assert "latency_ms" in metric
        assert "status_code" in metric
        assert "timestamp" in metric
        assert isinstance(metric["latency_ms"], float)
        assert isinstance(metric["status_code"], int)


def test_create_incident_sets_active_status():
    """Test that creating an incident sets its status to 'active'."""
    # Create a service first
    service_data = {
        "name": "Incident Service",
        "endpoint_url": "https://incident.example.com",
        "check_interval_sec": 15
    }
    create_response = client.post("/services", json=service_data)
    assert create_response.status_code == 201
    service_id = create_response.json()["id"]

    # Create an incident
    incident_data = {
        "service_id": service_id,
        "severity": "high"
    }
    response = client.post("/incidents", json=incident_data)
    assert response.status_code == 201
    data = response.json()
    assert data["service_id"] == service_id
    assert data["severity"] == "high"
    assert data["status"] == "active"
    assert "id" in data
    assert "created_at" in data


def test_resolve_incident_updates_timestamp():
    """Test that resolving an incident updates the resolved_at timestamp."""
    # Create a service
    service_data = {
        "name": "Resolve Service",
        "endpoint_url": "https://resolve.example.com",
        "check_interval_sec": 20
    }
    create_response = client.post("/services", json=service_data)
    assert create_response.status_code == 201
    service_id = create_response.json()["id"]

    # Create an incident
    incident_data = {
        "service_id": service_id,
        "severity": "medium"
    }
    incident_response = client.post("/incidents", json=incident_data)
    assert incident_response.status_code == 201
    incident_id = incident_response.json()["id"]

    # Resolve the incident
    response = client.patch(f"/incidents/{incident_id}/resolve")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "resolved"
    assert "resolved_at" in data
    assert data["resolved_at"] is not None
    # Verify the timestamp is a valid datetime string
    datetime.fromisoformat(data["resolved_at"].replace("Z", "+00:00"))


def test_get_incidents_filter_by_status():
    """Test that GET /incidents supports filtering by status query parameter."""
    # Create a service
    service_data = {
        "name": "Filter Service",
        "endpoint_url": "https://filter.example.com",
        "check_interval_sec": 25
    }
    create_response = client.post("/services", json=service_data)
    assert create_response.status_code == 201
    service_id = create_response.json()["id"]

    # Create an active incident
    incident_data = {
        "service_id": service_id,
        "severity": "low"
    }
    incident_response = client.post("/incidents", json=incident_data)
    assert incident_response.status_code == 201
    incident_id = incident_response.json()["id"]

    # Filter by active status
    response = client.get("/incidents", params={"status": "active"})
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    # The active incident should be in the list
    incident_ids = [i["id"] for i in data]
    assert incident_id in incident_ids

    # Filter by resolved status (should not include the active incident)
    response_resolved = client.get("/incidents", params={"status": "resolved"})
    assert response_resolved.status_code == 200
    data_resolved = response_resolved.json()
    assert isinstance(data_resolved, list)
    resolved_ids = [i["id"] for i in data_resolved]
    assert incident_id not in resolved_ids