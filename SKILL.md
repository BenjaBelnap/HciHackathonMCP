---
name: db-schema
description: "Discovers and inspects database schemas (tables, views, columns, stored procedures) across Oracle and SQL Server. Use when exploring a database, finding tables, looking up column definitions, retrieving stored procedure source code, or before writing SQL queries."
---

# Database Object Query API — Agent Skill

## How to Call This API

Use **curl via the Bash tool**. The base URL is `http://host.docker.internal:8001`.

> **Do NOT use WebFetch** — it cannot reach `host.docker.internal`. Always use curl.

---

## Discovery Flow (start here if you have no context)

Follow this sequence when you don't know the server or database yet.

### Step 1 — Find available servers

```bash
curl -s http://host.docker.internal:8001/servers
```

Returns a list of configured server connections with their type (oracle or sqlserver).

### Step 2 — If SQL Server, find available databases

```bash
curl -s http://host.docker.internal:8001/servers/sqlserver-local/databases
```

> **Oracle note**: Oracle does not use databases — skip this step for Oracle servers.

### Step 3 — Search for objects

```bash
curl -s -X POST http://host.docker.internal:8001/search_objects \
  -H 'Content-Type: application/json' \
  -d '{"pattern": "patient", "server": "sqlserver-local", "database": "CLARITY"}'
```

### Step 4 — Describe a specific object (tables/views only)

```bash
curl -s -X POST http://host.docker.internal:8001/describe_object \
  -H 'Content-Type: application/json' \
  -d '{"object_name": "dbo.PATIENT", "server": "sqlserver-local", "database": "CLARITY"}'
```

### Step 5 — Get stored procedure source code (SQL Server only)

```bash
curl -s -X POST http://host.docker.internal:8001/get_procedure_definition \
  -H 'Content-Type: application/json' \
  -d '{"object_name": "dbo.usp_SelectOne", "server": "sqlserver-local", "database": "master"}'
```

---

## Endpoints

### `GET /servers`

List all configured server connections.

```bash
curl -s http://host.docker.internal:8001/servers
```

Response:
```json
[
  { "name": "oracle-local",    "type": "oracle" },
  { "name": "sqlserver-local", "type": "sqlserver" }
]
```

---

### `GET /servers/{server_name}/databases`

List databases on a SQL Server instance. For Oracle, returns an empty list with a note.

```bash
curl -s http://host.docker.internal:8001/servers/sqlserver-local/databases
```

Response:
```json
{
  "server": "sqlserver-local",
  "type": "sqlserver",
  "databases": ["master", "CLARITY", "tempdb"]
}
```

---

### `GET /servers/{server_name}/schemas?database={db}`

List schemas within a server or database.

```bash
curl -s 'http://host.docker.internal:8001/servers/sqlserver-local/schemas?database=CLARITY'
```

Response:
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

```bash
curl -s -X POST http://host.docker.internal:8001/search_objects \
  -H 'Content-Type: application/json' \
  -d '{"pattern": "patient", "object_type": "TABLE", "server": "sqlserver-local", "database": "CLARITY"}'
```

| Field         | Required | Notes |
|---------------|----------|-------|
| `pattern`     | Yes      | Partial names work — wildcards added automatically. `"pat"` matches `PATIENT`, `PAT_ENC`, etc. |
| `object_type` | No       | `TABLE`, `VIEW`, `PROCEDURE`, `FUNCTION`. **Default: TABLE + VIEW only.** You must explicitly pass `"PROCEDURE"` to find stored procedures. |
| `schema`      | No       | Filter by schema/owner (e.g. `dbo`, `CLARITY`). |
| `server`      | No       | Omit → response contains `available_servers` list instead of results. |
| `database`    | No       | SQL Server only. Omit (with server set) → response contains `available_databases` list. Ignored for Oracle. |

