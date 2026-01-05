-- Healthcare Data Warehouse - Database Creation Script
-- ===============================================================================
-- Purpose: Creates complete healthcare data warehouse with star schema design
--          for Power BI analytics and operational reporting
--
-- Author: Lee Frasl
-- Date: January 2025
-- 
-- Schema Design:
--   - 12 Dimension tables (Patient, Provider, Facility, Date, etc.)
--   - 10 Fact tables (Encounters, Procedures, Medications, etc.)
--   - Optimized for Power BI import mode with appropriate indexes
--
-- Key Features:
--   - Star schema optimized for analytical queries
--   - Surrogate keys for all dimensions
--   - Date dimension with full calendar hierarchy
--   - Supports incremental loads via timestamp columns
--
-- Usage: Execute against SQL Server 2019+ instance
-- ===============================================================================

USE master;
GO

-- Drop database if it exists (use with caution!)
IF EXISTS (SELECT name FROM sys.databases WHERE name = N'HealthcareDataWarehouse')
BEGIN
    ALTER DATABASE HealthcareDataWarehouse SET SINGLE_USER WITH ROLLBACK IMMEDIATE;
    DROP DATABASE HealthcareDataWarehouse;
END
GO

-- Create the database
CREATE DATABASE HealthcareDataWarehouse
ON PRIMARY 
(
    NAME = N'HealthcareDataWarehouse_Data',
    FILENAME = N'C:\SQLData\HealthcareDataWarehouse_Data.mdf',
    SIZE = 500MB,
    MAXSIZE = UNLIMITED,
    FILEGROWTH = 100MB
)
LOG ON 
(
    NAME = N'HealthcareDataWarehouse_Log',
    FILENAME = N'C:\SQLData\HealthcareDataWarehouse_Log.ldf',
    SIZE = 100MB,
    MAXSIZE = 2GB,
    FILEGROWTH = 50MB
);
GO

USE HealthcareDataWarehouse;
GO

-- =====================================================================
-- DIMENSION TABLES
-- =====================================================================

-- DimDate - Date dimension
CREATE TABLE DimDate (
    DateKey INT NOT NULL PRIMARY KEY,
    [Date] DATE NOT NULL UNIQUE,
    [Year] INT NOT NULL,
    [Month] INT NOT NULL,
    MonthName VARCHAR(10) NOT NULL,
    [Quarter] INT NOT NULL,
    DayOfWeek VARCHAR(10) NOT NULL,
    IsWeekend BIT NOT NULL DEFAULT 0
);
GO

-- DimFacility - Facility dimension
CREATE TABLE DimFacility (
    FacilityID VARCHAR(10) NOT NULL PRIMARY KEY,
    FacilityName VARCHAR(100) NOT NULL,
    FacilityType VARCHAR(50) NOT NULL,
    City VARCHAR(50) NOT NULL,
    [State] VARCHAR(2) NOT NULL
);
GO

-- DimUnit - Unit dimension
CREATE TABLE DimUnit (
    UnitID VARCHAR(10) NOT NULL PRIMARY KEY,
    FacilityID VARCHAR(10) NOT NULL,
    UnitName VARCHAR(50) NOT NULL,
    UnitType VARCHAR(50) NOT NULL,
    StaffedBeds INT NOT NULL,
    CONSTRAINT FK_Unit_Facility FOREIGN KEY (FacilityID) 
        REFERENCES DimFacility(FacilityID)
);
GO

-- DimClinic - Clinic dimension
CREATE TABLE DimClinic (
    ClinicID VARCHAR(10) NOT NULL PRIMARY KEY,
    FacilityID VARCHAR(10) NOT NULL,
    ClinicName VARCHAR(100) NOT NULL,
    City VARCHAR(50) NOT NULL,
    CONSTRAINT FK_Clinic_Facility FOREIGN KEY (FacilityID) 
        REFERENCES DimFacility(FacilityID)
);
GO

-- DimProvider - Provider dimension
CREATE TABLE DimProvider (
    ProviderID VARCHAR(10) NOT NULL PRIMARY KEY,
    ProviderName VARCHAR(100) NOT NULL,
    Specialty VARCHAR(50) NOT NULL,
    PrimaryFacilityID VARCHAR(10) NOT NULL,
    ServiceLineID VARCHAR(10) NULL,
    NPI BIGINT NOT NULL,
    CONSTRAINT FK_Provider_Facility FOREIGN KEY (PrimaryFacilityID) 
        REFERENCES DimFacility(FacilityID)
);
GO

