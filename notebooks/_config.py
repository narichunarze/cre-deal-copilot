# Databricks notebook source
# MAGIC %md
# MAGIC ### Shared config (`%run ./_config`). Widgets are overridden by job parameters in `databricks.yml`.

# COMMAND ----------

dbutils.widgets.text("catalog", "main", "Catalog")
dbutils.widgets.text("schema", "cre_dd", "Schema")
# Any Foundation Model API chat endpoint (check Serving in your workspace).
dbutils.widgets.text("llm_endpoint", "databricks-gpt-oss-120b", "LLM endpoint")
dbutils.widgets.text("as_of_date", "2026-10-31", "Rent roll as-of date")

CATALOG = dbutils.widgets.get("catalog")
SCHEMA = dbutils.widgets.get("schema")
LLM = dbutils.widgets.get("llm_endpoint")
AS_OF = dbutils.widgets.get("as_of_date")
FQ = f"{CATALOG}.{SCHEMA}"
VOLUME = f"/Volumes/{CATALOG}/{SCHEMA}/deal_docs"
print(f"Schema: {FQ} | Volume: {VOLUME} | LLM: {LLM}")
