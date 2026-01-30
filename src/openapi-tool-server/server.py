"""
Oracle Database Query Tool Server for Open-WebUI
"""
import sys
import os
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import Optional

# Add the services directory to the Python path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'services', 'dataObjectQueryService'))

from oracle_query_service import OracleQueryService

app = FastAPI(
    title="Oracle Database Tool Server",
    description="A server with Oracle database query tools for Open-WebUI",
    version="1.0.0"
)

class DescribeObjectRequest(BaseModel):
    object_name: str = Field(..., description="Name of the Oracle database object (table, view, etc.) to describe")
    owner: Optional[str] = Field(None, description="Optional schema owner (defaults to current user)")

class DescribeObjectResponse(BaseModel):
    result: str
    object_name: str
    owner: Optional[str]

class SearchObjectsRequest(BaseModel):
    pattern: str = Field(..., description="Search pattern for object names (e.g., 'patient' will find all objects with 'patient' in the name)")
    object_type: Optional[str] = Field(None, description="Optional filter by object type (TABLE, VIEW, SEQUENCE, etc.)")
    owner: Optional[str] = Field(None, description="Optional schema owner filter")

class SearchObjectsResponse(BaseModel):
    objects: list[str]
    count: int
    pattern: str

@app.get("/")
def root():
    return {
        "message": "Oracle Database Tool Server",
        "docs": "/docs",
        "openapi": "/openapi.json"
    }

@app.post("/search_objects", response_model=SearchObjectsResponse, tags=["tools"])
def search_objects(request: SearchObjectsRequest):
    """
    Search for Oracle database objects matching a pattern
    Use this to discover objects before describing them
    """
    try:
        service = OracleQueryService()
        service.connect()
        
        objects = service.search_objects(
            pattern=request.pattern,
            object_type=request.object_type,
            owner=request.owner
        )
        
        service.disconnect()
        
        return SearchObjectsResponse(
            objects=objects,
            count=len(objects),
            pattern=request.pattern
        )
    except Exception as e:
        error_message = (
            f"ERROR occurred while searching for database objects with pattern '{request.pattern}': {str(e)}\n\n"
            f"INSTRUCTIONS FOR LLM: Please inform the user about this error in a clear and helpful way. "
            f"Explain what went wrong and suggest potential solutions such as:\n"
            f"- Verify database connectivity is working\n"
            f"- Check if the schema/owner name is correct (if specified)\n"
            f"- Ensure you have appropriate permissions to query the data dictionary\n"
            f"- Try a different search pattern"
        )
        raise HTTPException(status_code=500, detail=error_message)

@app.post("/describe_object", response_model=DescribeObjectResponse, tags=["tools"])
def describe_object(request: DescribeObjectRequest):
    """
    Describe an Oracle database object (table, view, etc.)
    Returns column information similar to SQL*Plus DESCRIBE command
    """
    try:
        service = OracleQueryService()
        service.connect()
        
        result = service.describe_object(
            object_name=request.object_name,
            owner=request.owner
        )
        
        service.disconnect()
        
        return DescribeObjectResponse(
            result=result,
            object_name=request.object_name,
            owner=request.owner
        )
    except Exception as e:
        error_message = (
            f"ERROR occurred while describing database object '{request.object_name}': {str(e)}\n\n"
            f"INSTRUCTIONS FOR LLM: Please inform the user about this error in a clear and helpful way. "
            f"Explain what went wrong and suggest potential solutions such as:\n"
            f"- Verify the object name is correct and exists in the database\n"
            f"- Check if the schema/owner name is correct (if specified)\n"
            f"- Ensure database connectivity is working\n"
            f"- Verify you have appropriate permissions to access this object"
        )
        raise HTTPException(status_code=500, detail=error_message)

@app.get("/health")
def health():
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
