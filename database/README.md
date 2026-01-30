# Oracle Database with Epic Clarity Schema

This directory contains a Docker Compose configuration to spin up an Oracle Database XE instance preloaded with Epic Clarity schema tables and mock patient data for testing and development.

## Quick Start

### 1. Start the Database

```powershell
cd database
docker compose up -d
```

The database will take about 60-90 seconds to fully initialize. You can monitor the logs:

```powershell
docker compose logs -f
```

Wait for the message indicating all initialization scripts have completed successfully.

### 2. Connection Details

Once the container is healthy, connect using:

- **Host**: `localhost`
- **Port**: `1521`
- **Service Name**: `XEPDB1`
- **Username**: `CLARITY`
- **Password**: `Clarity123`

**Connection String Example** (for oracledb Python library):
```python
import oracledb

dsn = oracledb.makedsn("localhost", 1521, service_name="XEPDB1")
connection = oracledb.connect(user="CLARITY", password="Clarity123", dsn=dsn)
```

### 3. Update Service Configuration

To connect the [oracle_query_service.py](../src/services/dataObjectQueryService/oracle_query_service.py) to this database, update [../src/services/dataObjectQueryService/.env](../src/services/dataObjectQueryService/.env):

```env
ORACLE_USERNAME=CLARITY
ORACLE_PASSWORD=Clarity123
ORACLE_HOST=localhost
ORACLE_PORT=1521
ORACLE_SERVICE_NAME=XEPDB1
```

## Epic Clarity Schema Overview

The database includes the following core Epic Clarity tables with mock data:

### Tables

| Table | Description | Record Count |
|-------|-------------|--------------|
| **CLARITY_DEP** | Hospital departments and clinics | 5 departments |
| **PATIENT** | Patient demographics | 8 patients |
| **PAT_ENC** | Patient encounters (visits) | 8 encounters |
| **ORDER_PROC** | Procedure orders (labs, imaging) | 6 orders |
| **CLARITY_MEDICATION** | Medication master file | 5 medications |
| **ORDER_MED** | Medication orders | 5 orders |

### Relationships

```
CLARITY_DEP (departments)
    ↓
PAT_ENC (encounters) ← PATIENT
    ↓
ORDER_PROC (procedures)

CLARITY_MEDICATION (meds)
    ↓
ORDER_MED (med orders) ← PAT_ENC
```

### Sample Queries

**List all patients:**
```sql
SELECT PAT_ID, PAT_MRN_ID, PAT_NAME, BIRTH_DATE FROM PATIENT;
```

**Get patient encounters:**
```sql
SELECT e.PAT_ENC_CSN_ID, p.PAT_NAME, e.CONTACT_DATE, d.DEPARTMENT_NAME
FROM PAT_ENC e
JOIN PATIENT p ON e.PAT_ID = p.PAT_ID
JOIN CLARITY_DEP d ON e.DEPARTMENT_ID = d.DEPARTMENT_ID;
```

**Find procedures for a patient:**
```sql
SELECT p.PAT_NAME, op.PROC_NAME, op.ORDER_TIME, op.RESULT_STATUS_C
FROM ORDER_PROC op
JOIN PAT_ENC e ON op.PAT_ENC_CSN_ID = e.PAT_ENC_CSN_ID
JOIN PATIENT p ON e.PAT_ID = p.PAT_ID
WHERE p.PAT_MRN_ID = 'MRN001234';
```

### Testing with oracle_query_service

Once configured, test the connection:

```powershell
cd ..\src\services\dataObjectQueryService
& ..\..\..\.venv\Scripts\python.exe -c "from oracle_query_service import OracleQueryService; service = OracleQueryService(); service.connect(); print(service.describe_object('PATIENT')); service.disconnect()"
```

Expected output:
```
Name              Null? Type         
----------------- ----- ------------ 
PAT_ID                  VARCHAR2(18) 
PAT_MRN_ID              VARCHAR2(50) 
PAT_NAME                VARCHAR2(254)
PAT_FIRST_NAME          VARCHAR2(100)
PAT_LAST_NAME           VARCHAR2(100)
BIRTH_DATE              DATE         
...
```

