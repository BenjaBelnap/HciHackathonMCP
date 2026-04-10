"""
Multi-database Object Query Tool Server for Open-WebUI / coding agents.

Supports Oracle and SQL Server through a shared connection configuration
(src/config/servers.json).  Agents should follow this discovery flow:

  1. No server known?  → POST /search_objects with no 'server' field
                          → response contains 'available_servers'
  2. Server is SQL Server, no database?
                        → POST /search_objects with 'server' but no 'database'
                          → response contains 'available_databases'
  3. All info known?  → POST /search_objects / POST /describe_object / POST /search_and_describe

Discovery endpoints (GET):
  GET /servers
  GET /servers/{server_name}/databases
  GET /servers/{server_name}/schemas
"""
import sys
import os
from typing import Optional

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, ConfigDict, Field

# ---------------------------------------------------------------------------
# Path setup — import services as a proper package to enable relative imports
# ---------------------------------------------------------------------------
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "services"))

from dataObjectQueryService.connection_manager import ConnectionManager, ServerNotFoundError  # noqa: E402

# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------
app = FastAPI(
    title="Database Object Query Tool Server",
    description=(
        "Query Oracle and SQL Server schemas to discover tables, views, and their "
        "column definitions. Supports multiple named server connections.\n\n"
        "**Discovery flow (for agents with no prior context):**\n"
        "1. `POST /search_objects` with no `server` → get `available_servers`\n"
        "2. If SQL Server: `POST /search_objects` with `server` but no `database` → get `available_databases`\n"
        "3. `POST /search_objects` with full context → get matching objects\n"
        "4. `POST /describe_object` → get column definitions\n"
    ),
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Dependency — lazy singleton ConnectionManager
# ---------------------------------------------------------------------------
_manager: Optional[ConnectionManager] = None


def get_manager() -> ConnectionManager:
    global _manager
    if _manager is None:
        _manager = ConnectionManager()
    return _manager


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

class ServerInfo(BaseModel):
    name: str
    type: str


class SearchResult(BaseModel):
    schema_name: str = Field(..., description="Schema / owner that contains this object")
    name: str        = Field(..., description="Object name")
    type: str        = Field(..., description="Object type, e.g. TABLE or VIEW")
    match_type: str  = Field(..., description="How the pattern matched: exact | prefix | substring | comment")
    full_name: str   = Field(..., description="Convenience: schema_name.name")


class SearchObjectsRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    pattern: str = Field(
        ...,
        description=(
            "Search pattern — partial names work, wildcards are added automatically. "
            "E.g. 'patient' finds PATIENT, PAT_ENC, INPATIENT_VISIT."
        ),
        examples=["patient", "order", "medication"],
    )
    object_type: Optional[str] = Field(
        None,
        description="Optionally restrict to TABLE, VIEW, PROCEDURE, FUNCTION, etc.",
        examples=["TABLE", "VIEW"],
    )
    db_schema: Optional[str] = Field(
        None,
        alias="schema",
        description="Optionally restrict to a specific schema / owner.",
        examples=["CLARITY", "dbo"],
    )
    server: Optional[str] = Field(
        None,
        description=(
            "Name of the server connection as defined in servers.json. "
            "Omit to receive a list of available servers."
        ),
        examples=["oracle-local", "sqlserver-local"],
    )
    database: Optional[str] = Field(
        None,
        description=(
            "SQL Server only: the database to search in. "
            "Omit (with a SQL Server server) to receive a list of available databases. "
            "Ignored for Oracle."
        ),
        examples=["CLARITY", "AdventureWorks"],
    )


class SearchObjectsResponse(BaseModel):
    pattern: str
    server: Optional[str]                     = None
    database: Optional[str]                   = None
    objects: Optional[list[SearchResult]]     = None
    count: Optional[int]                      = None
    available_servers: Optional[list[ServerInfo]] = None
    available_databases: Optional[list[str]]  = None
    message: Optional[str]                    = None


class DescribeObjectRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    object_name: str = Field(
        ...,
        description=(
            "Name of the database object. Accepts schema-qualified names "
            "(e.g. CLARITY.PATIENT or dbo.Patient)."
        ),
        examples=["PATIENT", "CLARITY.PAT_ENC", "dbo.Patient"],
    )
    db_schema: Optional[str] = Field(
        None,
        alias="schema",
        description="Schema / owner (optional if included in object_name).",
        examples=["CLARITY", "dbo"],
    )
    server: Optional[str] = Field(
        None,
        description="Name of the server connection. Omit to receive available servers.",
        examples=["oracle-local", "sqlserver-local"],
    )
    database: Optional[str] = Field(
        None,
        description="SQL Server only: database context. Ignored for Oracle.",
        examples=["CLARITY"],
    )


class DescribeObjectResponse(BaseModel):
    object_name: str
    db_schema: Optional[str]     = Field(None, alias="schema")
    server: Optional[str]    = None
    database: Optional[str]  = None
    result: Optional[str]    = None
    available_servers: Optional[list[ServerInfo]] = None
    available_databases: Optional[list[str]]      = None
    message: Optional[str]                        = None


class SearchAndDescribeRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    pattern: str = Field(
        ...,
        description="Search pattern — same as /search_objects.",
        examples=["patient", "order"],
    )
    object_type: Optional[str] = Field(None, examples=["TABLE"])
    db_schema: Optional[str]   = Field(None, alias="schema", examples=["CLARITY", "dbo"])
    server: Optional[str]      = Field(None, examples=["oracle-local", "sqlserver-local"])
    database: Optional[str]    = Field(None, examples=["CLARITY"])
    describe_all: bool = Field(
        False,
        description="If True, describe all matching objects. If False (default), describe only the first match.",
    )


class SearchAndDescribeResponse(BaseModel):
    pattern: str
    server: Optional[str]                     = None
    database: Optional[str]                   = None
    objects: Optional[list[SearchResult]]     = None
    count: Optional[int]                      = None
    descriptions: Optional[dict[str, str]]    = None
    available_servers: Optional[list[ServerInfo]] = None
    available_databases: Optional[list[str]]  = None
    message: Optional[str]                    = None


class GetProcedureDefinitionRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    object_name: str = Field(
        ...,
        description=(
            "Name of the stored procedure. Accepts schema-qualified names "
            "(e.g. dbo.usp_GetPatient)."
        ),
        examples=["dbo.usp_GetPatient", "usp_SelectOne"],
    )
    db_schema: Optional[str] = Field(
        None,
        alias="schema",
        description="Schema / owner (optional if included in object_name).",
        examples=["dbo"],
    )
    server: Optional[str] = Field(
        None,
        description="Name of the server connection. Omit to receive available servers.",
        examples=["sqlserver-local"],
    )
    database: Optional[str] = Field(
        None,
        description="SQL Server only: database context.",
        examples=["master", "CLARITY"],
    )


class GetProcedureDefinitionResponse(BaseModel):
    object_name: str
    db_schema: Optional[str]     = Field(None, alias="schema")
    server: Optional[str]        = None
    database: Optional[str]      = None
    definition: Optional[str]    = None
    available_servers: Optional[list[ServerInfo]] = None
    available_databases: Optional[list[str]]      = None
    message: Optional[str]                        = None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _to_search_results(raw: list[dict]) -> list[SearchResult]:
    return [
        SearchResult(
            schema_name=r["schema"],
            name=r["name"],
            type=r["type"],
            match_type=r["match_type"],
            full_name=f"{r['schema']}.{r['name']}",
        )
        for r in raw
    ]


def _guidance_no_server(manager: ConnectionManager, pattern: str) -> SearchObjectsResponse:
    servers = [ServerInfo(**s) for s in manager.list_servers()]
    return SearchObjectsResponse(
        pattern=pattern,
        available_servers=servers,
        message=(
            "No server specified. Please include a 'server' field in your request "
            "using one of the available server names listed in 'available_servers'."
        ),
    )


def _guidance_no_database(
    manager: ConnectionManager, server: str, pattern: str
) -> SearchObjectsResponse:
    service = manager.get_service(server)
    service.connect()
    databases = service.list_databases()
    service.disconnect()
    return SearchObjectsResponse(
        pattern=pattern,
        server=server,
        available_databases=databases,
        message=(
            f"Server '{server}' is a SQL Server instance that requires a database selection. "
            "Please include a 'database' field in your request using one of the values "
            "listed in 'available_databases'."
        ),
    )


# ---------------------------------------------------------------------------
# Info endpoints
# ---------------------------------------------------------------------------

@app.get("/", tags=["info"])
def root():
    return {
        "message": "Database Object Query Tool Server",
        "docs":    "/docs",
        "openapi": "/openapi.json",
        "version": "2.0.0",
    }


@app.get("/health", tags=["info"])
def health():
    return {"status": "healthy"}


@app.get("/servers", response_model=list[ServerInfo], tags=["discovery"])
def list_servers(manager: ConnectionManager = Depends(get_manager)):
    """List all configured database server connections."""
    return [ServerInfo(**s) for s in manager.list_servers()]


@app.get(
    "/servers/{server_name}/databases",
    tags=["discovery"],
    summary="List databases on a server",
)
def list_databases(
    server_name: str,
    manager: ConnectionManager = Depends(get_manager),
):
    """
    List available databases on the specified server.

    For SQL Server: returns a list of database names.
    For Oracle: returns an empty list with an explanatory note
                (Oracle uses schemas/owners, not databases).
    """
    try:
        server_type = manager.get_server_type(server_name)
        service = manager.get_service(server_name)
        service.connect()
        databases = service.list_databases()
        service.disconnect()
        if server_type == "oracle":
            return {
                "server": server_name,
                "type": "oracle",
                "databases": [],
                "note": (
                    "Oracle does not use the database/catalog concept. "
                    "Use GET /servers/{server_name}/schemas to list Oracle schemas."
                ),
            }
        return {"server": server_name, "type": server_type, "databases": databases}
    except ServerNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.get(
    "/servers/{server_name}/schemas",
    tags=["discovery"],
    summary="List schemas on a server",
)
def list_schemas(
    server_name: str,
    database: Optional[str] = None,
    manager: ConnectionManager = Depends(get_manager),
):
    """
    List schemas for the specified server.

    For SQL Server, provide the *database* query parameter to list schemas
    within that database.
    """
    try:
        server_type = manager.get_server_type(server_name)
        service = manager.get_service(server_name, database=database)
        service.connect()
        schemas = service.list_schemas()
        service.disconnect()
        return {
            "server":   server_name,
            "type":     server_type,
            "database": database,
            "schemas":  schemas,
        }
    except ServerNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


# ---------------------------------------------------------------------------
# Tool endpoints
# ---------------------------------------------------------------------------

@app.post("/search_objects", response_model=SearchObjectsResponse, tags=["tools"])
def search_objects(
    request: SearchObjectsRequest,
    manager: ConnectionManager = Depends(get_manager),
):
    """
    Search for database objects (tables, views, etc.) matching a pattern.

    **Discovery behaviour:**
    - Omit `server` → response contains `available_servers` list.
    - For SQL Server, omit `database` → response contains `available_databases` list.
    - Provide both → returns matching objects sorted by relevance.

    Pattern matching is automatic: the API searches for exact, prefix, and substring
    matches on object *names*, plus any description/comment metadata.
    You do **not** need to add `%` wildcards.
    """
    try:
        if not request.server:
            return _guidance_no_server(manager, request.pattern)

        server_type = manager.get_server_type(request.server)

        if server_type == "sqlserver" and not request.database:
            return _guidance_no_database(manager, request.server, request.pattern)

        service = manager.get_service(request.server, request.database)
        service.connect()
        raw = service.search_objects(
            pattern=request.pattern,
            object_type=request.object_type,
            schema=request.db_schema,
        )
        service.disconnect()

        objects = _to_search_results(raw)
        return SearchObjectsResponse(
            pattern=request.pattern,
            server=request.server,
            database=request.database,
            objects=objects,
            count=len(objects),
        )

    except ServerNotFoundError as exc:
        raise HTTPException(
            status_code=404,
            detail=(
                f"{exc}\n\nCall GET /servers to see all configured server names."
            ),
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=(
                f"Error searching for objects with pattern '{request.pattern}': {exc}\n\n"
                "Check database connectivity and verify the schema/server parameters."
            ),
        )


@app.post("/describe_object", response_model=DescribeObjectResponse, tags=["tools"])
def describe_object(
    request: DescribeObjectRequest,
    manager: ConnectionManager = Depends(get_manager),
):
    """
    Describe the structure (columns) of a database table or view.

    Accepts schema-qualified names: ``CLARITY.PATIENT`` or ``dbo.Patient``.

    **Discovery behaviour:**
    - Omit `server` → response contains `available_servers` list.
    - For SQL Server, omit `database` → response contains `available_databases` list.
    """
    try:
        if not request.server:
            servers = [ServerInfo(**s) for s in manager.list_servers()]
            return DescribeObjectResponse(
                object_name=request.object_name,
                available_servers=servers,
                message=(
                    "No server specified. Include a 'server' field using one of "
                    "the available server names listed in 'available_servers'."
                ),
            )

        server_type = manager.get_server_type(request.server)

        if server_type == "sqlserver" and not request.database:
            service = manager.get_service(request.server)
            service.connect()
            databases = service.list_databases()
            service.disconnect()
            return DescribeObjectResponse(
                object_name=request.object_name,
                server=request.server,
                available_databases=databases,
                message=(
                    f"Server '{request.server}' requires a database selection. "
                    "Include a 'database' field using one of 'available_databases'."
                ),
            )

        service = manager.get_service(request.server, request.database)
        service.connect()
        result = service.describe_object(request.object_name, schema=request.db_schema)
        service.disconnect()

        return DescribeObjectResponse(
            object_name=request.object_name,
            db_schema=request.db_schema,
            server=request.server,
            database=request.database,
            result=result,
        )

    except ServerNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=(
                f"Error describing object '{request.object_name}': {exc}\n\n"
                "Verify the object name and schema are correct and that you have access."
            ),
        )


