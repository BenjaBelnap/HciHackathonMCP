"""
Sample queries demonstrating the Database Object Query API.

Covers:
  - Listing servers / SQL Server databases
  - Searching objects (with schema scoping for Oracle)
  - Describing individual tables
  - Combined search_and_describe
  - Cross-server comparison of the same schema

Run with: .venv-win\Scripts\python.exe sample_queries.py
"""
import json
import urllib.request

BASE = "http://localhost:8001"


def get(path: str) -> dict:
    with urllib.request.urlopen(f"{BASE}{path}") as r:
        return json.loads(r.read())


def post(path: str, data: dict) -> dict:
    body = json.dumps(data).encode()
    req = urllib.request.Request(
        f"{BASE}{path}", data=body, headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req) as r:
        return json.loads(r.read())


def section(title: str) -> None:
    print(f"\n{'='*60}")
    print(f"  {title}")
    print("=" * 60)


# ---------------------------------------------------------------------------
# 1. List all configured servers
# ---------------------------------------------------------------------------
section("1 — Available Servers  GET /servers")
for s in get("/servers"):
    print(f"  {s['name']:30s}  type={s['type']}")

# ---------------------------------------------------------------------------
# 2. SQL Server: list databases
# ---------------------------------------------------------------------------
section("2 — SQL Server Databases  GET /servers/sqlserver-local/databases")
db_resp = get("/servers/sqlserver-local/databases")
print(f"  Server : {db_resp['server']}  ({db_resp['type']})")
for db in db_resp["databases"]:
    print(f"    {db}")

# ---------------------------------------------------------------------------
# 3. SQL Server: search for all CLARITY application tables
# ---------------------------------------------------------------------------
section("3 — SQL Server: discover CLARITY tables  POST /search_objects")

ss_tables: list[str] = []
for pat in ["patient", "order", "clarity", "medication"]:
    result = post(
        "/search_objects",
        {"pattern": pat, "server": "sqlserver-local", "database": "CLARITY"},
    )
    for obj in result.get("objects", []):
        if obj["full_name"] not in ss_tables:
            ss_tables.append(obj["full_name"])
            print(f"  {obj['full_name']:35s}  {obj['type']:8s}  {obj['match_type']}")

# ---------------------------------------------------------------------------
# 4. SQL Server: describe every discovered table
# ---------------------------------------------------------------------------
section("4 — SQL Server: describe each table  POST /describe_object")

for full_name in ss_tables:
    resp = post(
        "/describe_object",
        {"object_name": full_name, "server": "sqlserver-local", "database": "CLARITY"},
    )
    print(f"\n--- {resp['object_name']} ---")
    print(resp["result"])

# ---------------------------------------------------------------------------
# 5. Oracle: search within the CLARITY schema (avoids SYS noise)
# ---------------------------------------------------------------------------
section("5 — Oracle: discover CLARITY schema tables  POST /search_objects")

ora_tables: list[str] = []
for pat in ["patient", "order", "clarity", "medication", "dep", "enc"]:
    result = post(
        "/search_objects",
        {"pattern": pat, "server": "oracle-local", "schema": "CLARITY"},
    )
    for obj in result.get("objects", []):
        if obj["full_name"] not in ora_tables:
            ora_tables.append(obj["full_name"])
            print(f"  {obj['full_name']:40s}  {obj['type']:8s}  {obj['match_type']}")

# ---------------------------------------------------------------------------
# 6. Oracle: describe each CLARITY table
# ---------------------------------------------------------------------------
section("6 — Oracle: describe each table  POST /describe_object")

for full_name in ora_tables:
    resp = post("/describe_object", {"object_name": full_name, "server": "oracle-local"})
    print(f"\n--- {resp['object_name']} ---")
    print(resp["result"])

# ---------------------------------------------------------------------------
# 7. Combined search_and_describe — SQL Server PAT_ENC
# ---------------------------------------------------------------------------
section("7 — Combined search_and_describe: 'enc'  POST /search_and_describe")

result = post(
    "/search_and_describe",
    {"pattern": "enc", "server": "sqlserver-local", "database": "CLARITY", "describe_all": True},
)
print(f"  Matched {result['count']} object(s)")
for obj in result.get("objects", []):
    desc = result.get("descriptions", {}).get(obj["full_name"], "(no description)")
    print(f"\n--- {obj['full_name']} ({obj['type']}) ---")
    print(desc)

# ---------------------------------------------------------------------------
# 8. Oracle schemas endpoint
# ---------------------------------------------------------------------------
section("8 — Oracle Schemas  GET /servers/oracle-local/schemas")
oracle_schemas = get("/servers/oracle-local/schemas")
print(f"  Server : {oracle_schemas['server']}")
for schema in oracle_schemas.get("schemas", [])[:10]:
    print(f"    {schema}")

# ---------------------------------------------------------------------------
# 9. SQL Server schemas in CLARITY database
# ---------------------------------------------------------------------------
section("9 — SQL Server Schemas  GET /servers/sqlserver-local/schemas?database=CLARITY")
ss_schemas = get("/servers/sqlserver-local/schemas?database=CLARITY")
print(f"  Server : {ss_schemas['server']}, DB: {ss_schemas['database']}")
for schema in ss_schemas.get("schemas", []):
    print(f"    {schema}")
