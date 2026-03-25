-- =============================================================================
-- 01-create-schema.sql
-- Creates the CLARITY database and Epic Clarity-style tables for SQL Server.
-- Equivalent schema to the Oracle test database (database/init-scripts/).
-- =============================================================================

-- Create database ---------------------------------------------------------------
IF NOT EXISTS (SELECT name FROM sys.databases WHERE name = N'CLARITY')
BEGIN
    CREATE DATABASE CLARITY;
END
GO

USE CLARITY;
GO

-- =============================================================================
-- CLARITY_DEP — Departments / Clinics
-- =============================================================================
IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'CLARITY_DEP' AND schema_id = SCHEMA_ID('dbo'))
BEGIN
    CREATE TABLE dbo.CLARITY_DEP (
        DEPARTMENT_ID   INT          NOT NULL,
        DEPARTMENT_NAME VARCHAR(100) NULL,
        LOCATION        VARCHAR(100) NULL,
        SPECIALTY       VARCHAR(100) NULL,
        CONSTRAINT PK_CLARITY_DEP PRIMARY KEY (DEPARTMENT_ID)
    );

    EXEC sys.sp_addextendedproperty
        @name  = N'MS_Description',
        @value = N'Departments and clinic locations within the healthcare system.',
        @level0type = N'SCHEMA', @level0name = N'dbo',
        @level1type = N'TABLE',  @level1name = N'CLARITY_DEP';
END
GO

-- =============================================================================
-- PATIENT — Patient demographics
-- =============================================================================
IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'PATIENT' AND schema_id = SCHEMA_ID('dbo'))
BEGIN
    CREATE TABLE dbo.PATIENT (
        PAT_ID       INT          NOT NULL,
        PAT_MRN_ID   VARCHAR(20)  NULL,
        PAT_NAME     VARCHAR(100) NULL,
        BIRTH_DATE   DATE         NULL,
        SEX          VARCHAR(10)  NULL,
        ADDRESS_LINE VARCHAR(200) NULL,
        CITY         VARCHAR(100) NULL,
        STATE_C      VARCHAR(10)  NULL,
        CONSTRAINT PK_PATIENT PRIMARY KEY (PAT_ID),
        CONSTRAINT UQ_PATIENT_MRN UNIQUE (PAT_MRN_ID)
    );

    EXEC sys.sp_addextendedproperty
        @name  = N'MS_Description',
        @value = N'Patient demographic information including name, date of birth, and address.',
        @level0type = N'SCHEMA', @level0name = N'dbo',
        @level1type = N'TABLE',  @level1name = N'PATIENT';
END
GO

-- =============================================================================
-- PAT_ENC — Patient encounters / visits
-- =============================================================================
IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'PAT_ENC' AND schema_id = SCHEMA_ID('dbo'))
BEGIN
    CREATE TABLE dbo.PAT_ENC (
        PAT_ENC_CSN_ID INT          NOT NULL,
        PAT_ID         INT          NULL,
        CONTACT_DATE   DATE         NULL,
        DEPARTMENT_ID  INT          NULL,
        VISIT_TYPE     VARCHAR(100) NULL,
        PROVIDER_ID    INT          NULL,
        CONSTRAINT PK_PAT_ENC PRIMARY KEY (PAT_ENC_CSN_ID),
        CONSTRAINT FK_PAT_ENC_PATIENT FOREIGN KEY (PAT_ID)
            REFERENCES dbo.PATIENT (PAT_ID),
        CONSTRAINT FK_PAT_ENC_DEP FOREIGN KEY (DEPARTMENT_ID)
            REFERENCES dbo.CLARITY_DEP (DEPARTMENT_ID)
    );

    CREATE INDEX IX_PAT_ENC_PAT_ID       ON dbo.PAT_ENC (PAT_ID);
    CREATE INDEX IX_PAT_ENC_CONTACT_DATE ON dbo.PAT_ENC (CONTACT_DATE);

    EXEC sys.sp_addextendedproperty
        @name  = N'MS_Description',
        @value = N'Patient encounters (visits). Each row is one contact with the healthcare system.',
        @level0type = N'SCHEMA', @level0name = N'dbo',
        @level1type = N'TABLE',  @level1name = N'PAT_ENC';
