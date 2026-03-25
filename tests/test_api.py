"""
API integration tests for the OpenAPI tool server.

Uses FastAPI's TestClient with the ConnectionManager dependency overridden
by a mock — no real database connections required.
"""
import json
import os
import sys
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

# server.py is added to sys.path via conftest.py
import server as api_module
from server import app, get_manager


# ---------------------------------------------------------------------------
# Shared mock data
# ---------------------------------------------------------------------------

_SERVERS = [
    {"name": "oracle-local",    "type": "oracle"},
    {"name": "sqlserver-local", "type": "sqlserver"},
]

_SEARCH_ROWS = [
    {"schema": "CLARITY", "name": "PATIENT",           "type": "TABLE",  "match_type": "exact"},
    {"schema": "CLARITY", "name": "PAT_ENC",            "type": "TABLE",  "match_type": "prefix"},
    {"schema": "CLARITY", "name": "INPATIENT_VISIT",    "type": "TABLE",  "match_type": "substring"},
]

_DESCRIBE_RESULT = (
    "Name                           Null?    Type\n"
    "------------------------------- -------- ----------------------------\n"
    "PAT_ID                          NOT NULL NUMBER(10)\n"
    "PAT_NAME                                 VARCHAR2(100)\n"
)

_DATABASES = ["master", "CLARITY", "tempdb"]


# ---------------------------------------------------------------------------
# Fixture — inject mock manager into app
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_manager():
    from dataObjectQueryService.connection_manager import ServerNotFoundError as _SNF

    _server_types = {
        "oracle-local":    "oracle",
        "sqlserver-local": "sqlserver",
    }

    def _get_type(name):
        if name not in _server_types:
            raise _SNF(f"Server '{name}' not configured.")
        return _server_types[name]

    m = MagicMock()
    m.list_servers.return_value = _SERVERS
    m.get_server_type.side_effect = _get_type

    mock_service = MagicMock()
    mock_service.search_objects.return_value = _SEARCH_ROWS
    mock_service.describe_object.return_value = _DESCRIBE_RESULT
    mock_service.list_databases.return_value = _DATABASES
    mock_service.list_schemas.return_value = ["dbo", "CLARITY"]

    m.get_service.return_value = mock_service
    return m


@pytest.fixture
def client(mock_manager):
    app.dependency_overrides[get_manager] = lambda: mock_manager
    yield TestClient(app)
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Info / Discovery endpoints
# ---------------------------------------------------------------------------

