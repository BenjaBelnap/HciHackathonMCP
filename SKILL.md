---
name: db-schema
description: "Discovers and inspects database schemas (tables, views, columns) across Oracle and SQL Server. Use when exploring a database, finding tables, looking up column definitions, or before writing SQL queries."
---

# Database Object Query API — Agent Skill

## Purpose

This API lets you **discover and inspect database schemas** (tables, views, and their column definitions) across multiple Oracle and SQL Server database servers.

Use it whenever you need to:
- Find what tables/views exist in a database
- Get column names, types, and nullability for a specific table or view
- Understand the data model before writing SQL queries

---

## Base URL

Default: `http://localhost:8001`

Swagger UI: `http://localhost:8001/docs`

---

## Discovery Flow (start here if you have no context)

Follow this exact sequence if you don't know the server or database yet:

```
Step 1 — Find available servers
  GET /servers
  → returns list of { name, type } for each configured server

Step 2 — If server type is "sqlserver", find available databases
  GET /servers/{server_name}/databases
  OR
  POST /search_objects  { "pattern": "...", "server": "sqlserver-local" }
  → response contains "available_databases" list

Step 3 — Search for objects
  POST /search_objects  { "pattern": "...", "server": "...", "database": "..." }
  → returns matching tables/views with match_type info

Step 4 — Describe a specific object
  POST /describe_object { "object_name": "SCHEMA.TABLE", "server": "...", "database": "..." }
  → returns column listing

Step 5 (optional) — Search + describe in one call
  POST /search_and_describe { "pattern": "...", "server": "...", "database": "..." }
```

> **Oracle note**: Oracle does not have the "database" concept. The `database` field is ignored for Oracle servers. Skip Step 2 for Oracle — go straight to Step 3.

---

## Endpoints

### `GET /servers`

List all configured server connections.

**Response:**
```json
[
  { "name": "oracle-local",    "type": "oracle" },
  { "name": "sqlserver-local", "type": "sqlserver" }
]
```

---

### `GET /servers/{server_name}/databases`

List databases available on a SQL Server instance.

**Example:** `GET /servers/sqlserver-local/databases`

**Response:**
```json
{
  "server": "sqlserver-local",
  "type": "sqlserver",
  "databases": ["master", "CLARITY", "tempdb"]
}
```

For Oracle, `databases` will be `[]` and a `note` field explains that Oracle uses schemas instead.

---

### `GET /servers/{server_name}/schemas?database={db}`

List schemas within a server (or within a specific SQL Server database).

**Example:** `GET /servers/sqlserver-local/schemas?database=CLARITY`

**Response:**
```json
{
  "server": "sqlserver-local",
  "type": "sqlserver",
  "database": "CLARITY",
  "schemas": ["dbo", "clarity"]
}
```

---

### `POST /search_objects`

Search for database objects by name or description.

**Request body:**
```json
{
  "pattern":     "patient",
  "object_type": "TABLE",
  "schema":      "dbo",
  "server":      "sqlserver-local",
  "database":    "CLARITY"
}
```

| Field         | Required | Notes |
|---------------|----------|-------|
| `pattern`     | Yes      | Partial names work — wildcards added automatically. `"pat"` matches `PATIENT`, `PAT_ENC`, `INPATIENT_VISIT`. |
| `object_type` | No       | `TABLE`, `VIEW`, `PROCEDURE`, `FUNCTION`. Defaults to TABLE + VIEW. |
| `schema`      | No       | Filter by schema/owner (e.g. `dbo`, `CLARITY`). |
| `server`      | No       | Omit → get `available_servers` list in response. |
| `database`    | No       | SQL Server only. Omit (with server set) → get `available_databases` list. |

**Response when server is provided:**
```json
{
  "pattern": "patient",
  "server":  "sqlserver-local",
  "database": "CLARITY",
  "count":   3,
  "objects": [
    {
      "schema_name": "dbo",
      "name":        "PATIENT",
      "type":        "TABLE",
      "match_type":  "exact",
      "full_name":   "dbo.PATIENT"
    },
    {
      "schema_name": "dbo",
      "name":        "PAT_ENC",
      "type":        "TABLE",
      "match_type":  "prefix",
      "full_name":   "dbo.PAT_ENC"
    }
  ]
}
```

**Response when server is omitted:**
```json
{
  "pattern": "patient",
  "available_servers": [
    { "name": "oracle-local",    "type": "oracle" },
    { "name": "sqlserver-local", "type": "sqlserver" }
  ],
  "message": "No server specified. Please include a 'server' field..."
}
```