END
GO

-- =============================================================================
-- ORDER_PROC — Procedure orders (labs, imaging, etc.)
-- =============================================================================
IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'ORDER_PROC' AND schema_id = SCHEMA_ID('dbo'))
BEGIN
    CREATE TABLE dbo.ORDER_PROC (
        ORDER_PROC_ID  INT          NOT NULL,
        PAT_ENC_CSN_ID INT          NULL,
        PROC_CODE      VARCHAR(20)  NULL,
        PROC_NAME      VARCHAR(200) NULL,
        ORDER_DATE     DATE         NULL,
        ORDER_STATUS   VARCHAR(50)  NULL,
        CONSTRAINT PK_ORDER_PROC PRIMARY KEY (ORDER_PROC_ID),
        CONSTRAINT FK_ORDER_PROC_ENC FOREIGN KEY (PAT_ENC_CSN_ID)
            REFERENCES dbo.PAT_ENC (PAT_ENC_CSN_ID)
    );

    CREATE INDEX IX_ORDER_PROC_ENC ON dbo.ORDER_PROC (PAT_ENC_CSN_ID);

    EXEC sys.sp_addextendedproperty
        @name  = N'MS_Description',
        @value = N'Procedure orders such as lab tests and imaging requests.',
        @level0type = N'SCHEMA', @level0name = N'dbo',
        @level1type = N'TABLE',  @level1name = N'ORDER_PROC';
END
GO

-- =============================================================================
-- CLARITY_MEDICATION — Medication master list
-- =============================================================================
IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'CLARITY_MEDICATION' AND schema_id = SCHEMA_ID('dbo'))
BEGIN
    CREATE TABLE dbo.CLARITY_MEDICATION (
        MEDICATION_ID INT          NOT NULL,
        NAME          VARCHAR(200) NULL,
        GENERIC_NAME  VARCHAR(200) NULL,
        DRUG_CLASS    VARCHAR(100) NULL,
        CONSTRAINT PK_CLARITY_MEDICATION PRIMARY KEY (MEDICATION_ID)
    );

    EXEC sys.sp_addextendedproperty
        @name  = N'MS_Description',
        @value = N'Medication master catalogue including generic and brand names.',
        @level0type = N'SCHEMA', @level0name = N'dbo',
        @level1type = N'TABLE',  @level1name = N'CLARITY_MEDICATION';
END
GO

-- =============================================================================
-- ORDER_MED — Medication orders
-- =============================================================================
IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'ORDER_MED' AND schema_id = SCHEMA_ID('dbo'))
BEGIN
    CREATE TABLE dbo.ORDER_MED (
        ORDER_MED_ID   INT          NOT NULL,
        PAT_ENC_CSN_ID INT          NULL,
        MEDICATION_ID  INT          NULL,
        SIG            VARCHAR(500) NULL,
        QUANTITY       DECIMAL(10,2)NULL,
        REFILLS        INT          NULL,
        ORDER_DATE     DATE         NULL,
        CONSTRAINT PK_ORDER_MED PRIMARY KEY (ORDER_MED_ID),
        CONSTRAINT FK_ORDER_MED_ENC FOREIGN KEY (PAT_ENC_CSN_ID)
            REFERENCES dbo.PAT_ENC (PAT_ENC_CSN_ID),
        CONSTRAINT FK_ORDER_MED_MED FOREIGN KEY (MEDICATION_ID)
            REFERENCES dbo.CLARITY_MEDICATION (MEDICATION_ID)
    );

    CREATE INDEX IX_ORDER_MED_ENC ON dbo.ORDER_MED (PAT_ENC_CSN_ID);
    CREATE INDEX IX_ORDER_MED_MED ON dbo.ORDER_MED (MEDICATION_ID);

    EXEC sys.sp_addextendedproperty
        @name  = N'MS_Description',
        @value = N'Medication orders placed during patient encounters.',
        @level0type = N'SCHEMA', @level0name = N'dbo',
        @level1type = N'TABLE',  @level1name = N'ORDER_MED';
END
GO

PRINT 'Schema created successfully.';
GO