class TestInfoEndpoints:
    def test_root_returns_200(self, client):
        resp = client.get("/")
        assert resp.status_code == 200
        data = resp.json()
        assert "docs" in data

    def test_health_returns_healthy(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "healthy"

    def test_get_servers_returns_all(self, client):
        resp = client.get("/servers")
        assert resp.status_code == 200
        servers = resp.json()
        assert len(servers) == 2
        names = {s["name"] for s in servers}
        assert "oracle-local"    in names
        assert "sqlserver-local" in names

    def test_get_databases(self, client, mock_manager):
        mock_manager.get_server_type.side_effect = None
        mock_manager.get_server_type.return_value = "sqlserver"
        resp = client.get("/servers/sqlserver-local/databases")
        assert resp.status_code == 200
        data = resp.json()
        assert "databases" in data

    def test_get_schemas(self, client, mock_manager):
        mock_manager.get_server_type.side_effect = None
        mock_manager.get_server_type.return_value = "oracle"
        resp = client.get("/servers/oracle-local/schemas")
        assert resp.status_code == 200
        data = resp.json()
        assert "schemas" in data

    def test_get_oracle_databases_returns_advisory_note(self, client, mock_manager):
        mock_manager.get_server_type.side_effect = None
        mock_manager.get_server_type.return_value = "oracle"
        resp = client.get("/servers/oracle-local/databases")
        assert resp.status_code == 200
        data = resp.json()
        assert data["type"] == "oracle"
        assert data["databases"] == []
        assert "note" in data


# ---------------------------------------------------------------------------
# POST /search_objects
# ---------------------------------------------------------------------------

class TestSearchObjects:
    def test_no_server_returns_available_servers(self, client):
        resp = client.post("/search_objects", json={"pattern": "patient"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["available_servers"] is not None
        assert len(data["available_servers"]) == 2
        assert data["objects"] is None
        assert "message" in data

    def test_sqlserver_no_database_returns_available_databases(self, client, mock_manager):
        resp = client.post(
            "/search_objects",
            json={"pattern": "patient", "server": "sqlserver-local"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["available_databases"] is not None
        assert "CLARITY" in data["available_databases"]
        assert "message" in data

    def test_oracle_without_database_returns_results(self, client, mock_manager):
        """Oracle doesn't need a database — should return results directly."""
        resp = client.post(
            "/search_objects",
            json={"pattern": "patient", "server": "oracle-local"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["objects"] is not None
        assert data["count"] == 3

    def test_full_params_returns_results(self, client, mock_manager):
        mock_manager.get_server_type.side_effect = None
        mock_manager.get_server_type.return_value = "sqlserver"
        resp = client.post(
            "/search_objects",
            json={"pattern": "patient", "server": "sqlserver-local", "database": "CLARITY"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["objects"] is not None
        assert data["count"] == 3
        assert data["server"]   == "sqlserver-local"
        assert data["database"] == "CLARITY"

    def test_results_have_match_type(self, client):
        resp = client.post(
            "/search_objects",
            json={"pattern": "patient", "server": "oracle-local"},
        )
        assert resp.status_code == 200
        for obj in resp.json()["objects"]:
            assert "match_type" in obj
            assert "full_name"  in obj

    def test_unknown_server_returns_404(self, client, mock_manager):
        from dataObjectQueryService.connection_manager import ServerNotFoundError
        mock_manager.get_server_type.side_effect = ServerNotFoundError("not found")
        resp = client.post(
            "/search_objects",
            json={"pattern": "test", "server": "no-such-server"},
        )
        assert resp.status_code == 404

    def test_invalid_object_type_returns_422(self, client, mock_manager):
        mock_manager.get_server_type.side_effect = None
        mock_manager.get_server_type.return_value = "oracle"
        mock_service = mock_manager.get_service.return_value
        mock_service.search_objects.side_effect = ValueError("Invalid object_type")
        resp = client.post(
            "/search_objects",
            json={"pattern": "t", "server": "oracle-local", "object_type": "BANANA"},
        )
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# POST /describe_object
# ---------------------------------------------------------------------------

class TestDescribeObject:
    def test_no_server_returns_available_servers(self, client):
        resp = client.post("/describe_object", json={"object_name": "PATIENT"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["available_servers"] is not None

    def test_sqlserver_no_database_returns_available_databases(self, client, mock_manager):
        resp = client.post(
            "/describe_object",
            json={"object_name": "PATIENT", "server": "sqlserver-local"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["available_databases"] is not None

    def test_returns_column_description(self, client, mock_manager):
        mock_manager.get_server_type.side_effect = None
        mock_manager.get_server_type.return_value = "oracle"
        resp = client.post(
            "/describe_object",
            json={"object_name": "PATIENT", "server": "oracle-local"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "PAT_ID" in data["result"]

    def test_schema_qualified_name_accepted(self, client, mock_manager):
        mock_manager.get_server_type.side_effect = None
        mock_manager.get_server_type.return_value = "oracle"
        resp = client.post(
            "/describe_object",
            json={"object_name": "CLARITY.PATIENT", "server": "oracle-local"},
        )
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# POST /search_and_describe
# ---------------------------------------------------------------------------

class TestSearchAndDescribe:
    def test_no_server_returns_available_servers(self, client):
        resp = client.post("/search_and_describe", json={"pattern": "patient"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["available_servers"] is not None

    def test_returns_search_results_and_descriptions(self, client, mock_manager):
        mock_manager.get_server_type.side_effect = None
        mock_manager.get_server_type.return_value = "oracle"
        resp = client.post(
            "/search_and_describe",
            json={"pattern": "patient", "server": "oracle-local"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["objects"]      is not None
        assert data["descriptions"] is not None
        # Only first match described by default
        assert len(data["descriptions"]) == 1

    def test_describe_all_flag(self, client, mock_manager):
        mock_manager.get_server_type.side_effect = None
        mock_manager.get_server_type.return_value = "oracle"
        resp = client.post(
            "/search_and_describe",
            json={"pattern": "patient", "server": "oracle-local", "describe_all": True},
        )
        assert resp.status_code == 200
        data = resp.json()
        # describe_all=True → all 3 results described
        assert len(data["descriptions"]) == 3

    def test_sqlserver_no_database_returns_guidance(self, client, mock_manager):
        resp = client.post(
            "/search_and_describe",
            json={"pattern": "patient", "server": "sqlserver-local"},
        )
        assert resp.status_code == 200
        assert resp.json()["available_databases"] is not None
