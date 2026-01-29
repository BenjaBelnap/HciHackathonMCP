# Hello World OpenAPI Tool Server

A simple FastAPI server that provides OpenAPI-compliant tools for Open-WebUI.

## Installation

```bash
pip install -r requirements.txt
```

## Running

```bash
python server.py
```

The server will run on http://localhost:8001

## Endpoints

- `GET /` - Root endpoint with server info
- `GET /docs` - Interactive Swagger UI documentation
- `GET /openapi.json` - OpenAPI specification
- `POST /greet` - Greet someone in different languages
- `POST /echo` - Echo back a message
- `GET /health` - Health check endpoint

## Usage with Open-WebUI

1. Start the server: `python server.py`
2. In Open-WebUI, go to settings and add an external tool
3. Use the URL: `http://host.docker.internal:8001/openapi.json`
4. Open-WebUI will automatically discover and import the tools

## Example Tool Calls

### Greet
```json
{
  "name": "Alice",
  "language": "spanish"
}
```

### Echo
```json
{
  "message": "Hello World!"
}
```
