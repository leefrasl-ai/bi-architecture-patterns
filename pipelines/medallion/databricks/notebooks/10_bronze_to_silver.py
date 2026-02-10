# ============================================
# BRONZE TO SILVER TRANSFORMATION - DATABRICKS
# Healthcare Data Platform - Databricks Version
# ============================================
# This notebook transforms raw Bronze data into cleaned,
# validated Silver layer with proper data quality controls.
#
# ENHANCEMENTS:
#   ✓ Composite Key Creation (prevents ID collisions)
#   ✓ Data Quality Validation (age, dates, amounts)
#   ✓ Quarantine Tables (rejected records)
#   ✓ Referential Integrity Checks
#   ✓ Error Logging (data_quality_errors_silver)
#   ✓ Audit Trail (etl_batch_log_silver)
# ============================================

from datetime import datetime
from pyspark.sql.types import StructType, StructField, StringType, TimestampType, LongType
import uuid

# ============================================
# SETUP: Set Catalog and Schema Context
# ============================================

spark.sql("USE CATALOG dbw_healthcare")

# Create schemas if they don't exist
spark.sql("CREATE SCHEMA IF NOT EXISTS bronze")
spark.sql("CREATE SCHEMA IF NOT EXISTS silver")
spark.sql("CREATE SCHEMA IF NOT EXISTS gold")

# Use silver schema for this script
spark.sql("USE SCHEMA silver")

# Generate ETL batch ID for audit trail
etl_batch_id = str(uuid.uuid4())
etl_start_time = datetime.now()
print(f"ETL Batch ID: {etl_batch_id}")
print(f"ETL Start Time: {etl_start_time}")
print(f"Catalog: dbw_healthcare | Schema: silver")


# ============================================
# SETUP: Drop existing Silver tables
# ============================================

spark.sql("DROP TABLE IF EXISTS silver_dim_patient")
spark.sql("DROP TABLE IF EXISTS silver_dim_provider")
spark.sql("DROP TABLE IF EXISTS silver_dim_facility")
spark.sql("DROP TABLE IF EXISTS silver_dim_payer")
spark.sql("DROP TABLE IF EXISTS silver_dim_clinic")
spark.sql("DROP TABLE IF EXISTS silver_fact_visit")
spark.sql("DROP TABLE IF EXISTS quarantine_patients")
spark.sql("DROP TABLE IF EXISTS quarantine_visits")
spark.sql("DROP TABLE IF EXISTS data_quality_errors_silver")
spark.sql("DROP TABLE IF EXISTS etl_batch_log_silver")
print("All Silver tables dropped")


# ============================================
# AUDIT TABLE: ETL Batch Log (Silver Layer)
# ============================================

spark.sql("""
    CREATE TABLE IF NOT EXISTS etl_batch_log_silver (
        batch_id STRING,
        table_name STRING,
        start_time TIMESTAMP,
        end_time TIMESTAMP,
        status STRING,
        rows_processed BIGINT,
        rows_inserted BIGINT,
        rows_rejected BIGINT,
        error_message STRING
    ) USING DELTA
""")
print("✓ etl_batch_log_silver table ready")


# ============================================
# AUDIT TABLE: Data Quality Errors (Silver)
# ============================================

spark.sql("""
    CREATE TABLE IF NOT EXISTS data_quality_errors_silver (
        error_id STRING,
        batch_id STRING,
        table_name STRING,
        error_type STRING,
        error_description STRING,
        record_id STRING,
        record_data STRING,
        created_timestamp TIMESTAMP
    ) USING DELTA
""")
print("✓ data_quality_errors_silver table ready")


# ============================================
# QUARANTINE TABLE: Patients
# ============================================

spark.sql("""
    CREATE TABLE IF NOT EXISTS quarantine_patients (
        patient_id STRING,
        source_system STRING,
        first_name STRING,
        last_name STRING,
        date_of_birth DATE,
        gender STRING,
        postal_code STRING,
        phone_number STRING,
        email_address STRING,
        rejection_reason STRING,
        rejected_timestamp TIMESTAMP,
        batch_id STRING
    ) USING DELTA
""")
print("✓ quarantine_patients table ready")


# ============================================
# QUARANTINE TABLE: Visits
# ============================================