@app.post("/search_and_describe", response_model=SearchAndDescribeResponse, tags=["tools"])
def search_and_describe(
    request: SearchAndDescribeRequest,
    manager: ConnectionManager = Depends(get_manager),
):
    """
    Search for objects matching a pattern **and** describe the results in one call.

    Set ``describe_all=true`` to describe every match; default is the first match only.

    Same discovery behaviour as ``/search_objects``.
    """
    try:
        if not request.server:
            servers = [ServerInfo(**s) for s in manager.list_servers()]
            return SearchAndDescribeResponse(
                pattern=request.pattern,
                available_servers=servers,
                message=(
                    "No server specified. Include a 'server' field using one of "
                    "the available server names in 'available_servers'."
                ),
            )

        server_type = manager.get_server_type(request.server)

        if server_type == "sqlserver" and not request.database:
            service = manager.get_service(request.server)
            service.connect()
            databases = service.list_databases()
            service.disconnect()
            return SearchAndDescribeResponse(
                pattern=request.pattern,
                server=request.server,
                available_databases=databases,
                message=(
                    f"Server '{request.server}' requires a database selection. "
                    "Include a 'database' field using one of 'available_databases'."
                ),
            )

        service = manager.get_service(request.server, request.database)
        service.connect()

        raw = service.search_objects(
            pattern=request.pattern,
            object_type=request.object_type,
            schema=request.db_schema,
        )

        objects = _to_search_results(raw)
        to_describe = raw if request.describe_all else raw[:1]

        descriptions: dict[str, str] = {}
        for obj in to_describe:
            full_name = f"{obj['schema']}.{obj['name']}"
            descriptions[full_name] = service.describe_object(
                obj["name"], schema=obj["schema"]
            )

        service.disconnect()

        return SearchAndDescribeResponse(
            pattern=request.pattern,
            server=request.server,
            database=request.database,
            objects=objects,
            count=len(objects),
            descriptions=descriptions,
        )

    except ServerNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=(
                f"Error during search_and_describe with pattern '{request.pattern}': {exc}\n\n"
                "Verify database connectivity and parameter values."
            ),
        )


