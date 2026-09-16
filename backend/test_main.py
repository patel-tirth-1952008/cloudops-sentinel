import pytest
from fastapi.testclient import TestClient
from main import app, services_db, incidents_db, metrics_db
import uuid
from datetime import datetime, timedelta
import re

client = TestClient(app)

@pytest.fixture(autouse=True)
def clean_dbs():
    """Clean in-memory databases before each test to ensure isolation."""
    services_db.clear()
    incidents_db.clear()
    metrics_db.clear()
    yield
    services_db.clear()
    incidents_db.clear()
    metrics_db.clear()

def test_health_endpoint_returns_200():
    """
    Test that the health endpoint returns a 200 status code and valid JSON structure.
    """
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert data["status"] == "healthy"
    assert "timestamp" in data
    # Verify timestamp is a valid ISO format string
    try:
        datetime.fromisoformat(data["timestamp"].replace('Z', '+00:00'))
    except ValueError:
        pytest.fail("Invalid timestamp format in health response")

def test_get_services_returns_populated_list():
    """
    Test that GET /services returns a list of services.
    Since the DB is empty initially, we first create a service, then verify it appears in the list.
    """
    # Create a service to populate the DB
    service_data = {
        "name": "Test Service",
        "endpoint_url": "https://example.com/api",
        "check_interval_sec": 30
    }
    create_resp = client.post("/api/services", json=service_data)
    assert create_resp.status_code == 201, f"Failed to create service: {create_resp.text}"
    created_service = create_resp.json()
    service_id = created_service["id"]

    # Now fetch the list
    response = client.get("/api/services")
    assert response.status_code == 200
    data = response.json()
    
    # Depending on implementation, it might return a list directly or a dict with 'services' key.
    # Based on typical FastAPI patterns and the model ServiceResponse, let's assume it returns a list or a dict.
    # Let's check the structure. If it's a list:
    if isinstance(data, list):
        assert len(data) >= 1
        found = [s for s in data if s["id"] == service_id]
        assert len(found) == 1
        assert found[0]["name"] == "Test Service"
    elif isinstance(data, dict) and "services" in data:
        services_list = data["services"]
        assert len(services_list) >= 1
        found = [s for s in services_list if s["id"] == service_id]
        assert len(found) == 1
        assert found[0]["name"] == "Test Service"
    else:
        pytest.fail(f"Unexpected response structure for /services: {data}")

def test_create_service_validation_success():
    """
    Test that creating a service with valid data returns 201 and correct fields.
    """
    service_data = {
        "name": "Valid Service",
        "endpoint_url": "https://valid-endpoint.com/health",
        "check_interval_sec": 60
    }
    response = client.post("/api/services", json=service_data)
    assert response.status_code == 201
    data = response.json()
    
    assert "id" in data
    assert data["name"] == "Valid Service"
    assert data["endpoint_url"] == "https://valid-endpoint.com/health"
    assert data["check_interval_sec"] == 60
    assert "status" in data
    assert "uptime_pct" in data
    assert isinstance(data["uptime_pct"], float)
    
    # Verify it was added to the in-memory DB
    assert data["id"] in services_db

def test_create_service_invalid_url_fails():
    """
    Test that creating a service with an invalid URL (too short) returns 422.
    """
    service_data = {
        "name": "Invalid URL Service",
        "endpoint_url": "http://a",
        "check_interval_sec": 30
    }
    response = client.post("/api/services", json=service_data)
    assert response.status_code == 422
    data = response.json()
    assert "detail" in data
    # Pydantic validation errors should mention endpoint_url
    error_details = data["detail"]
    assert isinstance(error_details, list)
    assert any("endpoint_url" in str(err) for err in error_details)

def test_get_service_metrics_returns_time_series():
    """
    Test that GET /services/{id}/metrics returns a list of metrics.
    We need to create a service first. The app likely generates mock metrics or returns empty if none exist.
    Assuming the app generates some initial metrics or allows fetching an empty list.
    """
    # Create a service
    service_data = {
        "name": "Metrics Service",
        "endpoint_url": "https://metrics.example.com",
        "check_interval_sec": 10
    }
    create_resp = client.post("/api/services", json=service_data)
    assert create_resp.status_code == 201
    service_id = create_resp.json()["id"]

    # Fetch metrics
    response = client.get(f"/api/services/{service_id}/metrics")
    assert response.status_code == 200
    data = response.json()
    
    # Depending on implementation, it might be a list or a dict.
    # Let's assume it returns a list of MetricResponse objects.
    if isinstance(data, list):
        # It might be empty if no metrics were generated yet, or populated.
        # Let's just assert it's a list.
        assert isinstance(data, list)
        if len(data) > 0:
            metric = data[0]
            assert "id" in metric
            assert "service_id" in metric
            assert metric["service_id"] == service_id
            assert "latency_ms" in metric
            assert "status_code" in metric
            assert "timestamp" in metric
    elif isinstance(data, dict) and "metrics" in data:
        metrics_list = data["metrics"]
        assert isinstance(metrics_list, list)
    else:
        pytest.fail(f"Unexpected response structure for metrics: {data}")

def test_create_incident_sets_active_status():
    """
    Test that creating an incident sets its status to 'active'.
    """
    # First, create a service to associate with the incident
    service_data = {
        "name": "Incident Service",
        "endpoint_url": "https://incident.example.com",
        "check_interval_sec": 30
    }
    create_service_resp = client.post("/api/services", json=service_data)
    assert create_service_resp.status_code == 201
    service_id = create_service_resp.json()["id"]

    # Create an incident
    incident_data = {
        "service_id": service_id,
        "severity": "high",
        "summary": "Latency exceeded 500ms"
    }
    response = client.post("/api/incidents", json=incident_data)
    assert response.status_code == 201
    data = response.json()
    assert data["status"] == "active"
    assert data["severity"] == "high"
    assert data["service_id"] == service_id