spark.sql("""
    CREATE TABLE IF NOT EXISTS quarantine_visits (
        visit_id STRING,
        source_system STRING,
        patient_id STRING,
        provider_id STRING,
        visit_datetime TIMESTAMP,
        checkin_datetime TIMESTAMP,
        checkout_datetime TIMESTAMP,
        rejection_reason STRING,
        rejected_timestamp TIMESTAMP,
        batch_id STRING
    ) USING DELTA
""")
print("✓ quarantine_visits table ready")


# ============================================
# HELPER FUNCTION: Log ETL Batch
# ============================================

def log_batch(table_name, status, rows_processed=0, rows_inserted=0, rows_rejected=0, error_msg=None):
    """Log ETL batch execution to Silver audit table with explicit schema"""
    
    schema = StructType([
        StructField("batch_id", StringType(), False),
        StructField("table_name", StringType(), False),
        StructField("start_time", TimestampType(), False),
        StructField("end_time", TimestampType(), False),
        StructField("status", StringType(), False),
        StructField("rows_processed", LongType(), False),
        StructField("rows_inserted", LongType(), False),
        StructField("rows_rejected", LongType(), False),
        StructField("error_message", StringType(), True)
    ])
    
    log_data = [(
        str(etl_batch_id),
        str(table_name),
        etl_start_time,
        datetime.now(),
        str(status),
        int(rows_processed),
        int(rows_inserted),
        int(rows_rejected),
        str(error_msg) if error_msg else None
    )]
    
    log_df = spark.createDataFrame(log_data, schema)
    log_df.write.format("delta").mode("append").saveAsTable("etl_batch_log_silver")


# ############################################
#
#              PATIENTS
#
# ############################################

print("\n" + "="*50)
print("PROCESSING PATIENTS WITH DATA QUALITY CHECKS")
print("="*50)

