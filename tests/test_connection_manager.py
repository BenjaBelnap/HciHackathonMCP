"""
Unit tests for ConnectionManager.

Uses a temporary servers.json file (via tmp_path fixture) so no real
database or config file is required.
"""
import json
import os
from unittest.mock import patch

import pytest

from dataObjectQueryService.connection_manager import ConnectionManager, ServerNotFoundError
from dataObjectQueryService.oracle_query_service import OracleQueryService
from dataObjectQueryService.sql_server_query_service import SqlServerQueryService


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

ORACLE_CFG = {
    "type":         "oracle",
    "host":         "db-oracle.example.com",
    "port":         1521,
    "service_name": "MYDB",
    "username":     "user1",
    "password":     "pass1",
}

SQLSERVER_CFG = {
    "type":     "sqlserver",
    "host":     "db-sql.example.com",
    "port":     1433,
    "username": "sa",
    "password": "SqlPass!",
}


@pytest.fixture
def config_file(tmp_path):
    """Write a minimal servers.json to a temp directory and return its path."""
    cfg = {
        "servers": {
            "oracle-test":    ORACLE_CFG,
            "sqlserver-test": SQLSERVER_CFG,
        }
    }
    path = tmp_path / "servers.json"
    path.write_text(json.dumps(cfg), encoding="utf-8")
    return str(path)


@pytest.fixture
def manager(config_file):
    return ConnectionManager(config_path=config_file)


# ---------------------------------------------------------------------------
# Config loading
# ---------------------------------------------------------------------------

class TestConfigLoading:
    def test_loads_servers(self, manager):
        names = {s["name"] for s in manager.list_servers()}
        assert "oracle-test"    in names
        assert "sqlserver-test" in names

    def test_raises_if_file_missing(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            ConnectionManager(config_path=str(tmp_path / "does_not_exist.json"))

    def test_env_var_override_string(self, config_file, monkeypatch):
        monkeypatch.setenv("DB_SERVER_ORACLE_TEST_PASSWORD", "overridden_pass")
        m = ConnectionManager(config_path=config_file)
        # We can't read _servers directly in a clean way, but get_service should use it
        with (
            patch("dataObjectQueryService.oracle_query_service.oracledb") as mock_db,
        ):
            mock_db.makedsn.return_value = "dsn"
            mock_db.connect.return_value = __import__("unittest.mock", fromlist=["MagicMock"]).MagicMock()
            svc = m.get_service("oracle-test")
            assert svc.password == "overridden_pass"

    def test_env_var_override_integer_port(self, config_file, monkeypatch):
        monkeypatch.setenv("DB_SERVER_ORACLE_TEST_PORT", "1600")
        m = ConnectionManager(config_path=config_file)
        svc = m.get_service("oracle-test")
        assert isinstance(svc.port, int)
        assert svc.port == 1600


# ---------------------------------------------------------------------------
# list_servers
# ---------------------------------------------------------------------------

class TestListServers:
    def test_returns_all_servers(self, manager):
        servers = manager.list_servers()
        assert len(servers) == 2

    def test_server_has_name_and_type(self, manager):
        for s in manager.list_servers():
            assert "name" in s
            assert "type" in s

    def test_types_are_correct(self, manager):
        by_name = {s["name"]: s["type"] for s in manager.list_servers()}
        assert by_name["oracle-test"]    == "oracle"
        assert by_name["sqlserver-test"] == "sqlserver"


# ---------------------------------------------------------------------------
# get_server_type
# ---------------------------------------------------------------------------

class TestGetServerType:
    def test_oracle_type(self, manager):
        assert manager.get_server_type("oracle-test") == "oracle"

    def test_sqlserver_type(self, manager):
        assert manager.get_server_type("sqlserver-test") == "sqlserver"

    def test_raises_for_unknown_server(self, manager):
        with pytest.raises(ServerNotFoundError):
            manager.get_server_type("does-not-exist")


# ---------------------------------------------------------------------------
# get_service
# ---------------------------------------------------------------------------

class TestGetService:
    def test_oracle_returns_oracle_service(self, manager):
        svc = manager.get_service("oracle-test")
        assert isinstance(svc, OracleQueryService)

    def test_oracle_service_has_correct_params(self, manager):
        svc = manager.get_service("oracle-test")
        assert svc.host         == ORACLE_CFG["host"]
        assert svc.service_name == ORACLE_CFG["service_name"]
        assert svc.username     == ORACLE_CFG["username"]

    def test_sqlserver_returns_sqlserver_service(self, manager):
        svc = manager.get_service("sqlserver-test")
        assert isinstance(svc, SqlServerQueryService)

    def test_sqlserver_service_has_correct_params(self, manager):
        svc = manager.get_service("sqlserver-test")
        assert svc.host     == SQLSERVER_CFG["host"]
        assert svc.username == SQLSERVER_CFG["username"]

    def test_sqlserver_database_forwarded(self, manager):
        svc = manager.get_service("sqlserver-test", database="CLARITY")
        assert isinstance(svc, SqlServerQueryService)
        assert svc.database == "CLARITY"

    def test_oracle_database_param_ignored(self, manager):
        """Oracle service is returned regardless of what database is passed."""
        svc = manager.get_service("oracle-test", database="IGNORED")
        assert isinstance(svc, OracleQueryService)

    def test_raises_for_unknown_server(self, manager):
        with pytest.raises(ServerNotFoundError, match="not configured"):
            manager.get_service("nonexistent-server")

    def test_raises_for_unsupported_type(self, tmp_path):
        cfg = {"servers": {"bad-server": {"type": "mysql", "host": "localhost",
                                          "username": "u", "password": "p"}}}
        p = tmp_path / "servers.json"
        p.write_text(json.dumps(cfg))
        m = ConnectionManager(config_path=str(p))
        with pytest.raises(ValueError, match="Unsupported server type"):
            m.get_service("bad-server")
