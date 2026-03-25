"""
Connection Manager

Loads multi-server configuration from servers.json and instantiates
the appropriate DatabaseQueryService for each named server.

Config file format (src/config/servers.json):
{
    "servers": {
        "oracle-local": {
            "type": "oracle",
            "host": "localhost",
            "port": 1521,
            "service_name": "XEPDB1",
            "username": "CLARITY",
            "password": "Clarity123"
        },
        "sqlserver-local": {
            "type": "sqlserver",
            "host": "localhost",
            "port": 1433,
            "username": "sa",
            "password": "SqlPassword123!"
        }
    }
}

Environment variable overrides:
    DB_SERVER_<NAME_UPPER>_<FIELD_UPPER>
    e.g. DB_SERVER_ORACLE_LOCAL_PASSWORD=secret
         DB_SERVER_SQLSERVER_LOCAL_HOST=prod-db.example.com
    (hyphens in server names are converted to underscores for env var lookup)
"""
import json
import os
from typing import Optional

from .database_query_service import DatabaseQueryService
from .oracle_query_service import OracleQueryService
from .sql_server_query_service import SqlServerQueryService


class ServerNotFoundError(KeyError):
    """Raised when a requested server name is not in the configuration."""


class ConnectionManager:
    """Manages multiple named database server configurations."""

    # Default path: two levels up from this file → src/config/servers.json
    DEFAULT_CONFIG_PATH = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "..", "..", "config", "servers.json",
    )

    def __init__(self, config_path: Optional[str] = None):
        path = os.path.abspath(config_path or self.DEFAULT_CONFIG_PATH)
        self._servers = self._load_config(path)

    # ------------------------------------------------------------------ #
    # Config loading                                                       #
    # ------------------------------------------------------------------ #

    def _load_config(self, path: str) -> dict:
        with open(path, encoding="utf-8") as fh:
            raw = json.load(fh)

        servers: dict = raw.get("servers", {})

        # Apply environment-variable overrides
        for name, cfg in servers.items():
            env_prefix = "DB_SERVER_" + name.upper().replace("-", "_") + "_"
            for key in list(cfg.keys()):
                env_var = env_prefix + key.upper()
                if env_var in os.environ:
                    val = os.environ[env_var]
                    # Preserve integer types (e.g. port)
                    cfg[key] = int(val) if isinstance(cfg[key], int) else val

        return servers

    # ------------------------------------------------------------------ #
    # Public API                                                           #
    # ------------------------------------------------------------------ #

    def list_servers(self) -> list[dict]:
        """Return a list of ``{"name": ..., "type": ...}`` dicts for all configured servers."""
        return [
            {"name": name, "type": cfg["type"]}
            for name, cfg in self._servers.items()
        ]

    def get_server_type(self, server_name: str) -> str:
        """Return the type string ('oracle' | 'sqlserver') for *server_name*."""
        self._require_server(server_name)
        return self._servers[server_name]["type"]

    def get_service(
        self, server_name: str, database: Optional[str] = None
    ) -> DatabaseQueryService:
        """
        Instantiate and return the appropriate :class:`DatabaseQueryService`.

        For SQL Server, *database* sets the initial database context.
        For Oracle, *database* is silently ignored (Oracle uses schemas, not databases).
        """
        self._require_server(server_name)
        cfg = dict(self._servers[server_name])
        server_type = cfg.pop("type")

        if server_type == "oracle":
            return OracleQueryService(
                host=cfg["host"],
                port=int(cfg.get("port", 1521)),
                service_name=cfg["service_name"],
                username=cfg["username"],
                password=cfg["password"],
            )
        elif server_type == "sqlserver":
            return SqlServerQueryService(
                host=cfg["host"],
                port=int(cfg.get("port", 1433)),
                username=cfg["username"],
                password=cfg["password"],
                database=database,
            )
        else:
            raise ValueError(
                f"Unsupported server type '{server_type}' for server '{server_name}'."
            )

    # ------------------------------------------------------------------ #
    # Helpers                                                              #
    # ------------------------------------------------------------------ #

    def _require_server(self, server_name: str) -> None:
        if server_name not in self._servers:
            available = list(self._servers.keys())
            raise ServerNotFoundError(
                f"Server '{server_name}' is not configured. "
                f"Available servers: {available}"
            )