Response:
```json
{
  "pattern": "patient",
  "server": "sqlserver-local",
  "database": "CLARITY",
  "count": 2,
  "objects": [
    {
      "schema_name": "dbo",
      "name": "PATIENT",
      "type": "TABLE",
      "match_type": "exact",
      "full_name": "dbo.PATIENT"
    },
    {
      "schema_name": "dbo",
      "name": "PAT_ENC",
      "type": "TABLE",
      "match_type": "prefix",
      "full_name": "dbo.PAT_ENC"
    }
  ]
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

Get column definitions for a table or view.

```bash
curl -s -X POST http://host.docker.internal:8001/describe_object \
  -H 'Content-Type: application/json' \
  -d '{"object_name": "dbo.PATIENT", "server": "sqlserver-local", "database": "CLARITY"}'
```

| Field         | Required | Notes |
|---------------|----------|-------|
| `object_name` | Yes      | Schema-qualified names work: `SCHEMA.TABLE` or just the name. |
| `schema`      | No       | Schema / owner (optional if included in `object_name`). |
| `server`      | No       | Omit → guided discovery response. |
| `database`    | No       | SQL Server only. |

Response:
```json
{
  "object_name": "dbo.PATIENT",
  "server": "sqlserver-local",
  "database": "CLARITY",
  "result": "Column Name                     Nullable  Data Type\n------------------------------- --------- ----------------------------\nPAT_ID                          NOT NULL  int\nPAT_NAME                        NULL      varchar(100)\n..."
}
```

> **Note:** This endpoint is for tables and views only. Calling it on a stored procedure will return "Object not found". Use `/get_procedure_definition` for procedures.

---

### `POST /get_procedure_definition`

Get the SQL source code of a stored procedure. **SQL Server only.**

```bash
curl -s -X POST http://host.docker.internal:8001/get_procedure_definition \
  -H 'Content-Type: application/json' \
  -d '{"object_name": "dbo.usp_SelectOne", "server": "sqlserver-local", "database": "master"}'
```

| Field         | Required | Notes |
|---------------|----------|-------|
| `object_name` | Yes      | Schema-qualified names work: `dbo.usp_MyProc` or just the name. |
| `schema`      | No       | Schema / owner (optional if included in `object_name`). |
| `server`      | No       | Omit → guided discovery response. |
| `database`    | No       | Omit → guided discovery with available databases. |

Response:
```json
{
  "object_name": "dbo.usp_SelectOne",
  "server": "sqlserver-local",
  "database": "master",
  "definition": "CREATE PROCEDURE dbo.usp_SelectOne\nAS\nBEGIN\n    SELECT 1 AS Result;\nEND"
}
```

Error cases:
- **Oracle server** → HTTP 422: `"Procedure definition retrieval is only supported for SQL Server connections."`
- **Not found** → `"definition": "Procedure 'X' not found or not accessible."`
- **Encrypted** → `"definition": "Procedure 'X' is encrypted — definition is not available."`

---

### `POST /search_and_describe`

Combined search + describe in a single request. Searches for objects and describes the matches.

```bash
curl -s -X POST http://host.docker.internal:8001/search_and_describe \
  -H 'Content-Type: application/json' \
  -d '{"pattern": "patient", "server": "sqlserver-local", "database": "CLARITY", "describe_all": false}'
```

Setting `"describe_all": true` describes every match (can be verbose). Default describes only the first/best match.

---

## Important Nuances

- **Default search returns only TABLE + VIEW.** To find procedures, you must pass `"object_type": "PROCEDURE"`.
- **Guided discovery, not errors.** When you omit `server` or `database`, the API returns a helpful response with available options — it does not return an HTTP error.
- **Case insensitive.** `"Patient"`, `"PATIENT"`, `"patient"` all work the same.
- **No wildcards needed.** The API adds `%` wildcards automatically.
- **Oracle has no databases.** The `database` field is ignored for Oracle servers. Skip the database discovery step.
- **`describe_object` is for tables/views only.** Use `/get_procedure_definition` for stored procedure source code.
- **Procedure definitions are SQL Server only.** Oracle connections return a 422 error.
