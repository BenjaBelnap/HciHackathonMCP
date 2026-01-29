"""
Simple OpenAPI-compliant server for Open-WebUI external tools
"""
from fastapi import FastAPI
from pydantic import BaseModel, Field
from typing import Optional

app = FastAPI(
    title="Hello World Tool Server",
    description="A simple server with tools for Open-WebUI",
    version="1.0.0"
)

class GreetRequest(BaseModel):
    name: str = Field(..., description="The name to greet")
    language: Optional[str] = Field("english", description="Language for greeting (english, spanish, french)")

class GreetResponse(BaseModel):
    greeting: str
    
class EchoRequest(BaseModel):
    message: str = Field(..., description="The message to echo back")

class EchoResponse(BaseModel):
    echoed_message: str

@app.get("/")
def root():
    return {
        "message": "Hello World Tool Server",
        "docs": "/docs",
        "openapi": "/openapi.json"
    }

@app.post("/greet", response_model=GreetResponse, tags=["tools"])
def greet(request: GreetRequest):
    """
    Greet someone in different languages
    """
    greetings = {
        "english": f"Hello, {request.name}!",
        "spanish": f"¡Hola, {request.name}!",
        "french": f"Bonjour, {request.name}!"
    }
    greeting = greetings.get(request.language.lower(), f"Hello, {request.name}!")
    return GreetResponse(greeting=greeting)

@app.post("/echo", response_model=EchoResponse, tags=["tools"])
def echo(request: EchoRequest):
    """
    Echo back the provided message
    """
    return EchoResponse(echoed_message=request.message)

@app.get("/health")
def health():
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