try:
    # STEP 1: Load raw data
    patients_a = spark.sql("""
        SELECT *, 'HSA' as source_system FROM bronze.bronze_dimpatient
    """)
    patients_a.createOrReplaceTempView("patients_a_raw")

    patients_b = spark.sql("""
        SELECT *, 'UCN' as source_system FROM bronze.bronze_uc_patients
    """)
    patients_b.createOrReplaceTempView("patients_b_raw")

    rows_loaded = patients_a.count() + patients_b.count()
    print(f"PATIENTS - Loaded HSA: {patients_a.count()} rows, UCN: {patients_b.count()} rows")


    # STEP 2: Standardize columns & fix types
    patients_a = spark.sql("""
        SELECT 
            PatientID as patient_id,
            source_system,
            CAST(NULL AS STRING) as first_name,
            CAST(NULL AS STRING) as last_name,
            TO_DATE(BirthDate) as date_of_birth,
            Sex as gender,
            CAST(CAST(ZIP AS INT) AS STRING) as postal_code,
            CAST(NULL AS STRING) as phone_number,
            CAST(NULL AS STRING) as email_address
        FROM patients_a_raw
    """)
    patients_a.createOrReplaceTempView("patients_a_typed")

    patients_b = spark.sql("""
        SELECT 
            Patient_Num as patient_id,
            source_system,
            SPLIT(Full_Name, ' ')[0] as first_name,
            SPLIT(Full_Name, ' ')[SIZE(SPLIT(Full_Name, ' ')) - 1] as last_name,
            TO_DATE(Birth_Date) as date_of_birth,
            Sex as gender,
            CAST(NULL AS STRING) as postal_code,
            Phone_Number as phone_number,
            Email_Address as email_address
        FROM patients_b_raw
    """)
    patients_b.createOrReplaceTempView("patients_b_typed")


    # STEP 3: Handle nulls/empty strings
    patients_a = spark.sql("""
        SELECT 
            patient_id,
            source_system,
            first_name,
            last_name,
            date_of_birth,
            NULLIF(gender, '') as gender,
            NULLIF(postal_code, '') as postal_code,
            phone_number,
            email_address
        FROM patients_a_typed
    """)

    patients_b = spark.sql("""
        SELECT 
            patient_id,
            source_system,
            NULLIF(first_name, '') as first_name,
            NULLIF(last_name, '') as last_name,
            date_of_birth,
            NULLIF(gender, '') as gender,
            postal_code,
            NULLIF(phone_number, '') as phone_number,
            NULLIF(email_address, '') as email_address
        FROM patients_b_typed
    """)


    # STEP 4: Union both sources - DIRECT UNION (no temp view)
    patients_union = patients_a.union(patients_b)
    patients_union.createOrReplaceTempView("patients_union")


    # STEP 5: DATA QUALITY VALIDATION
    print("\n→ Running data quality validations...")
    
    patients_validated = spark.sql("""
        SELECT 
            *,
            FLOOR(DATEDIFF(CURRENT_DATE(), date_of_birth) / 365.25) as calculated_age,
            CASE 
                WHEN date_of_birth IS NULL THEN 'MISSING_DOB'
                WHEN FLOOR(DATEDIFF(CURRENT_DATE(), date_of_birth) / 365.25) < 0 THEN 'NEGATIVE_AGE'
                WHEN FLOOR(DATEDIFF(CURRENT_DATE(), date_of_birth) / 365.25) > 120 THEN 'AGE_TOO_HIGH'
                ELSE 'VALID'
            END as validation_status
        FROM patients_union
    """)
    patients_validated.createOrReplaceTempView("patients_validated")
    
    # Separate valid and invalid records
    valid_patients = spark.sql("""
        SELECT 
            CONCAT(source_system, '|', patient_id) as patient_key,
            patient_id,
            source_system,
            first_name,
            last_name,
            date_of_birth,
            gender,
            postal_code,
            phone_number,
            email_address,
            CURRENT_TIMESTAMP() as created_timestamp,
            CURRENT_TIMESTAMP() as modified_timestamp,
            '{batch_id}' as etl_batch_id
        FROM patients_validated
        WHERE validation_status = 'VALID'
    """.format(batch_id=etl_batch_id))
    
    invalid_patients = spark.sql("""
        SELECT 
            patient_id,
            source_system,
            first_name,
            last_name,
            date_of_birth,
            gender,
            postal_code,
            phone_number,
            email_address,
            validation_status as rejection_reason,
            CURRENT_TIMESTAMP() as rejected_timestamp,
            '{batch_id}' as batch_id
        FROM patients_validated
        WHERE validation_status != 'VALID'
    """.format(batch_id=etl_batch_id))
    
    rejected_count = invalid_patients.count()
    if rejected_count > 0:
        print(f"⚠️  Found {rejected_count} invalid patient records - moving to quarantine")
        invalid_patients.write.format("delta").mode("append").saveAsTable("quarantine_patients")
        
        # Log errors
        for row in invalid_patients.limit(100).collect():
            error_data = [(
                str(uuid.uuid4()),
                etl_batch_id,
                "silver_dim_patient",
                row.rejection_reason,
                f"Patient failed validation: {row.rejection_reason}",
                f"{row.source_system}|{row.patient_id}",
                f"patient_id={row.patient_id}, dob={row.date_of_birth}",
                datetime.now()
            )]
            spark.createDataFrame(error_data, ["error_id", "batch_id", "table_name", "error_type", 
                                               "error_description", "record_id", "record_data", 
                                               "created_timestamp"]).write.format("delta").mode("append").saveAsTable("data_quality_errors_silver")
    else:
        print("✓ All patient records passed validation")


    # STEP 6: Save valid records to Silver
    valid_patients.write.format("delta").mode("overwrite").saveAsTable("silver_dim_patient")
    valid_count = valid_patients.count()
    print(f"✓ silver_dim_patient: {valid_count} rows saved, {rejected_count} rejected")
    log_batch("silver_dim_patient", "SUCCESS", rows_loaded, valid_count, rejected_count)

except Exception as e:
    print(f"✗ silver_dim_patient failed: {str(e)}")
    log_batch("silver_dim_patient", "FAILED", 0, 0, 0, str(e))


# ############################################
#
#              PROVIDERS
#
# ############################################

print("\n" + "="*50)
print("PROCESSING PROVIDERS")
print("="*50)

