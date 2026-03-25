"""
Unit tests for OracleQueryService.

All database calls are mocked — no real Oracle connection required.
"""
from unittest.mock import MagicMock, patch, call

import pytest

from dataObjectQueryService.oracle_query_service import OracleQueryService


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_service(**kwargs) -> OracleQueryService:
    defaults = dict(
        host="localhost",
        port=1521,
        service_name="XEPDB1",
        username="CLARITY",
        password="Clarity123",
    )
    defaults.update(kwargs)
    return OracleQueryService(**defaults)


def _mock_oracle(mock_oracledb, fetchall_side_effects: list):
    """
    Prepare a mock oracledb module whose cursor().fetchall() returns
    successive values from *fetchall_side_effects*.
    """
    mock_conn   = MagicMock()
    mock_cursor = MagicMock()
    mock_conn.cursor.return_value = mock_cursor
    mock_cursor.fetchall.side_effect = fetchall_side_effects
    mock_oracledb.makedsn.return_value = "fake_dsn"
    mock_oracledb.connect.return_value = mock_conn
    return mock_conn, mock_cursor


# ---------------------------------------------------------------------------
# connect / disconnect
# ---------------------------------------------------------------------------

class TestConnect:
    def test_connect_calls_oracledb(self):
        svc = _make_service()
        with patch("dataObjectQueryService.oracle_query_service.oracledb") as mock_db:
            mock_db.makedsn.return_value = "dsn"
            mock_db.connect.return_value = MagicMock()
            svc.connect()
            mock_db.makedsn.assert_called_once_with("localhost", 1521, service_name="XEPDB1")
            mock_db.connect.assert_called_once()

    def test_disconnect_closes_connection(self):
        svc = _make_service()
        mock_conn = MagicMock()
        svc.connection = mock_conn
        svc.disconnect()
        mock_conn.close.assert_called_once()
        assert svc.connection is None

    def test_context_manager(self):
        svc = _make_service()
        with patch("dataObjectQueryService.oracle_query_service.oracledb") as mock_db:
            mock_db.makedsn.return_value = "dsn"
            mock_db.connect.return_value = MagicMock()
            with svc as s:
                assert s is svc
            mock_db.connect.return_value.close.assert_called_once()


# ---------------------------------------------------------------------------
# list_databases / list_schemas
# ---------------------------------------------------------------------------

class TestListDatabases:
    def test_list_databases_returns_empty_list(self):
        """Oracle does not have the database concept — always []."""
        svc = _make_service()
        assert svc.list_databases() == []


class TestListSchemas:
    def test_list_schemas_queries_all_objects(self):
        svc = _make_service()
        with patch("dataObjectQueryService.oracle_query_service.oracledb") as mock_db:
            _mock_oracle(mock_db, [
                [("CLARITY",), ("SYS",), ("SYSTEM",)],
            ])
            svc.connect()
            schemas = svc.list_schemas()
        assert schemas == ["CLARITY", "SYS", "SYSTEM"]


# ---------------------------------------------------------------------------
# search_objects
# ---------------------------------------------------------------------------

