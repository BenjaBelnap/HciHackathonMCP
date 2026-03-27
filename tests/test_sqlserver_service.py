"""
Unit tests for SqlServerQueryService.

All database calls are mocked — no real SQL Server connection required.
"""
from unittest.mock import MagicMock, patch

import pytest

from dataObjectQueryService.sql_server_query_service import SqlServerQueryService


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_service(**kwargs) -> SqlServerQueryService:
    defaults = dict(
        host="localhost",
        port=1433,
        username="sa",
        password="SqlPassword123!",
        database="CLARITY",
    )
    defaults.update(kwargs)
    return SqlServerQueryService(**defaults)


def _mock_pymssql(mock_pymssql_mod, fetchall_side_effects: list):
    """
    Prepare a mock pymssql module.  cursor().fetchall() returns successive values.
    """
    mock_conn   = MagicMock()
    mock_cursor = MagicMock()
    mock_conn.cursor.return_value = mock_cursor
    mock_cursor.fetchall.side_effect = fetchall_side_effects
    mock_pymssql_mod.connect.return_value = mock_conn
    return mock_conn, mock_cursor


# ---------------------------------------------------------------------------
# connect / disconnect
# ---------------------------------------------------------------------------

class TestConnect:
    def test_connect_with_database(self):
        svc = _make_service(database="CLARITY")
        with patch("dataObjectQueryService.sql_server_query_service.pymssql") as mock_db:
            mock_db.connect.return_value = MagicMock()
            svc.connect()
            mock_db.connect.assert_called_once_with(
                server="localhost:1433",
                user="sa",
                password="SqlPassword123!",
                database="CLARITY",
            )

    def test_connect_without_database(self):
        svc = _make_service(database=None)
        with patch("dataObjectQueryService.sql_server_query_service.pymssql") as mock_db:
            mock_db.connect.return_value = MagicMock()
            svc.connect()
            call_kwargs = mock_db.connect.call_args.kwargs
            assert "database" not in call_kwargs

    def test_disconnect_closes_connection(self):
        svc = _make_service()
        mock_conn = MagicMock()
        svc.connection = mock_conn
        svc.disconnect()
        mock_conn.close.assert_called_once()
        assert svc.connection is None

    def test_context_manager(self):
        svc = _make_service()
        with patch("dataObjectQueryService.sql_server_query_service.pymssql") as mock_db:
            mock_db.connect.return_value = MagicMock()
            with svc as s:
                assert s is svc
            mock_db.connect.return_value.close.assert_called_once()

    def test_connect_with_windows_auth(self):
        svc = SqlServerQueryService(host="localhost", port=1433, windows_auth=True)
        with patch("dataObjectQueryService.sql_server_query_service.pymssql") as mock_db:
            mock_db.connect.return_value = MagicMock()
            svc.connect()
            call_kwargs = mock_db.connect.call_args.kwargs
            assert call_kwargs.get("trusted_connection") is True
            assert "user" not in call_kwargs
            assert "password" not in call_kwargs

    def test_connect_sql_login_unaffected(self):
        svc = _make_service(windows_auth=False)
        with patch("dataObjectQueryService.sql_server_query_service.pymssql") as mock_db:
            mock_db.connect.return_value = MagicMock()
            svc.connect()
            mock_db.connect.assert_called_once_with(
                server="localhost:1433",
                user="sa",
                password="SqlPassword123!",
                database="CLARITY",
            )


# ---------------------------------------------------------------------------
# list_databases / list_schemas
# ---------------------------------------------------------------------------

class TestListDatabases:
    def test_returns_online_databases(self):
        with patch("dataObjectQueryService.sql_server_query_service.pymssql") as mock_db:
            _mock_pymssql(mock_db, [[("master",), ("CLARITY",), ("tempdb",)]])
            svc = _make_service(database=None)
            svc.connect()
            dbs = svc.list_databases()
        assert dbs == ["master", "CLARITY", "tempdb"]


class TestListSchemas:
    def test_returns_schema_names(self):
        with patch("dataObjectQueryService.sql_server_query_service.pymssql") as mock_db:
            _mock_pymssql(mock_db, [[("dbo",), ("clarity",)]])
            svc = _make_service()
            svc.connect()
            schemas = svc.list_schemas()
        assert schemas == ["dbo", "clarity"]


# ---------------------------------------------------------------------------
# search_objects
# ---------------------------------------------------------------------------