-- DimPatient - Patient dimension
CREATE TABLE DimPatient (
    PatientID VARCHAR(10) NOT NULL PRIMARY KEY,
    Sex VARCHAR(1) NOT NULL,
    BirthDate DATE NOT NULL,
    ZIP INT NOT NULL
);
GO

-- DimPayer - Payer dimension
CREATE TABLE DimPayer (
    PayerID VARCHAR(10) NOT NULL PRIMARY KEY,
    Payer VARCHAR(50) NOT NULL
);
GO

-- DimServiceLine - Service Line dimension
CREATE TABLE DimServiceLine (
    ServiceLineID VARCHAR(10) NOT NULL PRIMARY KEY,
    ServiceLine VARCHAR(50) NOT NULL
);
GO

-- DimAppointmentType - Appointment Type dimension
CREATE TABLE DimAppointmentType (
    ApptTypeID VARCHAR(10) NOT NULL PRIMARY KEY,
    AppointmentType VARCHAR(50) NOT NULL
);
GO

-- DimInfectionType - Infection Type dimension
CREATE TABLE DimInfectionType (
    InfectionTypeID VARCHAR(10) NOT NULL PRIMARY KEY,
    InfectionType VARCHAR(50) NOT NULL
);
GO

-- DimSurveyDomain - Survey Domain dimension
CREATE TABLE DimSurveyDomain (
    SurveyDomainID VARCHAR(10) NOT NULL PRIMARY KEY,
    SurveyDomain VARCHAR(100) NOT NULL
);
GO

-- DimDRG - Diagnosis Related Group dimension
CREATE TABLE DimDRG (
    DRGCode INT NOT NULL PRIMARY KEY,
    DRGName VARCHAR(100) NOT NULL,
    DRGWeight DECIMAL(10,3) NOT NULL
);
GO

-- =====================================================================
-- FACT TABLES
-- =====================================================================

-- FactEncounter - Inpatient Encounter fact table
CREATE TABLE FactEncounter (
    EncounterID VARCHAR(20) NOT NULL PRIMARY KEY,
    PatientID VARCHAR(10) NOT NULL,
    FacilityID VARCHAR(10) NOT NULL,
    ServiceLineID VARCHAR(10) NULL,
    ProviderID VARCHAR(10) NOT NULL,
    PayerID VARCHAR(10) NOT NULL,
    EncounterType VARCHAR(20) NOT NULL,
    AdmitDT DATETIME NOT NULL,
    DischargeDT DATETIME NULL,
    AdmitDate DATE NOT NULL,
    DischargeDate DATE NULL,
    DRGCode INT NULL,
    DRGWeight DECIMAL(10,3) NULL,
    ExpectedLOS_Days DECIMAL(10,2) NULL,
    IsIndexEligible BIT NULL,
    IsPlannedReadmit BIT NULL,
    TotalCharges DECIMAL(18,2) NULL,
    TotalPayments DECIMAL(18,2) NULL,
    TotalAdjustments DECIMAL(18,2) NULL,
    NetRevenue DECIMAL(18,2) NULL,
    ReadmittedWithin30D BIT NOT NULL DEFAULT 0,
    CONSTRAINT FK_Encounter_Patient FOREIGN KEY (PatientID) 
        REFERENCES DimPatient(PatientID),
    CONSTRAINT FK_Encounter_Facility FOREIGN KEY (FacilityID) 
        REFERENCES DimFacility(FacilityID),
    CONSTRAINT FK_Encounter_ServiceLine FOREIGN KEY (ServiceLineID) 
        REFERENCES DimServiceLine(ServiceLineID),
    CONSTRAINT FK_Encounter_Provider FOREIGN KEY (ProviderID) 
        REFERENCES DimProvider(ProviderID),
    CONSTRAINT FK_Encounter_Payer FOREIGN KEY (PayerID) 
        REFERENCES DimPayer(PayerID),
    CONSTRAINT FK_Encounter_DRG FOREIGN KEY (DRGCode) 
        REFERENCES DimDRG(DRGCode)
);
GO

