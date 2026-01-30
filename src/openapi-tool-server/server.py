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
    pattern: str = Field(
        ..., 
        description="Search pattern for object names (e.g., 'patient' will find all objects with 'patient' in the name)",
        examples=["patient", "emp", "order"]
    )
    object_type: Optional[str] = Field(
        None, 
        description="Optional filter by object type (TABLE, VIEW, SEQUENCE, etc.)",
        examples=["TABLE", "VIEW"]
    )
    owner: Optional[str] = Field(
        None, 
        description="Optional schema owner filter",
        examples=["MYSCHEMA", "HR"]
    )

class SearchObjectsResponse(BaseModel):
    objects: list[str]
    count: int
    pattern: str

class SearchAndDescribeRequest(BaseModel):
    pattern: str = Field(
        ..., 
        description="Search pattern for object names (e.g., 'patient' will find all objects with 'patient' in the name)",
        examples=["patient", "emp", "order"]
    )
    object_type: Optional[str] = Field(
        None, 
        description="Optional filter by object type (TABLE, VIEW, SEQUENCE, etc.)",
        examples=["TABLE", "VIEW"]
    )
    owner: Optional[str] = Field(
        None, 
        description="Optional schema owner filter",
        examples=["MYSCHEMA", "HR"]
    )
    describe_all: bool = Field(
        False, 
        description="If True, describes all matching objects. If False, only describes the first match"
    )

class SearchAndDescribeResponse(BaseModel):
    objects: list[str]
    count: int
    pattern: str
    descriptions: dict[str, str]

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
    Search for Oracle database objects matching a pattern.
    Use this to discover objects before describing them.
    
    Example request body:
    {
        "pattern": "patient",
        "object_type": "TABLE",
        "owner": "MYSCHEMA"
    }
    
    Or minimal:
    {
        "pattern": "patient"
    }
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
    Describe an Oracle database object (table, view, etc.).
    Returns column information similar to SQL*Plus DESCRIBE command.
    
    Example request body:
    {
        "object_name": "PATIENTS",
        "owner": "MYSCHEMA"
    }
    
    Or use schema-qualified name:
    {
        "object_name": "MYSCHEMA.PATIENTS"
    }
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

@app.post("/search_and_describe", response_model=SearchAndDescribeResponse, tags=["tools"])
def search_and_describe(request: SearchAndDescribeRequest):
    """
    Search for Oracle database objects matching a pattern and describe them.
    This combines search and describe operations in one step for convenience.
    
    Example request body:
    {
        "pattern": "patient",
        "object_type": "TABLE",
        "owner": "MYSCHEMA",
        "describe_all": false
    }
    
    Or minimal (describes only first match):
    {
        "pattern": "patient"
    }
    
    Note: All parameters must be sent in the request BODY as JSON, not as query parameters.
    """
    try:
        service = OracleQueryService()
        service.connect()
        
        # First, search for matching objects
        objects = service.search_objects(
            pattern=request.pattern,
            object_type=request.object_type,
            owner=request.owner
        )
        
        # Then describe the matching objects
        descriptions = {}
        
        if objects:
            # Determine how many objects to describe
            objects_to_describe = objects if request.describe_all else objects[:1]
            
            for obj_str in objects_to_describe:
                # Parse the object string (format: "Table Name: OWNER.OBJECT_NAME")
                parts = obj_str.split(": ", 1)
                if len(parts) == 2:
                    full_name = parts[1]  # This is "OWNER.OBJECT_NAME"
                    
                    # Describe the object (the service handles schema-qualified names)
                    description = service.describe_object(full_name)
                    descriptions[full_name] = description
        
        service.disconnect()
        
        return SearchAndDescribeResponse(
            objects=objects,
            count=len(objects),
            pattern=request.pattern,
            descriptions=descriptions
        )
    except Exception as e:
        error_message = (
            f"ERROR occurred while finding and describing database objects with pattern '{request.pattern}': {str(e)}\n\n"
            f"INSTRUCTIONS FOR LLM: Please inform the user about this error in a clear and helpful way. "
            f"Explain what went wrong and suggest potential solutions such as:\n"
            f"- Verify database connectivity is working\n"
            f"- Check if the schema/owner name is correct (if specified)\n"
            f"- Ensure you have appropriate permissions to query the data dictionary\n"
            f"- Try a different search pattern\n"
            f"- Check if the matching objects exist and are accessible"
        )
        raise HTTPException(status_code=500, detail=error_message)

@app.get("/health")
def health():
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