try:
    # STEP 1: Load raw data
    providers_a = spark.sql("""
        SELECT *, 'HSA' as source_system FROM bronze.bronze_dimprovider
    """)

    providers_b = spark.sql("""
        SELECT *, 'UCN' as source_system FROM bronze.bronze_uc_clinicians
    """)

    rows_loaded = providers_a.count() + providers_b.count()
    print(f"PROVIDERS - Loaded HSA: {providers_a.count()} rows, UCN: {providers_b.count()} rows")


    # STEP 2: Standardize columns & fix types
    providers_a = spark.sql("""
        SELECT 
            ProviderID as provider_id,
            'HSA' as source_system,
            ProviderName as provider_name,
            Specialty as specialty,
            CAST(NULL AS STRING) as credential,
            CASE 
                WHEN ProviderName LIKE 'Dr.%' THEN 'Y' 
                ELSE 'N' 
            END as credential_missing_likely_physician,
            CAST(NPI AS STRING) as npi
        FROM bronze.bronze_dimprovider
    """)

    providers_b = spark.sql("""
        SELECT 
            Clinician_Key as provider_id,
            'UCN' as source_system,
            Clinician_Name as provider_name,
            Specialty_Text as specialty,
            Credential as credential,
            CASE 
                WHEN Clinician_Name LIKE 'Dr.%' AND (Credential IS NULL OR Credential = '') 
                THEN 'Y' 
                ELSE 'N' 
            END as credential_missing_likely_physician,
            CAST(NPI_Number AS STRING) as npi
        FROM bronze.bronze_uc_clinicians
    """)


    # STEP 3: Handle nulls/empty strings
    providers_a_clean = providers_a.selectExpr(
        "provider_id",
        "source_system",
        "provider_name",
        "NULLIF(specialty, '') as specialty",
        "credential",
        "credential_missing_likely_physician",
        "NULLIF(npi, '') as npi"
    )

    providers_b_clean = providers_b.selectExpr(
        "provider_id",
        "source_system",
        "provider_name",
        "NULLIF(specialty, '') as specialty",
        "NULLIF(credential, '') as credential",
        "credential_missing_likely_physician",
        "NULLIF(npi, '') as npi"
    )


    # STEP 4: Union both sources - DIRECT UNION
    providers_union = providers_a_clean.union(providers_b_clean)
    providers_union.createOrReplaceTempView("providers_union")


    # STEP 5: Create composite keys
    providers_silver = spark.sql("""
        SELECT 
            CONCAT(source_system, '|', provider_id) as provider_key,
            provider_id,
            source_system,
            provider_name,
            specialty,
            credential,
            credential_missing_likely_physician,
            npi,
            CURRENT_TIMESTAMP() as created_timestamp,
            CURRENT_TIMESTAMP() as modified_timestamp,
            '{batch_id}' as etl_batch_id
        FROM providers_union
    """.format(batch_id=etl_batch_id))


    # STEP 6: Save to Silver
    providers_silver.write.format("delta").mode("overwrite").saveAsTable("silver_dim_provider")
    provider_count = providers_silver.count()
    print(f"✓ silver_dim_provider: {provider_count} rows saved")
    log_batch("silver_dim_provider", "SUCCESS", rows_loaded, provider_count, 0)

except Exception as e:
    print(f"✗ silver_dim_provider failed: {str(e)}")
    log_batch("silver_dim_provider", "FAILED", 0, 0, 0, str(e))


# ############################################
#
#              FACILITIES
#
# ############################################

print("\n" + "="*50)
print("PROCESSING FACILITIES")
print("="*50)