## Docker Management

### Stop the Database
```powershell
docker compose stop
```

### Start the Database (after stopping)
```powershell
docker compose start
```

### Restart the Database
```powershell
docker compose restart
```

### View Logs
```powershell
docker compose logs -f oracle-db
```

### Remove Container and Data
```powershell
docker compose down -v
```

**Warning**: The `-v` flag deletes all database data. Omit it to preserve data.

## Schema Details

### PATIENT Table
Core patient demographics including MRN, name, date of birth, gender, and address.

**Key Columns:**
- `PAT_ID` (PK) - Internal patient identifier
- `PAT_MRN_ID` (UK) - Medical Record Number
- `PAT_NAME` - Full name (Last, First format)
- `BIRTH_DATE` - Date of birth

### PAT_ENC Table
Patient encounters representing visits, admissions, and procedures.

**Key Columns:**
- `PAT_ENC_CSN_ID` (PK) - Contact Serial Number
- `PAT_ID` (FK) - References PATIENT
- `DEPARTMENT_ID` (FK) - References CLARITY_DEP
- `CONTACT_DATE` - Date of encounter

### ORDER_PROC Table
Procedure orders including labs, imaging, and other clinical procedures.

**Key Columns:**
- `ORDER_PROC_ID` (PK) - Order identifier
- `PAT_ENC_CSN_ID` (FK) - References PAT_ENC
- `PROC_CODE` - Procedure code
- `ORDER_TIME` - When ordered
- `RESULT_TIME` - When resulted

### CLARITY_MEDICATION Table
Master medication reference file.

**Key Columns:**
- `MEDICATION_ID` (PK) - Medication identifier
- `NAME` - Brand/formulation name
- `GENERIC_NAME` - Generic drug name
- `PHARM_CLASS` - Pharmacologic class

### ORDER_MED Table
Medication orders placed for patients.

**Key Columns:**
- `ORDER_MED_ID` (PK) - Order identifier
- `PAT_ENC_CSN_ID` (FK) - References PAT_ENC
- `MEDICATION_ID` (FK) - References CLARITY_MEDICATION
- `HV_DISCRETE_DOSE` - Dose amount
- `FREQ_NAME` - Frequency (e.g., "Once Daily")

## Troubleshooting

### Database Won't Start
Check if port 1521 is already in use:
```powershell
netstat -ano | findstr :1521
```

### Initialization Scripts Failed
View the initialization logs:
```powershell
docker compose logs oracle-db | Select-String "CREATE\|INSERT\|ERROR"
```

### Can't Connect from Application
1. Verify container is healthy: `docker compose ps`
2. Test connection: `docker compose exec oracle-db sqlplus CLARITY/Clarity123@XEPDB1`
3. Check network: `docker compose exec oracle-db lsnrctl status`

### Reset Database
To start fresh with a clean database:
```powershell
docker compose down -v
docker compose up -d
```

## Architecture

- **Image**: `gvenzl/oracle-xe:latest` (Oracle Database 21c Express Edition)
- **Container**: Lightweight, free Oracle database
- **Initialization**: SQL scripts in [init-scripts/](init-scripts/) run automatically on first startup
- **Volume**: `oracle_data` persists database files across container restarts
- **Port**: 1521 exposed for external connections

## Notes

- This is a **test/development database** with hardcoded credentials
- **Do not use in production** without proper security configuration
- The CLARITY user has full privileges within the XEPDB1 pluggable database
- Mock data represents realistic Epic Clarity structures but is fictional
- Database uses approximately 2-3 GB of disk space

## Additional Resources

- [Oracle Database Express Edition Documentation](https://docs.oracle.com/en/database/oracle/oracle-database/21/index.html)
- [Epic Clarity Data Model Overview](https://galaxy.epic.com/) (requires Epic UserWeb access)
- [python-oracledb Documentation](https://python-oracledb.readthedocs.io/)
