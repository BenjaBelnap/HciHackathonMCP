# MCP Server for Oracle Database Tools

Model Context Protocol server that exposes Oracle database search and describe capabilities as tools. Compatible with Crush, Claude Desktop, and any MCP-compatible client.

## Tools Exposed

### `search_database_objects`
Search for database tables and views matching a pattern.

**Parameters:**
- `pattern` (required): Search pattern (e.g., "patient" finds PATIENT, PAT_ENC, etc.)
- `object_type` (optional): Filter by TABLE or VIEW
- `owner` (optional): Filter by schema (e.g., "CLARITY")

### `describe_database_object`
Get the structure/definition of a table or view.

**Parameters:**
- `object_name` (required): Table/view name, can be schema-qualified (e.g., "CLARITY.PATIENT")
- `owner` (optional): Schema owner if not in object_name

## Setup

### 1. Install Dependencies

```powershell
# From project root
cd src/mcp-server
pip install -r requirements.txt
```

### 2. Configure Environment

The `.env` file contains Oracle connection settings:

```
ORACLE_USERNAME=CLARITY
ORACLE_PASSWORD=Clarity123
ORACLE_HOST=localhost
ORACLE_PORT=1521
ORACLE_SERVICE_NAME=XEPDB1
```

### 3. Start Database (if using local Docker)

```powershell
cd database
docker compose up -d
```

## Usage with Crush

### Install Crush

```powershell
# Windows
winget install charmbracelet.crush
```

### Run Crush

From the project root directory (where `crush.json` is located):

```powershell
crush
```

Crush will automatically detect the MCP server configuration and load the Oracle tools.

### Example Queries

Try these prompts in Crush:

- "Find all tables related to patients"
- "What tables contain medication information?"
- "Describe the CLARITY.PATIENT table"
- "Search for tables with 'order' in the name and describe them"

## Usage with Claude Desktop

Add to `claude_desktop_config.json` (typically at `%APPDATA%\Claude\claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "oracle-database": {
      "command": "python",
      "args": ["C:/Users/YOUR_USER/Documents/Repos/HciHackathonMCP/src/mcp-server/server.py"],
      "env": {
        "ORACLE_USERNAME": "CLARITY",
        "ORACLE_PASSWORD": "Clarity123",
        "ORACLE_HOST": "localhost",
        "ORACLE_PORT": "1521",
        "ORACLE_SERVICE_NAME": "XEPDB1"
      }
    }
  }
}
```

## Testing the Server

You can test the MCP server directly:

```powershell
cd src/mcp-server
python server.py
```

The server communicates via stdio (standard input/output) using the MCP protocol. It will wait for MCP client connections.

## Troubleshooting

### Connection Errors

1. Ensure Oracle database is running:
   ```powershell
   cd database
   docker compose ps
   ```

2. Verify credentials in `.env` match your database setup

3. Check network connectivity to Oracle host/port

### Missing Dependencies

```powershell
pip install mcp oracledb python-dotenv
```

### Crush Not Finding Tools

- Ensure you're running `crush` from the project root (where `crush.json` is)
- Check `crush.json` has correct path to `server.py`
- Verify Python is in your PATH