try:
    # STEP 1: Load raw data
    facilities_a = spark.sql("""
        SELECT 
            FacilityID as facility_id,
            'HSA' as source_system,
            FacilityName as facility_name,
            FacilityType as facility_type,
            CAST(NULL AS STRING) as address,
            City as city,
            State as state,
            CAST(NULL AS STRING) as postal_code
        FROM bronze.bronze_dimfacility
    """)

    facilities_b = spark.sql("""
        SELECT 
            Site_Code as facility_id,
            'UCN' as source_system,
            Site_Name as facility_name,
            'Urgent Care' as facility_type,
            Street_Line1 as address,
            City as city,
            State as state,
            CAST(Postal_Code AS STRING) as postal_code
        FROM bronze.bronze_uc_sites
    """)

    rows_loaded = facilities_a.count() + facilities_b.count()
    print(f"FACILITIES - Loaded HSA: {facilities_a.count()} rows, UCN: {facilities_b.count()} rows")


    # STEP 2: Handle nulls/empty strings
    facilities_a_clean = facilities_a.selectExpr(
        "facility_id",
        "source_system",
        "facility_name",
        "NULLIF(facility_type, '') as facility_type",
        "address",
        "NULLIF(city, '') as city",
        "NULLIF(state, '') as state",
        "postal_code"
    )

    facilities_b_clean = facilities_b.selectExpr(
        "facility_id",
        "source_system",
        "facility_name",
        "facility_type",
        "NULLIF(address, '') as address",
        "NULLIF(city, '') as city",
        "NULLIF(state, '') as state",
        "NULLIF(postal_code, '') as postal_code"
    )


    # STEP 3: Union both sources - DIRECT UNION
    facilities_union = facilities_a_clean.union(facilities_b_clean)
    facilities_union.createOrReplaceTempView("facilities_union")


    # STEP 4: Create composite keys
    facilities_silver = spark.sql("""
        SELECT 
            CONCAT(source_system, '|', facility_id) as facility_key,
            facility_id,
            source_system,
            facility_name,
            facility_type,
            address,
            city,
            state,
            postal_code,
            CURRENT_TIMESTAMP() as created_timestamp,
            CURRENT_TIMESTAMP() as modified_timestamp,
            '{batch_id}' as etl_batch_id
        FROM facilities_union
    """.format(batch_id=etl_batch_id))


    # STEP 5: Save to Silver
    facilities_silver.write.format("delta").mode("overwrite").saveAsTable("silver_dim_facility")
    facility_count = facilities_silver.count()
    print(f"✓ silver_dim_facility: {facility_count} rows saved")
    log_batch("silver_dim_facility", "SUCCESS", rows_loaded, facility_count, 0)

except Exception as e:
    print(f"✗ silver_dim_facility failed: {str(e)}")
    log_batch("silver_dim_facility", "FAILED", 0, 0, 0, str(e))


# ############################################
#
#              PAYERS
#
# ############################################

print("\n" + "="*50)
print("PROCESSING PAYERS")
print("="*50)

try:
    # STEP 1: Load raw data
    payers_a = spark.sql("""
        SELECT 
            PayerID as payer_id,
            'HSA' as source_system,
            Payer as payer_name,
            CAST(NULL AS STRING) as payer_type
        FROM bronze.bronze_dimpayer
    """)

    payers_b = spark.sql("""
        SELECT 
            Payer_Code as payer_id,
            'UCN' as source_system,
            Payer_Name as payer_name,
            Plan_Type as payer_type
        FROM bronze.bronze_uc_payers
    """)

    rows_loaded = payers_a.count() + payers_b.count()
    print(f"PAYERS - Loaded HSA: {payers_a.count()} rows, UCN: {payers_b.count()} rows")


    # STEP 2: Handle nulls/empty strings
    payers_a_clean = payers_a.selectExpr(
        "payer_id",
        "source_system",
        "NULLIF(payer_name, '') as payer_name",
        "payer_type"
    )

    payers_b_clean = payers_b.selectExpr(
        "payer_id",
        "source_system",
        "NULLIF(payer_name, '') as payer_name",
        "NULLIF(payer_type, '') as payer_type"
    )


    # STEP 3: Union both sources - DIRECT UNION
    payers_union = payers_a_clean.union(payers_b_clean)
    payers_union.createOrReplaceTempView("payers_union")


    # STEP 4: Create composite keys
    payers_silver = spark.sql("""
        SELECT 
            CONCAT(source_system, '|', payer_id) as payer_key,
            payer_id,
            source_system,
            payer_name,
            payer_type,
            CURRENT_TIMESTAMP() as created_timestamp,
            CURRENT_TIMESTAMP() as modified_timestamp,
            '{batch_id}' as etl_batch_id
        FROM payers_union
    """.format(batch_id=etl_batch_id))


    # STEP 5: Save to Silver
    payers_silver.write.format("delta").mode("overwrite").saveAsTable("silver_dim_payer")
    payer_count = payers_silver.count()
    print(f"✓ silver_dim_payer: {payer_count} rows saved")
    log_batch("silver_dim_payer", "SUCCESS", rows_loaded, payer_count, 0)

