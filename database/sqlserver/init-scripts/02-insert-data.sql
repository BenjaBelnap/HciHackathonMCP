-- =============================================================================
-- 02-insert-data.sql
-- Inserts mock Epic Clarity–style data into the SQL Server CLARITY database.
-- Equivalent data set to database/init-scripts/03-insert-data.sql (Oracle).
-- =============================================================================

USE CLARITY;
GO

-- =============================================================================
-- Departments
-- =============================================================================
IF NOT EXISTS (SELECT 1 FROM dbo.CLARITY_DEP WHERE DEPARTMENT_ID = 1)
BEGIN
    INSERT INTO dbo.CLARITY_DEP (DEPARTMENT_ID, DEPARTMENT_NAME, LOCATION, SPECIALTY)
    VALUES
        (1, 'Internal Medicine',     'Building A, Floor 2', 'Internal Medicine'),
        (2, 'Cardiology',            'Building B, Floor 3', 'Cardiology'),
        (3, 'Emergency Department',  'Building C, Floor 1', 'Emergency Medicine'),
        (4, 'Orthopedics',           'Building D, Floor 2', 'Orthopedics'),
        (5, 'Pediatrics',            'Building E, Floor 1', 'Pediatrics');
END
GO

-- =============================================================================
-- Patients
-- =============================================================================
IF NOT EXISTS (SELECT 1 FROM dbo.PATIENT WHERE PAT_ID = 1)
BEGIN
    INSERT INTO dbo.PATIENT (PAT_ID, PAT_MRN_ID, PAT_NAME, BIRTH_DATE, SEX, ADDRESS_LINE, CITY, STATE_C)
    VALUES
        (1, 'MRN001', 'Smith, John A',     '1965-03-15', 'Male',   '123 Oak Street',   'Springfield', 'IL'),
        (2, 'MRN002', 'Johnson, Mary B',   '1978-07-22', 'Female', '456 Maple Ave',    'Shelbyville', 'IL'),
        (3, 'MRN003', 'Williams, Robert C','1952-11-08', 'Male',   '789 Elm Road',     'Capital City','IL'),
        (4, 'MRN004', 'Brown, Patricia D', '1989-04-30', 'Female', '321 Pine Lane',    'Ogdenville',  'IL'),
        (5, 'MRN005', 'Jones, Michael E',  '1971-09-14', 'Male',   '654 Cedar Blvd',   'North Haverbrook','IL'),
        (6, 'MRN006', 'Garcia, Linda F',   '1983-12-05', 'Female', '987 Birch Court',  'Springfield', 'IL'),
        (7, 'MRN007', 'Martinez, David G', '1945-06-20', 'Male',   '147 Spruce Way',   'Shelbyville', 'IL'),
        (8, 'MRN008', 'Anderson, Susan H', '1995-02-28', 'Female', '258 Willow Drive', 'Capital City','IL');
END
GO

-- =============================================================================
-- Patient encounters
-- =============================================================================
IF NOT EXISTS (SELECT 1 FROM dbo.PAT_ENC WHERE PAT_ENC_CSN_ID = 1001)
BEGIN
    INSERT INTO dbo.PAT_ENC (PAT_ENC_CSN_ID, PAT_ID, CONTACT_DATE, DEPARTMENT_ID, VISIT_TYPE, PROVIDER_ID)
    VALUES
        (1001, 1, '2024-01-10', 1, 'Office Visit',     101),
        (1002, 2, '2024-01-15', 2, 'Cardiology Consult',102),
        (1003, 3, '2024-01-20', 3, 'Emergency Visit',  103),
        (1004, 4, '2024-02-05', 1, 'Follow-up',        101),
        (1005, 5, '2024-02-10', 4, 'Orthopedic Consult',104),
        (1006, 6, '2024-02-20', 5, 'Well Child Visit', 105),
        (1007, 7, '2024-03-01', 2, 'Cardiology Follow-up',102),
        (1008, 8, '2024-03-15', 1, 'New Patient Visit',101);
END
GO

-- =============================================================================
-- Medications
-- =============================================================================
IF NOT EXISTS (SELECT 1 FROM dbo.CLARITY_MEDICATION WHERE MEDICATION_ID = 1)
BEGIN
    INSERT INTO dbo.CLARITY_MEDICATION (MEDICATION_ID, NAME, GENERIC_NAME, DRUG_CLASS)
    VALUES
        (1, 'Prinivil',     'Lisinopril',    'ACE Inhibitor'),
        (2, 'Glucophage',   'Metformin',     'Biguanide'),
        (3, 'Lipitor',      'Atorvastatin',  'Statin'),
        (4, 'Amoxil',       'Amoxicillin',   'Antibiotic'),
        (5, 'Vicodin',      'Hydrocodone',   'Opioid Analgesic');
END
GO

-- =============================================================================
-- Procedure orders
-- =============================================================================
IF NOT EXISTS (SELECT 1 FROM dbo.ORDER_PROC WHERE ORDER_PROC_ID = 5001)
BEGIN
    INSERT INTO dbo.ORDER_PROC (ORDER_PROC_ID, PAT_ENC_CSN_ID, PROC_CODE, PROC_NAME, ORDER_DATE, ORDER_STATUS)
    VALUES
        (5001, 1001, 'ECG001',  'Electrocardiogram',      '2024-01-10', 'Completed'),
        (5002, 1001, 'LAB002',  'Lipid Panel',            '2024-01-10', 'Completed'),
        (5003, 1002, 'LAB003',  'Complete Blood Count',   '2024-01-15', 'Completed'),
        (5004, 1003, 'IMG001',  'Chest X-Ray',            '2024-01-20', 'Completed'),
        (5005, 1005, 'IMG002',  'MRI Knee',               '2024-02-10', 'Completed'),
        (5006, 1007, 'IMG003',  'CT Chest',               '2024-03-01', 'Pending');
END
GO

-- =============================================================================
-- Medication orders
-- =============================================================================
IF NOT EXISTS (SELECT 1 FROM dbo.ORDER_MED WHERE ORDER_MED_ID = 8001)
BEGIN
    INSERT INTO dbo.ORDER_MED (ORDER_MED_ID, PAT_ENC_CSN_ID, MEDICATION_ID, SIG, QUANTITY, REFILLS, ORDER_DATE)
    VALUES
        (8001, 1001, 1, 'Take 10mg once daily',             30, 3, '2024-01-10'),
        (8002, 1001, 2, 'Take 500mg twice daily with meals',60, 3, '2024-01-10'),
        (8003, 1002, 3, 'Take 40mg once daily at bedtime',  30, 6, '2024-01-15'),
        (8004, 1003, 4, 'Take 500mg three times daily',     21, 0, '2024-01-20'),
        (8005, 1007, 1, 'Take 20mg once daily',             30, 6, '2024-03-01');
END
GO

PRINT 'Test data inserted successfully.';
GO