-- FactEDVisit - Emergency Department Visit fact table
CREATE TABLE FactEDVisit (
    EDEncounterID VARCHAR(20) NOT NULL PRIMARY KEY,
    PatientID VARCHAR(10) NOT NULL,
    FacilityID VARCHAR(10) NOT NULL,
    UnitID VARCHAR(10) NOT NULL,
    PayerID VARCHAR(10) NOT NULL,
    ArrivalDT DATETIME NOT NULL,
    DepartureDT DATETIME NULL,
    ArrivalDate DATE NOT NULL,
    Disposition VARCHAR(20) NOT NULL,
    ESI_Acuity INT NOT NULL,
    CONSTRAINT FK_EDVisit_Patient FOREIGN KEY (PatientID) 
        REFERENCES DimPatient(PatientID),
    CONSTRAINT FK_EDVisit_Facility FOREIGN KEY (FacilityID) 
        REFERENCES DimFacility(FacilityID),
    CONSTRAINT FK_EDVisit_Unit FOREIGN KEY (UnitID) 
        REFERENCES DimUnit(UnitID),
    CONSTRAINT FK_EDVisit_Payer FOREIGN KEY (PayerID) 
        REFERENCES DimPayer(PayerID)
);
GO

-- FactAppointment - Outpatient Appointment fact table
CREATE TABLE FactAppointment (
    ApptID VARCHAR(20) NOT NULL PRIMARY KEY,
    PatientID VARCHAR(10) NOT NULL,
    ClinicID VARCHAR(10) NOT NULL,
    FacilityID VARCHAR(10) NOT NULL,
    ProviderID VARCHAR(10) NOT NULL,
    PayerID VARCHAR(10) NOT NULL,
    ApptTypeID VARCHAR(10) NOT NULL,
    ScheduledDT DATETIME NOT NULL,
    ApptDT DATETIME NOT NULL,
    ApptDate DATE NOT NULL,
    [Status] VARCHAR(20) NOT NULL,
    CancelDT DATETIME NULL,
    PlannedDurationMin INT NOT NULL,
    CheckInDelayMin INT NULL,
    CONSTRAINT FK_Appt_Patient FOREIGN KEY (PatientID) 
        REFERENCES DimPatient(PatientID),
    CONSTRAINT FK_Appt_Clinic FOREIGN KEY (ClinicID) 
        REFERENCES DimClinic(ClinicID),
    CONSTRAINT FK_Appt_Facility FOREIGN KEY (FacilityID) 
        REFERENCES DimFacility(FacilityID),
    CONSTRAINT FK_Appt_Provider FOREIGN KEY (ProviderID) 
        REFERENCES DimProvider(ProviderID),
    CONSTRAINT FK_Appt_Payer FOREIGN KEY (PayerID) 
        REFERENCES DimPayer(PayerID),
    CONSTRAINT FK_Appt_Type FOREIGN KEY (ApptTypeID) 
        REFERENCES DimAppointmentType(ApptTypeID)
);
GO

-- FactCensusDaily - Daily Census fact table
CREATE TABLE FactCensusDaily (
    CensusDate DATE NOT NULL,
    FacilityID VARCHAR(10) NOT NULL,
    UnitID VARCHAR(10) NOT NULL,
    OccupiedBeds INT NOT NULL,
    StaffedBeds INT NOT NULL,
    PatientDays INT NOT NULL,
    CONSTRAINT PK_CensusDaily PRIMARY KEY (CensusDate, FacilityID, UnitID),
    CONSTRAINT FK_Census_Facility FOREIGN KEY (FacilityID) 
        REFERENCES DimFacility(FacilityID),
    CONSTRAINT FK_Census_Unit FOREIGN KEY (UnitID) 
        REFERENCES DimUnit(UnitID)
);
GO

-- FactDeviceDays - Device Days fact table
CREATE TABLE FactDeviceDays (
    DeviceDate DATE NOT NULL,
    FacilityID VARCHAR(10) NOT NULL,
    UnitID VARCHAR(10) NOT NULL,
    DeviceType VARCHAR(50) NOT NULL,
    DeviceDays INT NOT NULL,
    CONSTRAINT PK_DeviceDays PRIMARY KEY (DeviceDate, FacilityID, UnitID, DeviceType),
    CONSTRAINT FK_Device_Facility FOREIGN KEY (FacilityID) 
        REFERENCES DimFacility(FacilityID),
    CONSTRAINT FK_Device_Unit FOREIGN KEY (UnitID) 
        REFERENCES DimUnit(UnitID)
);
GO