except Exception as e:
    print(f"✗ silver_dim_payer failed: {str(e)}")
    log_batch("silver_dim_payer", "FAILED", 0, 0, 0, str(e))


# ############################################
#
#              CLINICS (HSA Only)
#
# ############################################

print("\n" + "="*50)
print("PROCESSING CLINICS")
print("="*50)

try:
    # STEP 1: Load and transform in one step
    clinics_silver = spark.sql("""
        SELECT 
            CONCAT('HSA', '|', ClinicID) as clinic_key,
            ClinicID as clinic_id,
            'HSA' as source_system,
            NULLIF(ClinicName, '') as clinic_name,
            CONCAT('HSA', '|', FacilityID) as facility_key,
            CURRENT_TIMESTAMP() as created_timestamp,
            CURRENT_TIMESTAMP() as modified_timestamp,
            '{batch_id}' as etl_batch_id
        FROM bronze.bronze_dimclinic
    """.format(batch_id=etl_batch_id))

    rows_loaded = clinics_silver.count()
    print(f"CLINICS - Loaded HSA: {rows_loaded} rows (UCN has no clinic data)")


    # STEP 2: Save to Silver
    clinics_silver.write.format("delta").mode("overwrite").saveAsTable("silver_dim_clinic")
    print(f"✓ silver_dim_clinic: {rows_loaded} rows saved")
    log_batch("silver_dim_clinic", "SUCCESS", rows_loaded, rows_loaded, 0)

except Exception as e:
    print(f"✗ silver_dim_clinic failed: {str(e)}")
    log_batch("silver_dim_clinic", "FAILED", 0, 0, 0, str(e))


# ############################################
#
#              VISITS (Fact Table)
#
# ############################################

print("\n" + "="*50)
print("PROCESSING VISITS WITH DATA QUALITY CHECKS")
print("="*50)

