# Databricks notebook source
# MAGIC %md
# MAGIC # 00 · Setup — CRE Deal Due-Diligence Copilot
# MAGIC Creates the Unity Catalog schema + volume and loads the sample deal package (rent roll, T-12, OM PDFs).
# MAGIC
# MAGIC In production, the acquisitions team just drops each deal package into the volume (a file-arrival trigger runs the job).

# COMMAND ----------

# MAGIC %run ./_config

# COMMAND ----------

spark.sql(f"CREATE SCHEMA IF NOT EXISTS {FQ}")
spark.sql(f"CREATE VOLUME IF NOT EXISTS {FQ}.deal_docs")

# COMMAND ----------

import os

# Repo lives in a Git folder / bundle: data/ files are reachable by local path.
src = os.path.abspath("../data/deals")
for f in sorted(os.listdir(src)):
    dbutils.fs.cp(f"file:{src}/{f}", f"{VOLUME}/{f}")
display(dbutils.fs.ls(VOLUME))
