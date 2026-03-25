# README
## MVP
### MCP SERVER
  - A single function that returns the table/view definition in the database.
  - A frontend chat that can interface with the MCP

---

## Claude Code Skill Setup

This repo includes a Claude Code skill that teaches Claude how to discover and query database schemas via the API.

### Install the skill

```bash
# Create your personal Claude skills folder (once)
mkdir -p ~/.claude/skills

# Link (or copy) this repo's skill into it
ln -s "$(pwd)/SKILL.md" ~/.claude/skills/db-schema/SKILL.md
# Windows: mklink /D %USERPROFILE%\.claude\skills\db-schema "$(pwd)"
```

Or copy it manually:

```bash
mkdir -p ~/.claude/skills/db-schema
cp SKILL.md ~/.claude/skills/db-schema/SKILL.md
```

### Use the skill

Claude will load it automatically when you ask schema-related questions, or invoke it directly:

```
/db-schema
```

### Start the API server first

The skill requires the OpenAPI tool server to be running:

```bash
cd src/openapi-tool-server
pip install -r requirements.txt
python server.py
# → http://localhost:8001
```

From a devcontainer, use `http://host.docker.internal:8001` instead of `localhost`.