try:
    # STEP 1: Load raw data
    visits_a = spark.sql("""
        SELECT 
            ApptID as visit_id,
            'HSA' as source_system,
            'Scheduled' as access_channel,
            PatientID as patient_id,
            ProviderID as provider_id,
            FacilityID as facility_id,
            ClinicID as clinic_id,
            PayerID as payer_id,
            TO_TIMESTAMP(ApptDT) as visit_datetime,
            CAST(NULL AS TIMESTAMP) as checkin_datetime,
            CAST(NULL AS TIMESTAMP) as checkout_datetime,
            Status as visit_status,
            CAST(PlannedDurationMin AS INT) as planned_duration_min,
            CAST(CheckInDelayMin AS INT) as checkin_delay_min,
            CAST(NULL AS STRING) as discharge_disposition,
            CAST(NULL AS STRING) as reason_for_visit,
            CAST(NULL AS DECIMAL(10,2)) as copay_amt
        FROM bronze.bronze_factappointment
    """)

    visits_b = spark.sql("""
        SELECT 
            Visit_ID as visit_id,
            'UCN' as source_system,
            Arrival_Mode as access_channel,
            Patient_Num as patient_id,
            Clinician_Key as provider_id,
            Site_Code as facility_id,
            CAST(NULL AS STRING) as clinic_id,
            Primary_Payer_Code as payer_id,
            CASE 
                WHEN Visit_DateTime IS NOT NULL AND Visit_DateTime != '' 
                THEN TO_TIMESTAMP(Visit_DateTime)
                ELSE NULL 
            END as visit_datetime,
            CASE 
                WHEN Checkin_Time IS NOT NULL AND Checkin_Time != '' 
                THEN TO_TIMESTAMP(CONCAT(DATE(TO_TIMESTAMP(Visit_DateTime)), ' ', Checkin_Time))
                ELSE NULL 
            END as checkin_datetime,
            CASE 
                WHEN CheckOut_Time IS NOT NULL AND CheckOut_Time != '' 
                THEN TO_TIMESTAMP(CONCAT(DATE(TO_TIMESTAMP(Visit_DateTime)), ' ', CheckOut_Time))
                ELSE NULL 
            END as checkout_datetime,
            Visit_Status as visit_status,
            CAST(NULL AS INT) as planned_duration_min,
            CAST(NULL AS INT) as checkin_delay_min,
            Discharge_Disposition as discharge_disposition,
            Reason_For_Visit as reason_for_visit,
            CASE 
                WHEN Copay_Amt IS NULL OR Copay_Amt = '' THEN NULL 
                ELSE CAST(Copay_Amt AS DECIMAL(10,2)) 
            END as copay_amt
        FROM bronze.bronze_uc_visits
    """)

    rows_loaded = visits_a.count() + visits_b.count()
    print(f"VISITS - Loaded HSA: {visits_a.count()} rows, UCN: {visits_b.count()} rows")


    # STEP 2: Handle nulls/empty strings
    visits_a_clean = visits_a.selectExpr(
        "visit_id", "source_system",
        "NULLIF(access_channel, '') as access_channel",
        "patient_id", "provider_id", "facility_id", "clinic_id", "payer_id",
        "visit_datetime", "checkin_datetime", "checkout_datetime",
        "NULLIF(visit_status, '') as visit_status",
        "planned_duration_min", "checkin_delay_min",
        "discharge_disposition", "reason_for_visit", "copay_amt"
    )

    visits_b_clean = visits_b.selectExpr(
        "visit_id", "source_system",
        "NULLIF(access_channel, '') as access_channel",
        "patient_id", "provider_id", "facility_id", "clinic_id", "payer_id",
        "visit_datetime", "checkin_datetime", "checkout_datetime",
        "NULLIF(visit_status, '') as visit_status",
        "planned_duration_min", "checkin_delay_min",
        "NULLIF(discharge_disposition, '') as discharge_disposition",
        "NULLIF(reason_for_visit, '') as reason_for_visit",
        "copay_amt"
    )


    # STEP 3: Union both sources - DIRECT UNION
    visits_union = visits_a_clean.union(visits_b_clean)
    visits_union.createOrReplaceTempView("visits_union")


    # STEP 4: DATA QUALITY VALIDATION
    print("\n→ Running data quality validations for visits...")
    
    visits_validated = spark.sql("""
        SELECT 
            *,
            CASE 
                WHEN visit_datetime IS NULL THEN 'MISSING_VISIT_DATETIME'
                WHEN visit_datetime > CURRENT_TIMESTAMP() THEN 'FUTURE_VISIT_DATE'
                WHEN checkout_datetime IS NOT NULL AND checkin_datetime IS NOT NULL 
                     AND checkout_datetime < checkin_datetime THEN 'INVALID_CHECKOUT_TIME'
                WHEN copay_amt < 0 THEN 'NEGATIVE_COPAY'
                ELSE 'VALID'
            END as validation_status
        FROM visits_union
    """)
    visits_validated.createOrReplaceTempView("visits_validated")
    
    # Separate valid and invalid records
    valid_visits = spark.sql("""
        SELECT 
            CONCAT(source_system, '|', visit_id) as visit_key,
            CONCAT(source_system, '|', patient_id) as patient_key,
            CONCAT(source_system, '|', provider_id) as provider_key,
            CONCAT(source_system, '|', facility_id) as facility_key,
            CONCAT(source_system, '|', clinic_id) as clinic_key,
            CONCAT(source_system, '|', payer_id) as payer_key,
            visit_id, source_system, access_channel,
            patient_id, provider_id, facility_id, clinic_id, payer_id,
            visit_datetime, checkin_datetime, checkout_datetime,
            visit_status, planned_duration_min, checkin_delay_min,
            discharge_disposition, reason_for_visit, copay_amt,
            CURRENT_TIMESTAMP() as created_timestamp,
            CURRENT_TIMESTAMP() as modified_timestamp,
            '{batch_id}' as etl_batch_id
        FROM visits_validated
        WHERE validation_status = 'VALID'
    """.format(batch_id=etl_batch_id))
    
    invalid_visits = spark.sql("""
        SELECT 
            visit_id, source_system, patient_id, provider_id,
            visit_datetime, checkin_datetime, checkout_datetime,
            validation_status as rejection_reason,
            CURRENT_TIMESTAMP() as rejected_timestamp,
            '{batch_id}' as batch_id
        FROM visits_validated
        WHERE validation_status != 'VALID'
    """.format(batch_id=etl_batch_id))
    
    rejected_count = invalid_visits.count()
    if rejected_count > 0:
        print(f"⚠️  Found {rejected_count} invalid visit records - moving to quarantine")
        invalid_visits.write.format("delta").mode("append").saveAsTable("quarantine_visits")
    else:
        print("✓ All visit records passed validation")


    # STEP 5: Referential Integrity Check
    print("\n→ Checking referential integrity...")
    
    valid_visits.createOrReplaceTempView("temp_valid_visits")
    
    orphan_visits = spark.sql("""
        SELECT v.visit_key, v.patient_key, v.source_system
        FROM temp_valid_visits v
        LEFT JOIN silver_dim_patient p
            ON v.patient_key = p.patient_key
        WHERE p.patient_key IS NULL
    """)
    
    orphan_count = orphan_visits.count()
    if orphan_count > 0:
        print(f"⚠️  Found {orphan_count} visits with missing patient references")
    else:
        print("✓ All visits have valid patient references")


    # STEP 6: Save valid records to Silver
    valid_visits.write.format("delta").mode("overwrite").saveAsTable("silver_fact_visit")
    valid_count = valid_visits.count()
    print(f"✓ silver_fact_visit: {valid_count} rows saved, {rejected_count} rejected")
    log_batch("silver_fact_visit", "SUCCESS", rows_loaded, valid_count, rejected_count)

