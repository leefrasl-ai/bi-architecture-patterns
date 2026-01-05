# Healthcare Data Warehouse - Star Schema Design

## Overview
Complete SQL Server data warehouse implementation for healthcare analytics with Power BI integration. Designed to support operational reporting, clinical analytics, and executive dashboards.

## Architecture
- **Design Pattern:** Star schema optimized for analytical queries
- **Platform:** SQL Server 2019+
- **BI Tool:** Power BI (import mode)
- **Scale:** 12 dimension tables, 10 fact tables, 50+ indexes

## Schema Design

### Dimension Tables (12)
- **DimDate** - Full calendar dimension with fiscal periods
- **DimFacility** - Hospital locations and departments
- **DimUnit** - Inpatient units with bed capacity
- **DimClinic** - Outpatient clinics
- **DimProvider** - Healthcare providers (physicians, nurses, staff)
- **DimPatient** - Patient demographics (HIPAA-compliant)
- **DimPayer** - Insurance payers and plans
- **DimServiceLine** - Clinical service lines
- **DimAppointmentType** - Appointment type classifications
- **DimInfectionType** - Hospital-acquired infection types
- **DimSurveyDomain** - Patient satisfaction survey domains
- **DimDRG** - Diagnosis Related Groups with weights

### Fact Tables (10)
- **FactEncounter** - Inpatient admissions and discharges
- **FactEDVisit** - Emergency department visits
- **FactAppointment** - Outpatient appointments
- **FactCensusDaily** - Daily inpatient census
- **FactDeviceDays** - Medical device utilization
- **FactInfectionEvent** - Hospital-acquired infection events
- **FactSurveyResponse** - Patient satisfaction surveys
- **FactRevenueDaily** - Daily revenue tracking
- **FactARSnapshot** - Accounts receivable aging
- **FactTNA_Snapshot** - Third Next Available appointment tracking

## Key Features

### Performance Optimization
- Surrogate keys on all dimensions for stability
- Clustered indexes on fact table date columns
- Non-clustered indexes on foreign keys and common filters
- Optimized for Power BI import mode with sub-second query response

### Data Quality
- Foreign key constraints maintain referential integrity
- NOT NULL constraints on required fields
- CHECK constraints on data ranges
- Unique constraints on natural keys

## Files
- [`healthcare-datawarehouse-schema.sql`](healthcare-datawarehouse-schema.sql) - Complete database creation script

## Usage
```sql
-- Execute against master database
sqlcmd -S YourServer -i healthcare-datawarehouse-schema.sql
```

## Design Decisions

**Why Star Schema?**  
Star schema provides optimal query performance for analytical workloads and simplifies Power BI semantic model design.

**Why Surrogate Keys?**  
Natural keys can change; surrogate keys ensure data stability and better join performance.

**Why Separate Date Dimension?**  
Enables Power BI time intelligence functions and provides consistent date hierarchies across all fact tables.

## Author
Lee Frasl - Senior BI Architect  
[LinkedIn](https://linkedin.com/in/leefrasl) | [GitHub](https://github.com/leefrasl)