class TestSearchObjects:
    def test_returns_structured_results(self):
        with patch("dataObjectQueryService.sql_server_query_service.pymssql") as mock_db:
            # exact, prefix, substring, extended_props — 4 fetchall calls
            _mock_pymssql(mock_db, [
                [("dbo", "PATIENT", "U ")],   # exact
                [],
                [],
                [],
            ])
            svc = _make_service()
            svc.connect()
            results = svc.search_objects("PATIENT")

        assert len(results) == 1
        r = results[0]
        assert r["schema"]     == "dbo"
        assert r["name"]       == "PATIENT"
        assert r["type"]       == "TABLE"        # 'U' → 'TABLE'
        assert r["match_type"] == "exact"

    def test_view_type_mapped_correctly(self):
        with patch("dataObjectQueryService.sql_server_query_service.pymssql") as mock_db:
            _mock_pymssql(mock_db, [
                [("dbo", "PATIENT_SUMMARY", "V ")],
                [],
                [],
                [],
            ])
            svc = _make_service()
            svc.connect()
            results = svc.search_objects("PATIENT_SUMMARY", object_type="VIEW")

        assert results[0]["type"] == "VIEW"

    def test_deduplicates_across_tiers(self):
        with patch("dataObjectQueryService.sql_server_query_service.pymssql") as mock_db:
            row = ("dbo", "PATIENT", "U ")
            _mock_pymssql(mock_db, [
                [row],   # exact
                [row],   # prefix (dup)
                [row],   # substring (dup)
                [],
            ])
            svc = _make_service()
            svc.connect()
            results = svc.search_objects("PATIENT")

        assert len(results) == 1
        assert results[0]["match_type"] == "exact"

    def test_extended_property_match(self):
        with patch("dataObjectQueryService.sql_server_query_service.pymssql") as mock_db:
            _mock_pymssql(mock_db, [
                [],
                [],
                [],
                [("dbo", "PAT_ENC", "U ")],   # extended props match
            ])
            svc = _make_service()
            svc.connect()
            results = svc.search_objects("encounter")

        assert len(results) == 1
        assert results[0]["match_type"] == "comment"

    def test_raises_on_invalid_object_type(self):
        svc = _make_service()
        with patch("dataObjectQueryService.sql_server_query_service.pymssql") as mock_db:
            mock_db.connect.return_value = MagicMock()
            svc.connect()
        with pytest.raises(ValueError, match="Invalid object_type"):
            svc.search_objects("patient", object_type="NOTATYPE")

    def test_schema_filter_included_in_query(self):
        with patch("dataObjectQueryService.sql_server_query_service.pymssql") as mock_db:
            mock_conn, mock_cursor = _mock_pymssql(mock_db, [[], [], [], []])
            svc = _make_service()
            svc.connect()
            svc.search_objects("PAT", schema="dbo")

        execute_calls = mock_cursor.execute.call_args_list
        # Check that at least one call passes schema as an argument
        any_has_schema = any(
            "dbo" in str(c) for c in execute_calls
        )
        assert any_has_schema


# ---------------------------------------------------------------------------
# describe_object
# ---------------------------------------------------------------------------

class TestDescribeObject:
    _COLUMNS = [
        ("PAT_ID",   "int",     4,   10, 0, False, 1),
        ("PAT_NAME", "varchar", 100, 0,  0, True,  2),
    ]

    def test_returns_formatted_output(self):
        with patch("dataObjectQueryService.sql_server_query_service.pymssql") as mock_db:
            _mock_pymssql(mock_db, [self._COLUMNS])
            svc = _make_service()
            svc.connect()
            result = svc.describe_object("PATIENT")

        assert "PAT_ID" in result
        assert "PAT_NAME" in result
        assert "NOT NULL" in result

    def test_parses_schema_qualified_name(self):
        with patch("dataObjectQueryService.sql_server_query_service.pymssql") as mock_db:
            _mock_pymssql(mock_db, [self._COLUMNS])
            svc = _make_service()
            svc.connect()
            result = svc.describe_object("dbo.PATIENT")

        assert "PAT_ID" in result

    def test_returns_not_found_for_missing_object(self):
        with patch("dataObjectQueryService.sql_server_query_service.pymssql") as mock_db:
            _mock_pymssql(mock_db, [[]])
            svc = _make_service()
            svc.connect()
            result = svc.describe_object("NONEXISTENT")

        assert "not found" in result.lower()

    def test_nvarchar_divides_max_length_by_two(self):
        columns = [("LABEL", "nvarchar", 200, 0, 0, True, 1)]
        with patch("dataObjectQueryService.sql_server_query_service.pymssql") as mock_db:
            _mock_pymssql(mock_db, [columns])
            svc = _make_service()
            svc.connect()
            result = svc.describe_object("SOME_TABLE")

        # nvarchar with max_length=200 bytes → 100 chars
        assert "nvarchar(100)" in result.lower()

    def test_nvarchar_max_shown_as_max(self):
        columns = [("BODY", "nvarchar", -1, 0, 0, True, 1)]
        with patch("dataObjectQueryService.sql_server_query_service.pymssql") as mock_db:
            _mock_pymssql(mock_db, [columns])
            svc = _make_service()
            svc.connect()
            result = svc.describe_object("SOME_TABLE")

        assert "nvarchar(MAX)" in result or "nvarchar(max)" in result.lower()

    def test_decimal_includes_precision_and_scale(self):
        columns = [("AMOUNT", "decimal", 9, 10, 2, False, 1)]
        with patch("dataObjectQueryService.sql_server_query_service.pymssql") as mock_db:
            _mock_pymssql(mock_db, [columns])
            svc = _make_service()
            svc.connect()
            result = svc.describe_object("SOME_TABLE")

        assert "decimal(10,2)" in result.lower()
