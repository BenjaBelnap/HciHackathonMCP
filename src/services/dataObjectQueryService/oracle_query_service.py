"""
Oracle Database Query Service

Queries Oracle data-dictionary views to return object metadata.
Uses oracledb thin-mode — no Oracle Client installation required.
"""
from typing import Optional

import oracledb

from .database_query_service import DatabaseQueryService

# Object types accepted for the object_type filter
_ALLOWED_ORACLE_TYPES = {
    "TABLE", "VIEW", "SEQUENCE", "PROCEDURE", "FUNCTION",
    "PACKAGE", "INDEX", "SYNONYM", "TRIGGER", "TYPE",
}


class OracleQueryService(DatabaseQueryService):
    """Queries Oracle database object metadata."""

    def __init__(
        self,
        host: str,
        username: str,
        password: str,
        service_name: str,
        port: int = 1521,
    ):
        self.host = host
        self.port = int(port)
        self.username = username
        self.password = password
        self.service_name = service_name
        self.connection = None
    
    # ------------------------------------------------------------------ #
    # Connection management                                                #
    # ------------------------------------------------------------------ #

    def connect(self) -> None:
        dsn = oracledb.makedsn(self.host, self.port, service_name=self.service_name)
        self.connection = oracledb.connect(
            user=self.username,
            password=self.password,
            dsn=dsn,
        )

    def disconnect(self) -> None:
        if self.connection:
            self.connection.close()
            self.connection = None

    # ------------------------------------------------------------------ #
    # Discovery                                                            #
    # ------------------------------------------------------------------ #

    def list_databases(self) -> list[str]:
        """Oracle does not use the database/catalog concept. Always returns []."""
        return []

    def list_schemas(self) -> list[str]:
        """List all Oracle schemas that own at least one object."""
        if not self.connection:
            self.connect()
        cursor = self.connection.cursor()
        cursor.execute(
            "SELECT DISTINCT owner FROM all_objects ORDER BY owner"
        )
        schemas = [row[0] for row in cursor.fetchall()]
        cursor.close()
        return schemas

    # ------------------------------------------------------------------ #
    # Search                                                               #
    # ------------------------------------------------------------------ #

    def search_objects(
        self,
        pattern: str,
        object_type: Optional[str] = None,
        schema: Optional[str] = None,
    ) -> list[dict]:
        """
        Search for Oracle objects by name and comment metadata.

        Results are ordered by match quality: exact → prefix → substring → comment.
        Wildcards are added automatically — do not include them in *pattern*.
        """
        if not self.connection:
            self.connect()

        upper_pattern = pattern.upper().strip("%")
        if object_type:
            object_type = object_type.upper()
            if object_type not in _ALLOWED_ORACLE_TYPES:
                raise ValueError(
                    f"Invalid object_type '{object_type}'. "
                    f"Allowed values: {sorted(_ALLOWED_ORACLE_TYPES)}"
                )

        cursor = self.connection.cursor()
        results: list[dict] = []
        seen: set[tuple] = set()

        schema_clause = "AND owner = :schema" if schema else ""
        schema_param: dict = {"schema": schema.upper()} if schema else {}

        if object_type:
            type_clause = "AND object_type = :otype"
            type_param: dict = {"otype": object_type}
        else:
            type_clause = "AND object_type IN ('TABLE', 'VIEW')"
            type_param = {}

        base_params = {**type_param, **schema_param}

        # -- Name searches (exact, prefix, substring) --------------------
        for match_label, pat in [
            ("exact",     upper_pattern),
            ("prefix",    upper_pattern + "%"),
            ("substring", "%" + upper_pattern + "%"),
        ]:
            query = f"""
                SELECT DISTINCT owner, object_name, object_type
                FROM   all_objects
                WHERE  object_name LIKE :pattern
                  {type_clause}
                  {schema_clause}
                ORDER BY owner, object_type, object_name
            """
            cursor.execute(query, {"pattern": pat, **base_params})
            for row in cursor.fetchall():
                key = (row[0], row[1])
                if key not in seen:
                    seen.add(key)
                    results.append({
                        "schema": row[0],
                        "name":   row[1],
                        "type":   row[2],
                        "match_type": match_label,
                    })

        # -- Comment/description searches --------------------------------
        if object_type in (None, "TABLE", "VIEW"):
            comment_params = {"pattern": "%" + upper_pattern + "%", **base_params}
            owner_col_map = [
                ("all_tab_comments", "tc", "owner",  "table_name"),
                ("all_col_comments", "cc", "owner",  "table_name"),
            ]
            for tbl, alias, owner_col, name_col in owner_col_map:
                q = f"""
                    SELECT DISTINCT {alias}.{owner_col}, {alias}.{name_col}, ao.object_type
                    FROM   {tbl} {alias}
                    JOIN   all_objects ao
                           ON  ao.owner       = {alias}.{owner_col}
                           AND ao.object_name = {alias}.{name_col}
                    WHERE  UPPER({alias}.comments) LIKE :pattern
                      {type_clause}
                      {'AND ' + alias + '.' + owner_col + ' = :schema' if schema else ''}
                    ORDER BY {alias}.{owner_col}, ao.object_type, {alias}.{name_col}
                """
                cursor.execute(q, comment_params)
                for row in cursor.fetchall():
                    key = (row[0], row[1])
                    if key not in seen:
                        seen.add(key)
                        results.append({
                            "schema": row[0],
                            "name":   row[1],
                            "type":   row[2],
                            "match_type": "comment",
                        })

        cursor.close()
        return results

    # ------------------------------------------------------------------ #
    # Describe                                                             #
    # ------------------------------------------------------------------ #

    def describe_object(self, object_name: str, schema: Optional[str] = None) -> str:
        """Return SQL*Plus–style DESCRIBE output for an Oracle table or view."""
        if "." in object_name and schema is None:
            schema, object_name = object_name.split(".", 1)

        if not self.connection:
            self.connect()

        cursor = self.connection.cursor()
        query = """
            SELECT column_name, nullable, data_type,
                   data_length, data_precision, data_scale
            FROM   all_tab_columns
            WHERE  table_name = :object_name
        """
        params: dict = {"object_name": object_name.upper()}
        if schema:
            query += " AND owner = :schema"
            params["schema"] = schema.upper()
        query += " ORDER BY column_id"

        cursor.execute(query, params)
        columns = cursor.fetchall()
        cursor.close()

        if not columns:
            return f"Object '{object_name}' not found or no columns accessible."

        output = [
            "Name                           Null?    Type",
            "------------------------------- -------- ----------------------------",
        ]
        for col_name, nullable, data_type, data_length, data_precision, data_scale in columns:
            null_str = "NOT NULL" if nullable == "N" else ""
            if data_type in ("VARCHAR2", "CHAR", "NVARCHAR2", "NCHAR", "RAW"):
                type_str = f"{data_type}({data_length})"
            elif data_type == "NUMBER":
                if data_precision is not None:
                    if data_scale is not None and data_scale > 0:
                        type_str = f"NUMBER({data_precision},{data_scale})"
                    else:
                        type_str = f"NUMBER({data_precision})"
                else:
                    type_str = "NUMBER"
            else:
                type_str = data_type
            output.append(f"{col_name:<31} {null_str:<8} {type_str}")

        return "\n".join(output)
