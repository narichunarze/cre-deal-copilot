# Databricks notebook source
# MAGIC %md
# MAGIC # 01 · Ingest + document parsing
# MAGIC - Rent roll and T-12 (CSV) → Delta tables, gated by data-quality checks.
# MAGIC - Offering Memorandums (PDF) → text with **`ai_parse_document`**.

# COMMAND ----------

# MAGIC %run ./_config

# COMMAND ----------

import os, sys
sys.path.append(os.path.abspath(".."))
from src.quality import check_rent_roll, check_t12

dfs = {name: spark.read.option("header", True).option("inferSchema", True).csv(f"{VOLUME}/{name}.csv")
       for name in ["rent_roll", "t12"]}

# Quality gate: fail the job before bad data reaches underwriting
errors = check_rent_roll(dfs["rent_roll"].toPandas()) + check_t12(dfs["t12"].toPandas())
if errors:
    raise ValueError("Data quality checks failed:\n- " + "\n- ".join(errors))

for name, df in dfs.items():
    df.write.mode("overwrite").option("overwriteSchema", True).saveAsTable(f"{FQ}.{name}")
display(spark.table(f"{FQ}.rent_roll").limit(10))

# COMMAND ----------

# MAGIC %md
# MAGIC ### Parse PDFs
# MAGIC `ai_parse_document` extracts text, tables and layout. If it is not enabled in your region/workspace,
# MAGIC the fallback reads the OM's `.md` version shipped with the repo.

# COMMAND ----------

try:
    spark.sql(f"""
      CREATE OR REPLACE TABLE {FQ}.om_documents AS
      WITH parsed AS (
        SELECT regexp_extract(path, '(D\\\\d+)_offering', 1) AS deal_id,
               path,
               ai_parse_document(content) AS doc
        FROM READ_FILES('{VOLUME}/*_offering_memorandum.pdf', format => 'binaryFile')
      )
      SELECT deal_id, path,
             concat_ws('\\n\\n', transform(try_cast(doc:document:elements AS ARRAY<VARIANT>),
                                          e -> try_cast(e:content AS STRING))) AS om_text
      FROM parsed
    """)
    print("Parsed with ai_parse_document")
except Exception as e:
    print(f"ai_parse_document unavailable ({type(e).__name__}); using .md fallback")
    spark.sql(f"""
      CREATE OR REPLACE TABLE {FQ}.om_documents AS
      SELECT regexp_extract(_metadata.file_path, '(D\\\\d+)_offering', 1) AS deal_id,
             _metadata.file_path AS path, value AS om_text
      FROM read_files('{VOLUME}/*_offering_memorandum.md', format => 'text', wholeText => true)
    """)

display(spark.table(f"{FQ}.om_documents"))
