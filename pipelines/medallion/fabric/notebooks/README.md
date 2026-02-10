# Fabric Medallion Pipeline (Healthcare Demo)

This folder contains the Fabric version of a simple Medallion (Bronze → Silver → Gold) pipeline.

## Run order

1. **00 – Bronze (manual load)**
2. **10_bronze_to_silver.py**
3. **20_silver_to_gold.py**

---

## 00 – Bronze (manual load)

In this Fabric demo, Bronze is created by placing raw source files directly into the Lakehouse.

**Bronze approach**
- Upload or copy raw files into the Lakehouse Files area
- Keep the files as close to “as-is” as possible (no business transforms)
- Treat this as the immutable landing zone for reprocessing

**Expected raw sources**
- HSA (Health System A): Excel workbook (multiple sheets)
- UCN (Urgent Care Network): multiple CSV files

---

## 10 – Bronze → Silver

`10_bronze_to_silver.py`

Purpose:
- Standardize column names / data types
- Conform IDs and key fields
- Apply light quality checks
- Write curated Silver tables

---

## 20 – Silver → Gold

`20_silver_to_gold.py`

Purpose:
- Build reporting-friendly marts (star schema style)
- Create aggregates / KPIs for Power BI
- Output Gold tables/views