class TestSearchObjects:
    def _run_search(self, mock_db, pattern, **kwargs):
        svc = _make_service()
        svc.connect()
        return svc.search_objects(pattern, **kwargs)

    def test_returns_structured_results(self):
        with patch("dataObjectQueryService.oracle_query_service.oracledb") as mock_db:
            # exact, prefix, substring, + 2 comment queries (tab + col) — 5 fetchall calls
            _mock_oracle(mock_db, [
                [("CLARITY", "PATIENT", "TABLE")],   # exact
                [],                                   # prefix  (already seen)
                [],                                   # substring (already seen)
                [],                                   # tab comments
                [],                                   # col comments
            ])
            svc = _make_service()
            svc.connect()
            results = svc.search_objects("PATIENT")

        assert len(results) == 1
        r = results[0]
        assert r["schema"] == "CLARITY"
        assert r["name"]   == "PATIENT"
        assert r["type"]   == "TABLE"
        assert r["match_type"] == "exact"

    def test_deduplicates_across_match_tiers(self):
        with patch("dataObjectQueryService.oracle_query_service.oracledb") as mock_db:
            # Same row appears in exact AND prefix — should only appear once
            row = ("CLARITY", "PATIENT", "TABLE")
            _mock_oracle(mock_db, [
                [row],   # exact
                [row],   # prefix (duplicate)
                [row],   # substring (duplicate)
                [],
                [],
            ])
            svc = _make_service()
            svc.connect()
            results = svc.search_objects("PATIENT")

        assert len(results) == 1
        assert results[0]["match_type"] == "exact"

    def test_comment_match_added_after_name_matches(self):
        with patch("dataObjectQueryService.oracle_query_service.oracledb") as mock_db:
            _mock_oracle(mock_db, [
                [],   # exact — no name match
                [],   # prefix
                [],   # substring
                [("CLARITY", "PAT_ENC", "TABLE")],  # table comment match
                [],
            ])
            svc = _make_service()
            svc.connect()
            results = svc.search_objects("encounter")

        assert len(results) == 1
        assert results[0]["match_type"] == "comment"
        assert results[0]["name"] == "PAT_ENC"

    def test_multiple_results_ordered_by_tier(self):
        with patch("dataObjectQueryService.oracle_query_service.oracledb") as mock_db:
            _mock_oracle(mock_db, [
                [("CLARITY", "PATIENT", "TABLE")],              # exact
                [("CLARITY", "PAT_ENC", "TABLE")],              # prefix
                [("CLARITY", "INPATIENT_VISIT", "TABLE")],      # substring
                [],
                [],
            ])
            svc = _make_service()
            svc.connect()
            results = svc.search_objects("PAT")

        assert results[0]["match_type"] == "exact"
        assert results[1]["match_type"] == "prefix"
        assert results[2]["match_type"] == "substring"

    def test_raises_on_invalid_object_type(self):
        svc = _make_service()
        with patch("dataObjectQueryService.oracle_query_service.oracledb") as mock_db:
            mock_db.makedsn.return_value = "dsn"
            mock_db.connect.return_value = MagicMock()
            svc.connect()
        with pytest.raises(ValueError, match="Invalid object_type"):
            svc.search_objects("patient", object_type="BANANA")

    def test_schema_filter_applies(self):
        with patch("dataObjectQueryService.oracle_query_service.oracledb") as mock_db:
            mock_conn, mock_cursor = _mock_oracle(mock_db, [[], [], [], [], []])
            svc = _make_service()
            svc.connect()
            svc.search_objects("PAT", schema="CLARITY")

        # Verify :schema was passed in one of the execute calls
        calls = mock_cursor.execute.call_args_list
        any_has_schema = any(
            "schema" in str(c) for c in calls
        )
        assert any_has_schema


# ---------------------------------------------------------------------------
# describe_object
# ---------------------------------------------------------------------------

class TestDescribeObject:
    _COLUMNS = [
        ("PAT_ID",   "N", "NUMBER",   22, 10, 0),
        ("PAT_NAME", "Y", "VARCHAR2", 100, None, None),
    ]

    def test_returns_formatted_output(self):
        with patch("dataObjectQueryService.oracle_query_service.oracledb") as mock_db:
            _mock_oracle(mock_db, [self._COLUMNS])
            svc = _make_service()
            svc.connect()
            result = svc.describe_object("PATIENT", schema="CLARITY")

        assert "PAT_ID" in result
        assert "PAT_NAME" in result
        assert "NOT NULL" in result

    def test_parses_schema_qualified_name(self):
        with patch("dataObjectQueryService.oracle_query_service.oracledb") as mock_db:
            _mock_oracle(mock_db, [self._COLUMNS])
            svc = _make_service()
            svc.connect()
            result = svc.describe_object("CLARITY.PATIENT")

        assert "PAT_ID" in result

    def test_returns_not_found_for_missing_object(self):
        with patch("dataObjectQueryService.oracle_query_service.oracledb") as mock_db:
            _mock_oracle(mock_db, [[]])   # no rows returned
            svc = _make_service()
            svc.connect()
            result = svc.describe_object("NONEXISTENT")

        assert "not found" in result.lower()

    def test_number_with_scale_formatted_correctly(self):
        columns = [("AMOUNT", "N", "NUMBER", 22, 10, 2)]
        with patch("dataObjectQueryService.oracle_query_service.oracledb") as mock_db:
            _mock_oracle(mock_db, [columns])
            svc = _make_service()
            svc.connect()
            result = svc.describe_object("SOME_TABLE")

        assert "NUMBER(10,2)" in result

    def test_varchar2_type_includes_length(self):
        columns = [("NAME", "Y", "VARCHAR2", 100, None, None)]
        with patch("dataObjectQueryService.oracle_query_service.oracledb") as mock_db:
            _mock_oracle(mock_db, [columns])
            svc = _make_service()
            svc.connect()
            result = svc.describe_object("SOME_TABLE")

        assert "VARCHAR2(100)" in result
