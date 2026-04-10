# src/config

This directory holds all runtime configuration for the project.

## Files

| File | Committed | Purpose |
|------|-----------|---------|
| `servers.example.json` | Yes | Template for server connection config — safe to commit, uses placeholder values |
| `servers.json` | **No** (git-ignored) | Your real server list with actual hostnames and credentials |
| `.env.example` | Yes | Template for environment variables — safe to commit, uses placeholder values |
| `.env` | **No** (git-ignored) | Your real environment variables with actual credentials |

## How passwords (and other credentials) work

**Yes — the `.env` file is the right place to store passwords for all servers defined in `servers.json`.**

`servers.json` supports every server connection field (`host`, `port`, `username`, `password`, etc.), but storing real passwords there is risky because the file can be accidentally committed. Instead:

- `servers.json` holds non-secret settings (host, port, service name, username) with placeholder values like `"CHANGE_ME"` for anything sensitive.
- `.env` holds the real secrets.
- At startup, `ConnectionManager` reads both files and **merges the env vars over `servers.json`**, so the live connection always uses the value from `.env` when one is present.

### Quick start

1. Copy the example files and fill in your real values:

   ```bash
   cp servers.example.json servers.json
   cp .env.example .env
   ```

2. Edit `servers.json` with your hostnames, ports, and usernames — leave passwords as `"CHANGE_ME"`.

3. Edit `.env` with your real passwords. There are **two env var patterns** depending on which component you are configuring:

   **Pattern 1 — `ORACLE_*` (standalone MCP server / `crush.json`):**
   Used directly by the MCP server for a single Oracle connection.
   ```env
   ORACLE_USERNAME=CLARITY
   ORACLE_PASSWORD=my_real_password
   ORACLE_HOST=localhost
   ORACLE_PORT=1521
   ORACLE_SERVICE_NAME=XEPDB1
   ```

   **Pattern 2 — `DB_SERVER_*` (`ConnectionManager` / `servers.json`):**
   Overrides any field in `servers.json` for each named server.
   ```env
   DB_SERVER_ORACLE_LOCAL_PASSWORD=my_oracle_password
   DB_SERVER_ORACLE_PROD_PASSWORD=my_prod_oracle_password
   DB_SERVER_SQLSERVER_LOCAL_PASSWORD=my_sqlserver_password
   DB_SERVER_SQLSERVER_PROD_PASSWORD=my_prod_sqlserver_password
   ```

4. `.env` is already git-ignored — it will never be committed.

## Credential override pattern (DB_SERVER_*)

Any field in a `servers.json` server entry can be overridden by an environment variable. The naming scheme is:

```
DB_SERVER_<SERVER_NAME_UPPER>_<FIELD_UPPER>
```

Hyphens in server names are converted to underscores. Examples:

| servers.json key → field | Environment variable |
|--------------------------|----------------------|
| `oracle-local` → `password` | `DB_SERVER_ORACLE_LOCAL_PASSWORD` |
| `oracle-local` → `host` | `DB_SERVER_ORACLE_LOCAL_HOST` |
| `oracle-prod` → `password` | `DB_SERVER_ORACLE_PROD_PASSWORD` |
| `sqlserver-local` → `password` | `DB_SERVER_SQLSERVER_LOCAL_PASSWORD` |
| `sqlserver-local` → `host` | `DB_SERVER_SQLSERVER_LOCAL_HOST` |
| `sqlserver-prod` → `username` | `DB_SERVER_SQLSERVER_PROD_USERNAME` |

Integer-typed fields (e.g. `port`) are automatically cast back to `int` when read from the environment.

## Why not put passwords directly in servers.json?

- `servers.json` is easy to accidentally commit even when git-ignored (e.g. via `git add -f` or IDE tooling).
- Plaintext credentials in JSON files appear in logs, clipboard history, and editor search indexes.
- `.env` files have broad tooling support for secure handling (Docker secrets, CI/CD variable injection, etc.).
