"""
SQL Server Database Query Service

Queries SQL Server system catalog views to return object metadata.
Uses pymssql — a pure-Python driver that does not require ODBC installation.
"""
from typing import Optional

import pymssql

from .database_query_service import DatabaseQueryService

# Map common generic type names → SQL Server type codes in sys.objects
_TYPE_MAP = {
    "TABLE":     ("U",),
    "VIEW":      ("V",),
    "PROCEDURE": ("P",),
    "FUNCTION":  ("FN", "IF", "TF"),
}

_ALLOWED_SS_TYPES = set(_TYPE_MAP.keys())

_TYPE_LABEL = {
    "U":  "TABLE",
    "V":  "VIEW",
    "P":  "PROCEDURE",
    "FN": "FUNCTION",
    "IF": "FUNCTION",
    "TF": "FUNCTION",
}


class SqlServerQueryService(DatabaseQueryService):
    """Queries SQL Server database object metadata."""

    def __init__(
        self,
        host: str,
        port: int = 1433,
        username: Optional[str] = None,
        password: Optional[str] = None,
        database: Optional[str] = None,
        windows_auth: bool = False,
    ):
        self.host = host
        self.port = int(port)
        self.username = username
        self.password = password
        self.database = database
        self.windows_auth = windows_auth
        self.connection = None

    # ------------------------------------------------------------------ #
    # Connection management                                                #
    # ------------------------------------------------------------------ #

    def connect(self) -> None:
        kwargs: dict = {"server": f"{self.host}:{self.port}"}
        if not self.windows_auth:
            kwargs["user"] = self.username
            kwargs["password"] = self.password
        if self.database:
            kwargs["database"] = self.database
        self.connection = pymssql.connect(**kwargs)

    def disconnect(self) -> None:
        if self.connection:
            self.connection.close()
            self.connection = None

    # ------------------------------------------------------------------ #
    # Discovery                                                            #
    # ------------------------------------------------------------------ #

    def list_databases(self) -> list[str]:
        """List all online databases on this SQL Server instance."""
        if not self.connection:
            self.connect()
        cursor = self.connection.cursor()
        cursor.execute(
            "SELECT name FROM sys.databases WHERE state_desc = 'ONLINE' ORDER BY name"
        )
        dbs = [row[0] for row in cursor.fetchall()]
        cursor.close()
        return dbs

    def list_schemas(self) -> list[str]:
        """List schemas within the currently connected database."""
        if not self.connection:
            self.connect()
        cursor = self.connection.cursor()
        cursor.execute(
            "SELECT SCHEMA_NAME FROM INFORMATION_SCHEMA.SCHEMATA ORDER BY SCHEMA_NAME"
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
        Search SQL Server objects by name and extended-property descriptions.

        Results ordered by match quality: exact → prefix → substring → comment.
        Wildcards are added automatically — do not include them in *pattern*.
        """
        if not self.connection:
            self.connect()

        upper_pattern = pattern.upper().strip("%")
        sql_types: tuple[str, ...]

        if object_type:
            object_type = object_type.upper()
            if object_type not in _ALLOWED_SS_TYPES:
                raise ValueError(
                    f"Invalid object_type '{object_type}'. "
                    f"Allowed values: {sorted(_ALLOWED_SS_TYPES)}"
                )
            sql_types = _TYPE_MAP[object_type]
        else:
            sql_types = ("U", "V")

        # Build an IN clause of the correct width (placeholders = %s each)
        type_placeholders = ", ".join(["%s"] * len(sql_types))
        type_clause = f"AND o.type IN ({type_placeholders})"

        schema_clause = "AND SCHEMA_NAME(o.schema_id) = %s" if schema else ""

        cursor = self.connection.cursor()
        results: list[dict] = []
        seen: set[tuple] = set()

        def _type_args() -> list:
            return list(sql_types)

        def _schema_args() -> list:
            return [schema] if schema else []

        def _search_by_name(pat: str) -> list:
            args = [pat] + _type_args() + _schema_args()
            cursor.execute(
                f"""
                SELECT SCHEMA_NAME(o.schema_id), o.name, o.type
                FROM   sys.objects o
                WHERE  UPPER(o.name) LIKE %s
                  {type_clause}
                  {schema_clause}
                ORDER BY SCHEMA_NAME(o.schema_id), o.type, o.name
                """,
                args,
            )
            return cursor.fetchall()

        # -- Name searches -----------------------------------------------
        for match_label, pat in [
            ("exact",     upper_pattern),
            ("prefix",    upper_pattern + "%"),
            ("substring", "%" + upper_pattern + "%"),
        ]:
            for row in _search_by_name(pat):
                key = (row[0], row[1])
                if key not in seen:
                    seen.add(key)
                    results.append({
                        "schema": row[0],
                        "name":   row[1],
                        "type":   _TYPE_LABEL.get(row[2].strip(), row[2].strip()),
                        "match_type": match_label,
                    })

        # -- Extended property (MS_Description) search -------------------
        ep_args = ["%" + upper_pattern + "%"] + _type_args() + _schema_args()
        cursor.execute(
            f"""
            SELECT DISTINCT SCHEMA_NAME(o.schema_id), o.name, o.type
            FROM   sys.objects o
            JOIN   sys.extended_properties ep
                   ON  ep.major_id = o.object_id
                   AND ep.minor_id = 0
                   AND ep.name     = 'MS_Description'
            WHERE  UPPER(CAST(ep.value AS NVARCHAR(MAX))) LIKE %s
              {type_clause}
              {schema_clause}
            """,
            ep_args,
        )
        for row in cursor.fetchall():
            key = (row[0], row[1])
            if key not in seen:
                seen.add(key)
                results.append({
                    "schema": row[0],
                    "name":   row[1],
                    "type":   _TYPE_LABEL.get(row[2].strip(), row[2].strip()),
                    "match_type": "comment",
                })

        cursor.close()
        return results

    # ------------------------------------------------------------------ #
    # Describe                                                             #
    # ------------------------------------------------------------------ #

    def describe_object(self, object_name: str, schema: Optional[str] = None) -> str:
        """Return a formatted column listing for a SQL Server table or view."""
        if "." in object_name and schema is None:
            schema, object_name = object_name.split(".", 1)

        if not self.connection:
            self.connect()

        cursor = self.connection.cursor()
        args: list = [object_name.upper()]
        schema_clause = ""
        if schema:
            schema_clause = "AND UPPER(SCHEMA_NAME(o.schema_id)) = %s"
            args.append(schema.upper())

        cursor.execute(
            f"""
            SELECT c.name,
                   t.name         AS data_type,
                   c.max_length,
                   c.precision,
                   c.scale,
                   c.is_nullable,
                   c.column_id
            FROM   sys.columns c
            JOIN   sys.objects o  ON o.object_id      = c.object_id
            JOIN   sys.types   t  ON t.user_type_id   = c.user_type_id
            WHERE  UPPER(o.name) = %s
              {schema_clause}
            ORDER BY c.column_id
            """,
            args,
        )
        columns = cursor.fetchall()
        cursor.close()

        if not columns:
            return f"Object '{object_name}' not found or no columns accessible."

        output = [
            "Column Name                     Nullable  Data Type",
            "------------------------------- --------- ----------------------------",
        ]
        for col_name, data_type, max_length, precision, scale, is_nullable, _ in columns:
            null_str = "NULL" if is_nullable else "NOT NULL"
            dt_upper = data_type.upper()
            if dt_upper in ("NVARCHAR", "NCHAR"):
                size = "MAX" if max_length == -1 else str(max_length // 2)
                type_str = f"{data_type}({size})"
            elif dt_upper in ("VARCHAR", "CHAR", "VARBINARY", "BINARY"):
                size = "MAX" if max_length == -1 else str(max_length)
                type_str = f"{data_type}({size})"
            elif dt_upper in ("DECIMAL", "NUMERIC"):
                type_str = f"{data_type}({precision},{scale})"
            else:
                type_str = data_type
            output.append(f"{col_name:<31} {null_str:<9} {type_str}")

        return "\n".join(output)
