# Databricks notebook source
# MAGIC %md
# MAGIC # 03 · Deterministic underwriting + red flags
# MAGIC Metrics are computed in tested code (`src/underwriting.py`), **not** by the LLM:
# MAGIC physical/economic occupancy, loss-to-lease, delinquency, 90-day rollover, T-12 and T-3 NOI, cap rate, DSCR.
# MAGIC Then compared against the OM's claims.

# COMMAND ----------

# MAGIC %run ./_config

# COMMAND ----------

import os, sys
from datetime import date

import pandas as pd

sys.path.append(os.path.abspath(".."))
from src.underwriting import compute_scorecard, recommendation, red_flags

as_of = date.fromisoformat(AS_OF)
rr_all = spark.table(f"{FQ}.rent_roll").toPandas()
t12_all = spark.table(f"{FQ}.t12").toPandas()
claims = spark.table(f"{FQ}.om_claims").drop("raw").toPandas()

scores, flags = [], []
for _, om in claims.iterrows():
    d = om["deal_id"]
    sc = compute_scorecard(rr_all[rr_all.deal_id == d], t12_all[t12_all.deal_id == d], om.to_dict(), as_of)
    fl = red_flags(sc)
    scores.append({"deal_id": d, "property_name": om["property_name"],
                   "location": f"{om['city']}, {om['state']}", "recommendation": recommendation(fl),
                   "high_flags": sum(f["severity"] == "HIGH" for f in fl), **sc})
    flags += [{"deal_id": d, **f} for f in fl]

spark.createDataFrame(pd.DataFrame(scores)).write.mode("overwrite").option("overwriteSchema", True) \
     .saveAsTable(f"{FQ}.deal_scorecard")
spark.createDataFrame(pd.DataFrame(flags, columns=["deal_id", "severity", "code", "message"]),
                      "deal_id string, severity string, code string, message string").write.mode("overwrite").option("overwriteSchema", True) \
     .saveAsTable(f"{FQ}.deal_red_flags")

# COMMAND ----------

display(spark.sql(f"""
  SELECT deal_id, property_name, recommendation,
         round(physical_occupancy*100,1) AS occ_actual, round(om_occupancy*100,1) AS occ_om,
         round(t12_noi) AS noi_t12, round(om_noi) AS noi_om,
         round(cap_rate_actual*100,2) AS cap_actual, round(dscr,2) AS dscr
  FROM {FQ}.deal_scorecard ORDER BY deal_id"""))
display(spark.table(f"{FQ}.deal_red_flags"))
