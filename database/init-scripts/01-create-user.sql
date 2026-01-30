-- Create CLARITY user for Epic Clarity schema
-- This script runs automatically when the Oracle container starts

-- Connect as SYSTEM user (default for init scripts)
ALTER SESSION SET CONTAINER = XEPDB1;

-- Create CLARITY user with password
CREATE USER CLARITY IDENTIFIED BY Clarity123
  DEFAULT TABLESPACE USERS
  TEMPORARY TABLESPACE TEMP
  QUOTA UNLIMITED ON USERS;

-- Grant necessary privileges
GRANT CONNECT TO CLARITY;
GRANT RESOURCE TO CLARITY;
GRANT CREATE VIEW TO CLARITY;
GRANT CREATE SYNONYM TO CLARITY;
GRANT CREATE DATABASE LINK TO CLARITY;
GRANT CREATE SESSION TO CLARITY;

-- Display success message
SELECT 'CLARITY user created successfully' AS STATUS FROM DUAL;