**`match_type` values** (sorted by relevance, best first):
| Value       | Meaning                                         |
|-------------|--------------------------------------------------|
| `exact`     | Object name exactly matches the pattern          |
| `prefix`    | Object name starts with the pattern              |
| `substring` | Object name contains the pattern anywhere        |
| `comment`   | Object description/comment contains the pattern  |

---

### `POST /describe_object`

Get column definitions for a specific table or view.

**Request body:**
```json
{
  "object_name": "dbo.PATIENT",
  "server":      "sqlserver-local",
  "database":    "CLARITY"
}
```

You can pass the schema in `object_name` as `SCHEMA.TABLE`, or separately in `schema`.

**Response:**
```json
{
  "object_name": "dbo.PATIENT",
  "server":      "sqlserver-local",
  "database":    "CLARITY",
  "result": "Column Name                     Nullable  Data Type\n------------------------------- --------- ----------------------------\nPAT_ID                          NOT NULL  int\nPAT_NAME                        NULL      varchar(100)\n..."
}
```

---

### `POST /search_and_describe`

Combined search + describe in a single request. Useful when you know the pattern but not the exact object name.

**Request body:**
```json
{
  "pattern":      "patient",
  "server":       "sqlserver-local",
  "database":     "CLARITY",
  "describe_all": false
}
```

Setting `"describe_all": true` describes every matching object (can be verbose). Default is `false` — describes only the first/best match.

**Response:**
```json
{
  "pattern":  "patient",
  "server":   "sqlserver-local",
  "database": "CLARITY",
  "count":    2,
  "objects":  [ ... ],
  "descriptions": {
    "dbo.PATIENT": "Column Name ...\n..."
  }
}
```

---

## Search Tips

- **Partial names always work**: `"pat"` → PATIENT, PAT_ENC, INPATIENT_VISIT
- **No need for `%` wildcards** — the API adds them automatically
- **Case insensitive** — `"Patient"`, `"PATIENT"`, `"patient"` all work the same
- **Description search**: If an object has extended property / table comment containing your term, it shows up as `match_type: "comment"`
- **Filter noise**: Use `"object_type": "TABLE"` to exclude views, procedures, etc.
- **Narrow by schema**: Use `"schema": "dbo"` to skip system schemas

---

## Configuration

Server connections are defined in `src/config/servers.json`:
```json
{
  "servers": {
    "oracle-local": {
      "type":         "oracle",
      "host":         "localhost",
      "port":         1521,
      "service_name": "XEPDB1",
      "username":     "CLARITY",
      "password":     "Clarity123"
    },
    "sqlserver-local": {
      "type":     "sqlserver",
      "host":     "localhost",
      "port":     1433,
      "username": "sa",
      "password": "SqlPassword123!"
    }
  }
}
```

**Environment variable overrides** (useful for CI / secrets management):
```
DB_SERVER_<NAME_UPPER>_<FIELD_UPPER>=value
# Examples:
DB_SERVER_ORACLE_LOCAL_PASSWORD=prod_secret
DB_SERVER_SQLSERVER_LOCAL_HOST=prod-sql.example.com
```
(Hyphens in server names become underscores in the env var name.)

---

## Error Handling

| HTTP Status | Meaning |
|-------------|---------|
| 200         | Success — or guidance response (available_servers / available_databases) |
| 404         | Server name not found in configuration |
| 422         | Invalid parameter (e.g. unsupported `object_type`) |
| 500         | Database error (connectivity, permission, etc.) |

All error responses include a `detail` string with a description and suggested fixes.

Guidance responses (missing server, missing database) return **HTTP 200**, not an error. Check for the presence of `available_servers` or `available_databases` keys to detect them.

---

## Starting the Server

```bash
cd src/openapi-tool-server
pip install -r requirements.txt
python server.py
# → Listening on http://0.0.0.0:8001
```

Or with uvicorn directly:
```bash
uvicorn server:app --host 0.0.0.0 --port 8001 --reload
```

---

## Test Databases (Docker)

### Oracle XE

```bash
cd database
docker compose up -d
# Oracle available at localhost:1521, service XEPDB1, user CLARITY / Clarity123
```

### SQL Server 2022

```bash
cd database/sqlserver
docker compose up -d
# SQL Server at localhost:1433, SA / SqlPassword123!, database CLARITY
```

Both have the same Epic Clarity–style schema: CLARITY_DEP, PATIENT, PAT_ENC, ORDER_PROC, CLARITY_MEDICATION, ORDER_MED.

---

## Running Tests

```bash
pip install -r tests/requirements.txt
pytest tests/ -v
```

All tests are fully mocked — no database running required.