@app.post(
    "/get_procedure_definition",
    response_model=GetProcedureDefinitionResponse,
    tags=["tools"],
)
def get_procedure_definition(
    request: GetProcedureDefinitionRequest,
    manager: ConnectionManager = Depends(get_manager),
):
    """
    Return the SQL source code of a stored procedure.

    **SQL Server only.** Returns an error for Oracle connections.

    Same discovery behaviour as other endpoints: omit ``server`` or ``database``
    to receive guided discovery responses.
    """
    try:
        if not request.server:
            servers = [ServerInfo(**s) for s in manager.list_servers()]
            return GetProcedureDefinitionResponse(
                object_name=request.object_name,
                available_servers=servers,
                message=(
                    "No server specified. Include a 'server' field using one of "
                    "the available server names listed in 'available_servers'."
                ),
            )

        server_type = manager.get_server_type(request.server)

        if server_type != "sqlserver":
            raise HTTPException(
                status_code=422,
                detail=(
                    f"Procedure definition retrieval is only supported for SQL Server connections. "
                    f"Server '{request.server}' is of type '{server_type}'."
                ),
            )

        if not request.database:
            service = manager.get_service(request.server)
            service.connect()
            databases = service.list_databases()
            service.disconnect()
            return GetProcedureDefinitionResponse(
                object_name=request.object_name,
                server=request.server,
                available_databases=databases,
                message=(
                    f"Server '{request.server}' requires a database selection. "
                    "Include a 'database' field using one of 'available_databases'."
                ),
            )

        service = manager.get_service(request.server, request.database)
        service.connect()
        definition = service.get_procedure_definition(
            request.object_name, schema=request.db_schema
        )
        service.disconnect()

        return GetProcedureDefinitionResponse(
            object_name=request.object_name,
            db_schema=request.db_schema,
            server=request.server,
            database=request.database,
            definition=definition,
        )

    except ServerNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=(
                f"Error retrieving definition for '{request.object_name}': {exc}\n\n"
                "Verify the procedure name, schema, and database are correct."
            ),
        )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)