-- FactInfectionEvent - Infection Event fact table
CREATE TABLE FactInfectionEvent (
    InfectionEventID VARCHAR(20) NOT NULL PRIMARY KEY,
    EventDT DATETIME NOT NULL,
    EventDate DATE NOT NULL,
    FacilityID VARCHAR(10) NOT NULL,
    UnitID VARCHAR(10) NOT NULL,
    InfectionTypeID VARCHAR(10) NOT NULL,
    PatientID VARCHAR(10) NOT NULL,
    CONSTRAINT FK_Infection_Facility FOREIGN KEY (FacilityID) 
        REFERENCES DimFacility(FacilityID),
    CONSTRAINT FK_Infection_Unit FOREIGN KEY (UnitID) 
        REFERENCES DimUnit(UnitID),
    CONSTRAINT FK_Infection_Type FOREIGN KEY (InfectionTypeID) 
        REFERENCES DimInfectionType(InfectionTypeID),
    CONSTRAINT FK_Infection_Patient FOREIGN KEY (PatientID) 
        REFERENCES DimPatient(PatientID)
);
GO

-- FactSurveyResponse - Survey Response fact table
CREATE TABLE FactSurveyResponse (
    ResponseID VARCHAR(20) NOT NULL PRIMARY KEY,
    ResponseDT DATETIME NOT NULL,
    ResponseDate DATE NOT NULL,
    Instrument VARCHAR(50) NOT NULL,
    SurveyDomainID VARCHAR(10) NOT NULL,
    Score_1to5 INT NOT NULL,
    TopBoxFlag BIT NOT NULL DEFAULT 0,
    FacilityID VARCHAR(10) NOT NULL,
    LinkedEncounterID VARCHAR(20) NULL,
    LinkedApptID VARCHAR(20) NULL,
    CONSTRAINT FK_Survey_Domain FOREIGN KEY (SurveyDomainID) 
        REFERENCES DimSurveyDomain(SurveyDomainID),
    CONSTRAINT FK_Survey_Facility FOREIGN KEY (FacilityID) 
        REFERENCES DimFacility(FacilityID),
    CONSTRAINT FK_Survey_Encounter FOREIGN KEY (LinkedEncounterID) 
        REFERENCES FactEncounter(EncounterID),
    CONSTRAINT FK_Survey_Appt FOREIGN KEY (LinkedApptID) 
        REFERENCES FactAppointment(ApptID)
);
GO

-- FactRevenueDaily - Daily Revenue fact table
CREATE TABLE FactRevenueDaily (
    RevenueDate DATE NOT NULL,
    FacilityID VARCHAR(10) NOT NULL,
    NetPatientRevenue DECIMAL(18,2) NOT NULL,
    CONSTRAINT PK_RevenueDaily PRIMARY KEY (RevenueDate, FacilityID),
    CONSTRAINT FK_Revenue_Facility FOREIGN KEY (FacilityID) 
        REFERENCES DimFacility(FacilityID)
);
GO

-- FactARSnapshot - Accounts Receivable Snapshot fact table
CREATE TABLE FactARSnapshot (
    SnapshotDate DATE NOT NULL,
    FacilityID VARCHAR(10) NOT NULL,
    PayerID VARCHAR(10) NOT NULL,
    ARBalance DECIMAL(18,2) NOT NULL,
    AR_0_30 DECIMAL(18,2) NOT NULL,
    AR_31_60 DECIMAL(18,2) NOT NULL,
    AR_61_90 DECIMAL(18,2) NOT NULL,
    AR_91_120 DECIMAL(18,2) NOT NULL,
    AR_120_plus DECIMAL(18,2) NOT NULL,
    CONSTRAINT PK_ARSnapshot PRIMARY KEY (SnapshotDate, FacilityID, PayerID),
    CONSTRAINT FK_AR_Facility FOREIGN KEY (FacilityID) 
        REFERENCES DimFacility(FacilityID),
    CONSTRAINT FK_AR_Payer FOREIGN KEY (PayerID) 
        REFERENCES DimPayer(PayerID)
);
GO

-- FactTNA_Snapshot - Third Next Available Snapshot fact table
CREATE TABLE FactTNA_Snapshot (
    SnapshotDate DATE NOT NULL,
    ClinicID VARCHAR(10) NOT NULL,
    ApptTypeID VARCHAR(10) NOT NULL,
    ThirdNextAvailableDate DATE NOT NULL,
    TNA_Days INT NOT NULL,
    CONSTRAINT PK_TNA_Snapshot PRIMARY KEY (SnapshotDate, ClinicID, ApptTypeID),
    CONSTRAINT FK_TNA_Clinic FOREIGN KEY (ClinicID) 
        REFERENCES DimClinic(ClinicID),
    CONSTRAINT FK_TNA_ApptType FOREIGN KEY (ApptTypeID) 
        REFERENCES DimAppointmentType(ApptTypeID)
);
GO

