#!/bin/bash
# entrypoint.sh — Start SQL Server, wait until ready, run init scripts.
set -e

SQLCMD=/opt/mssql-tools18/bin/sqlcmd
SA_PASS="${SA_PASSWORD:-SqlPassword123!}"

echo ">>> Starting SQL Server..."
/opt/mssql/bin/sqlservr &
MSSQL_PID=$!

echo ">>> Waiting for SQL Server to accept connections..."
for i in $(seq 1 40); do
    if $SQLCMD -S localhost -U sa -P "$SA_PASS" -Q "SELECT 1" -b -C -l 3 &>/dev/null; then
        echo ">>> SQL Server is ready after ${i} attempts."
        break
    fi
    echo "    Attempt $i — not ready yet, sleeping 3 s..."
    sleep 3
done

# Verify it's actually up before continuing
if ! $SQLCMD -S localhost -U sa -P "$SA_PASS" -Q "SELECT 1" -b -C &>/dev/null; then
    echo "!!! SQL Server did not start in time. Exiting."
    exit 1
fi

echo ">>> Running initialisation scripts..."
for script in $(ls /docker-entrypoint-initdb.d/*.sql 2>/dev/null | sort); do
    echo "    Executing: $script"
    $SQLCMD -S localhost -U sa -P "$SA_PASS" -i "$script" -b -C
    echo "    Done: $script"
done

echo ">>> Initialisation complete. SQL Server is running."
wait $MSSQL_PID
