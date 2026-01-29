# Oracle Database Query Service

A Python service for querying Oracle database object information using DESCRIBE functionality.

## Setup

### 1. Create Virtual Environment

```powershell
# Navigate to the service directory
cd src\services\dataObjectQueryService

# Create virtual environment
python -m venv venv

# Activate virtual environment
.\venv\Scripts\Activate.ps1
```

### 2. Install Dependencies

```powershell
# Install required packages
pip install -r requirements.txt
```

### 3. Configure Database Connection

```powershell
# Copy the example environment file
copy .env.example .env

# Edit .env with your actual Oracle database credentials
```

Update the `.env` file with your Oracle database connection details:
- `ORACLE_USERNAME`: Your Oracle database username
- `ORACLE_PASSWORD`: Your Oracle database password
- `ORACLE_HOST`: Oracle database host/IP address
- `ORACLE_PORT`: Oracle database port (default: 1521)
- `ORACLE_SERVICE_NAME`: Oracle service name

## Usage

### Basic Usage

```python
from oracle_query_service import OracleQueryService

# Create service instance
service = OracleQueryService()

try:
    # Connect to database
    service.connect()
    
    # Describe a table - returns formatted string
    result = service.describe_object('EMPLOYEES')
    print(result)
    
    # Output:
    # Name          Null? Type         
    # ------------- ----- ------------ 
    # MRN                 VARCHAR2(20) 
    # PAT_BIRTHDATE       DATE         
    # CREATE_DATE         DATE  
    
finally:
    service.disconnect()
```

### Using Context Manager

```python
from oracle_query_service import OracleQueryService

# Automatically handles connection and disconnection
with OracleQueryService() as service:
    result = service.describe_object('DEPARTMENTS', owner='HR')
    
    # Use the string result for LLM context
    llm_context = f"Database table structure:\n{result}"
    print(llm_context)
```

### Command Line Usage

```powershell
# Run the service interactively
python oracle_query_service.py
```

## Response Format

The `describe_object` method returns a formatted string similar to SQL*Plus DESCRIBE output:

```
Name          Null? Type         
------------- ----- ------------ 
MRN                 VARCHAR2(20) 
PAT_BIRTHDATE       DATE         
CREATE_DATE         DATE         
EMPLOYEE_ID   NOT NULL NUMBER(10)
```

This format is ideal for providing database schema context to LLMs.

## Features

- ✅ Query Oracle database object structure
- ✅ Support for tables, views, and other database objects
- ✅ Retrieve column information (name, type, constraints)
- ✅ Get object metadata (creation date, status, owner)
- ✅ Context manager support for automatic connection handling
- ✅ Batch querying of multiple objects
- ✅ Secure credential management via .env file

## Requirements

- Python 3.8+
- Oracle Database (tested with 11g, 12c, 19c, 21c)
- Network access to Oracle database
Returns simple string format (perfect for LLM context)
- ✅ Support for tables, views, and other database objects
- ✅ Retrieve column information (name, type, nullable constraints)
- ✅ Context manager support for automatic connection handling
If you encounter connection issues:
1. Verify your Oracle database is accessible
2. Check firewall settings
3. Confirm the service name is correct
4. Ensure Oracle client libraries are installed (if required)

### Oracle Client Installation

For some Oracle database versions, you may need Oracle Instant Client:

```powershell
# Download Oracle Instant Client from Oracle website
# Install and add to PATH
```

Or use the python-oracledb thin mode (default, no client needed).