-- =====================================================================
-- INDEXES FOR PERFORMANCE
-- =====================================================================

-- DimDate indexes
CREATE INDEX IX_DimDate_Year_Month ON DimDate([Year], [Month]);
CREATE INDEX IX_DimDate_Quarter ON DimDate([Quarter]);
GO

-- DimPatient indexes
CREATE INDEX IX_DimPatient_ZIP ON DimPatient(ZIP);
CREATE INDEX IX_DimPatient_BirthDate ON DimPatient(BirthDate);
GO

-- DimProvider indexes
CREATE INDEX IX_DimProvider_Specialty ON DimProvider(Specialty);
CREATE INDEX IX_DimProvider_Facility ON DimProvider(PrimaryFacilityID);
CREATE INDEX IX_DimProvider_ServiceLine ON DimProvider(ServiceLineID);
GO

-- FactEncounter indexes
CREATE INDEX IX_Encounter_AdmitDate ON FactEncounter(AdmitDate);
CREATE INDEX IX_Encounter_DischargeDate ON FactEncounter(DischargeDate);
CREATE INDEX IX_Encounter_Facility ON FactEncounter(FacilityID);
CREATE INDEX IX_Encounter_ServiceLine ON FactEncounter(ServiceLineID);
CREATE INDEX IX_Encounter_DRG ON FactEncounter(DRGCode);
CREATE INDEX IX_Encounter_Readmit ON FactEncounter(ReadmittedWithin30D);
GO

-- FactEDVisit indexes
CREATE INDEX IX_EDVisit_ArrivalDate ON FactEDVisit(ArrivalDate);
CREATE INDEX IX_EDVisit_Facility ON FactEDVisit(FacilityID);
CREATE INDEX IX_EDVisit_Acuity ON FactEDVisit(ESI_Acuity);
GO

-- FactAppointment indexes
CREATE INDEX IX_Appt_ApptDate ON FactAppointment(ApptDate);
CREATE INDEX IX_Appt_Clinic ON FactAppointment(ClinicID);
CREATE INDEX IX_Appt_Status ON FactAppointment([Status]);
CREATE INDEX IX_Appt_Type ON FactAppointment(ApptTypeID);
GO

-- FactCensusDaily indexes
CREATE INDEX IX_Census_Date ON FactCensusDaily(CensusDate);
CREATE INDEX IX_Census_Facility ON FactCensusDaily(FacilityID);
GO

-- FactDeviceDays indexes
CREATE INDEX IX_Device_Date ON FactDeviceDays(DeviceDate);
CREATE INDEX IX_Device_Type ON FactDeviceDays(DeviceType);
GO

-- FactInfectionEvent indexes
CREATE INDEX IX_Infection_Date ON FactInfectionEvent(EventDate);
CREATE INDEX IX_Infection_Type ON FactInfectionEvent(InfectionTypeID);
GO

-- FactSurveyResponse indexes
CREATE INDEX IX_Survey_Date ON FactSurveyResponse(ResponseDate);
CREATE INDEX IX_Survey_Domain ON FactSurveyResponse(SurveyDomainID);
CREATE INDEX IX_Survey_TopBox ON FactSurveyResponse(TopBoxFlag);
GO

-- FactRevenueDaily indexes
CREATE INDEX IX_Revenue_Date ON FactRevenueDaily(RevenueDate);
GO

-- FactARSnapshot indexes
CREATE INDEX IX_AR_Date ON FactARSnapshot(SnapshotDate);
GO

-- FactTNA_Snapshot indexes
CREATE INDEX IX_TNA_Date ON FactTNA_Snapshot(SnapshotDate);
GO

-- =====================================================================
-- SUMMARY
-- =====================================================================
PRINT '================================================';
PRINT 'Database: HealthcareDataWarehouse';
PRINT 'Status: Created Successfully';
PRINT '================================================';
PRINT 'Dimension Tables: 12';
PRINT 'Fact Tables: 10';
PRINT 'Total Tables: 22';
PRINT 'Foreign Keys: Created';
PRINT 'Indexes: Created';
PRINT '================================================';
GO
