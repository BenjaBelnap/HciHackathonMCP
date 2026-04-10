"""
MCP Server for Oracle Database Tools
Exposes database search and describe capabilities via Model Context Protocol
"""
import sys
import os
from pathlib import Path

# Add the services directory to the path so we can import OracleQueryService
services_path = Path(__file__).parent.parent / "services" / "dataObjectQueryService"
sys.path.insert(0, str(services_path))

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent
from dotenv import load_dotenv

# Load environment variables from src/config/.env
load_dotenv(Path(__file__).parent.parent / "config" / ".env")

# Import the Oracle Query Service
from oracle_query_service import OracleQueryService

# Create the MCP server
server = Server("oracle-database-tools")


@server.list_tools()
async def list_tools() -> list[Tool]:
    """List available database tools"""
    return [
        Tool(
            name="search_database_objects",
            description="Search for database objects (tables, views) matching a pattern. Use this to find relevant tables before describing them. Returns a list of matching objects with their schema and type.",
            inputSchema={
                "type": "object",
                "properties": {
                    "pattern": {
                        "type": "string",
                        "description": "Search pattern to find objects. Example: 'patient' finds objects like PATIENT, PAT_ENC, etc."
                    },
                    "object_type": {
                        "type": "string",
                        "description": "Optional: Filter by object type (TABLE, VIEW). If not specified, searches both tables and views.",
                        "enum": ["TABLE", "VIEW"]
                    },
                    "owner": {
                        "type": "string",
                        "description": "Optional: Filter by schema owner (e.g., 'CLARITY'). If not specified, searches all accessible schemas."
                    }
                },
                "required": ["pattern"]
            }
        ),
        Tool(
            name="describe_database_object",
            description="Get the structure/definition of a database table or view. Returns column names, data types, and nullable constraints. Use after search_database_objects to get details about specific tables.",
            inputSchema={
                "type": "object",
                "properties": {
                    "object_name": {
                        "type": "string",
                        "description": "Name of the database object. Can be schema-qualified (e.g., 'CLARITY.PATIENT') or just the object name."
                    },
                    "owner": {
                        "type": "string",
                        "description": "Optional: Schema owner if not specified in object_name."
                    }
                },
                "required": ["object_name"]
            }
        )
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    """Handle tool calls"""
    
    if name == "search_database_objects":
        return await handle_search(arguments)
    elif name == "describe_database_object":
        return await handle_describe(arguments)
    else:
        return [TextContent(type="text", text=f"Unknown tool: {name}")]


async def handle_search(arguments: dict) -> list[TextContent]:
    """Handle search_database_objects tool call"""
    pattern = arguments.get("pattern", "")
    object_type = arguments.get("object_type")
    owner = arguments.get("owner")
    
    if not pattern:
        return [TextContent(type="text", text="Error: 'pattern' parameter is required")]
    
    try:
        # Create service instance and execute search
        service = OracleQueryService()
        service.connect()
        
        try:
            results = service.search_objects(
                pattern=pattern,
                object_type=object_type,
                owner=owner
            )
            
            if not results:
                return [TextContent(
                    type="text",
                    text=f"No database objects found matching pattern '{pattern}'"
                )]
            
            # Format results
            output = f"Found {len(results)} database object(s) matching '{pattern}':\n\n"
            output += "\n".join(results)
            
            return [TextContent(type="text", text=output)]
            
        finally:
            service.disconnect()
            
    except ValueError as e:
        # Configuration errors (missing env vars)
        return [TextContent(
            type="text",
            text=f"Configuration Error: {str(e)}\n\nPlease ensure Oracle connection environment variables are set."
        )]
    except Exception as e:
        return [TextContent(
            type="text",
            text=f"Database Error: {str(e)}\n\nPlease check database connectivity and permissions."
        )]


async def handle_describe(arguments: dict) -> list[TextContent]:
    """Handle describe_database_object tool call"""
    object_name = arguments.get("object_name", "")
    owner = arguments.get("owner")
    
    if not object_name:
        return [TextContent(type="text", text="Error: 'object_name' parameter is required")]
    
    try:
        # Create service instance and execute describe
        service = OracleQueryService()
        service.connect()
        
        try:
            result = service.describe_object(
                object_name=object_name,
                owner=owner
            )
            
            # Add context header
            display_name = f"{owner}.{object_name}" if owner else object_name
            output = f"Structure of {display_name.upper()}:\n\n{result}"
            
            return [TextContent(type="text", text=output)]
            
        finally:
            service.disconnect()
            
    except ValueError as e:
        # Configuration errors (missing env vars)
        return [TextContent(
            type="text",
            text=f"Configuration Error: {str(e)}\n\nPlease ensure Oracle connection environment variables are set."
        )]
    except Exception as e:
        return [TextContent(
            type="text",
            text=f"Database Error: {str(e)}\n\nPlease check database connectivity and permissions."
        )]


async def main():
    """Run the MCP server"""
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options()
        )


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
