# Databricks Medallion Pipeline (Healthcare Demo)

This folder contains the Databricks version of a simple Medallion (Bronze → Silver → Gold) pipeline implemented as Python scripts.

## Run order

1. **00_load_to_bronze.py**
2. **10_bronze_to_silver.py**
3. **20_silver_to_gold.py**

---

## 00 – Load → Bronze

`notebooks/00_load_to_bronze.py`

Purpose:
- Land raw source data into Bronze with minimal transformation
- Preserve lineage to enable reprocessing

Inputs (example demo sources):
- HSA (Health System A): Excel workbook (multiple sheets)
- UCN (Urgent Care Network): multiple CSV files

Outputs:
- Bronze Delta tables (or files) in the configured bronze schema/path

---

## 10 – Bronze → Silver

`notebooks/10_bronze_to_silver.py`

Purpose:
- Standardize column names and data types
- Conform keys/IDs across source systems
- Apply light data quality checks
- Write curated Silver tables

---

## 20 – Silver → Gold

`notebooks/20_silver_to_gold.py`

Purpose:
- Build reporting-friendly marts (star-schema style)
- Create aggregates / KPI-ready tables
- Output Gold tables/views for BI consumption

---

## Execution notes

Typical execution options:
- Run scripts manually in order for development/testing
- Schedule as a Databricks Job with three tasks (00 → 10 → 20)
- Parameterize paths/schemas via widgets or environment variables (dev/test/prod)
