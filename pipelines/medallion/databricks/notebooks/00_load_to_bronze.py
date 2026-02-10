# ============================================
# BRONZE DATA LOADING - UNIFIED SCRIPT
# Healthcare Data Platform - Databricks
# ============================================
# This notebook loads raw data from two source systems
# into the Bronze layer as Delta tables.
#
# Data Sources:
#   1. HSA (HealthSystem A) - Hospital/Clinic network
#      Source: Excel file with multiple sheets
#      Format: healthcare_powerbi_sample_data_2yr.xlsx
#
#   2. UCN (Urgent Care Network) - Recently acquired
#      Source: Multiple CSV files
#      Format: uc_*.csv files
#
# Bronze Layer Purpose:
#   - Stores raw data "as-is" from source systems
#   - Minimal transformation (column names only)
#   - Foundation for Silver layer transformations
# ============================================

import pandas as pd

# ============================================
# SECTION 1: LOAD HSA DATA (Excel)
# ============================================
print("="*50)
print("LOADING HSA DATA FROM EXCEL")
print("="*50)

file_path = "/Volumes/dbw_healthcare/bronze/raw_files/healthcare_powerbi_sample_data_2yr.xlsx"

# All sheets except README
sheets = [
    'DimDate', 'DimFacility', 'DimUnit', 'DimClinic', 'DimProvider', 
    'DimPatient', 'DimPayer', 'DimServiceLine', 'DimAppointmentType',
    'DimInfectionType', 'DimSurveyDomain', 'DimDRG',
    'FactEncounter', 'FactEDVisit', 'FactAppointment', 'FactCensusDaily',
    'FactDeviceDays', 'FactInfectionEvent', 'FactSurveyResponse',
    'FactRevenueDaily', 'FactARSnapshot', 'FactTNA_Snapshot'
]

for sheet in sheets:
    # Read Excel sheet with pandas (best for Excel files)
    pdf = pd.read_excel(file_path, sheet_name=sheet)
    
    # Handle duplicate column names (pandas adds .1, .2 etc to duplicates)
    # Remove any columns that are exact duplicates
    pdf = pdf.loc[:, ~pdf.columns.duplicated()]
    
    # Convert to Spark DataFrame
    df = spark.createDataFrame(pdf)
    
    # Write to bronze schema as Delta table (with raw_ prefix)
    table_name = f"dbw_healthcare.bronze.raw_{sheet.lower()}"
    df.write.format("delta").mode("overwrite").option("overwriteSchema", "true").saveAsTable(table_name)
    
    print(f"✓ {table_name}: {df.count()} rows")

print("\n✅ All HSA Bronze tables loaded!\n")


# ============================================
# SECTION 2: LOAD UCN DATA (CSV)
# ============================================
print("="*50)
print("LOADING UCN DATA FROM CSV FILES")
print("="*50)

uc_file_path = "/Volumes/dbw_healthcare/bronze/raw_files/"

# UCN source files mapping
uc_files = {
    'uc_clinicians.csv': 'bronze_uc_clinicians',    # Provider/clinician data
    'uc_patients.csv': 'bronze_uc_patients',        # Patient demographics
    'uc_payers.csv': 'bronze_uc_payers',            # Insurance payers
    'uc_sites.csv': 'bronze_uc_sites',              # Urgent care locations
    'uc_visits.csv': 'bronze_uc_visits',            # Visit/encounter data
    'uc_visit_dx.csv': 'bronze_uc_visit_dx'         # Visit diagnoses
}

for file_name, table_name in uc_files.items():
    # Read CSV file with Spark
    # Note: inferSchema="false" keeps everything as strings in Bronze
    # This prevents casting errors with empty values - Silver layer handles typing
    df = spark.read.format("csv") \
        .option("header", "true") \
        .option("inferSchema", "false") \
        .load(f"{uc_file_path}{file_name}")
    
    # Write to bronze schema as Delta table
    full_table_name = f"dbw_healthcare.bronze.{table_name}"
    df.write.format("delta").mode("overwrite").option("overwriteSchema", "true").saveAsTable(full_table_name)
    
    print(f"✓ {full_table_name}: {df.count()} rows")

print("\n✅ All UCN Bronze tables loaded!\n")


# ============================================
# SUMMARY
# ============================================
print("="*50)
print("BRONZE DATA LOADING COMPLETE")
print("="*50)
print("\nHSA Tables (22):")
print("  - Dimensions: Date, Facility, Unit, Clinic, Provider, Patient, Payer, etc.")
print("  - Facts: Encounter, EDVisit, Appointment, Census, Revenue, etc.")
print("\nUCN Tables (6):")
print("  - bronze_uc_clinicians")
print("  - bronze_uc_patients")
print("  - bronze_uc_payers")
print("  - bronze_uc_sites")
print("  - bronze_uc_visits")
print("  - bronze_uc_visit_dx")
print("\n✓ Bronze layer ready for Silver transformations")