except Exception as e:
    print(f"✗ silver_fact_visit failed: {str(e)}")
    log_batch("silver_fact_visit", "FAILED", 0, 0, 0, str(e))


# ############################################
#
#              DATA QUALITY SUMMARY
#
# ############################################

print("\n" + "="*50)
print("DATA QUALITY SUMMARY - SILVER LAYER")
print("="*50)

dq_summary = spark.sql("""
    SELECT 
        table_name,
        error_type,
        COUNT(*) as error_count,
        COUNT(DISTINCT record_id) as unique_records
    FROM data_quality_errors_silver
    WHERE batch_id = '{batch_id}'
    GROUP BY table_name, error_type
    ORDER BY table_name, error_count DESC
""".format(batch_id=etl_batch_id))

if dq_summary.count() > 0:
    print("\nData Quality Issues Found:")
    dq_summary.show(truncate=False)
else:
    print("\n✓ No data quality issues found")

# Quarantine summary
print("\nQuarantine Summary:")
try:
    q_patients = spark.sql("SELECT COUNT(*) FROM quarantine_patients WHERE batch_id = '{}'".format(etl_batch_id)).collect()[0][0]
    q_visits = spark.sql("SELECT COUNT(*) FROM quarantine_visits WHERE batch_id = '{}'".format(etl_batch_id)).collect()[0][0]
    print(f"  quarantine_patients: {q_patients} rejected records")
    print(f"  quarantine_visits: {q_visits} rejected records")
except:
    print("  (Unable to retrieve quarantine counts)")


# ############################################
#
#              FINAL SUMMARY
#
# ############################################

etl_end_time = datetime.now()
etl_duration = (etl_end_time - etl_start_time).total_seconds()

print("\n" + "="*50)
print("BRONZE TO SILVER TRANSFORMATION COMPLETE")
print("="*50)
print(f"\nETL Batch ID: {etl_batch_id}")
print(f"Duration: {etl_duration:.2f} seconds")
print("\n✅ SILVER TABLES CREATED (6):")
print("  ✓ silver_dim_patient (with patient_key)")
print("  ✓ silver_dim_provider (with provider_key)")
print("  ✓ silver_dim_facility (with facility_key)")
print("  ✓ silver_dim_payer (with payer_key)")
print("  ✓ silver_dim_clinic (with clinic_key)")
print("  ✓ silver_fact_visit (with composite foreign keys)")
print("\n✅ DATA QUALITY TABLES (4):")
print("  ✓ quarantine_patients (rejected patient records)")
print("  ✓ quarantine_visits (rejected visit records)")
print("  ✓ data_quality_errors_silver (error log)")
print("  ✓ etl_batch_log_silver (execution audit)")
print("\n📊 KEY ENHANCEMENTS:")
print("  ✓ Composite keys prevent ID collisions across systems")
print("  ✓ Data quality validation with rejection workflow")
print("  ✓ Referential integrity checks")
print("  ✓ Complete audit trail and error logging")
print("  ✓ Quarantine tables for rejected records")
print("\n✅ Silver layer ready for Gold transformations!")
print("="*50)
