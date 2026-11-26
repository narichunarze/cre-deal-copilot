# Databricks notebook source
# MAGIC %md
# MAGIC # 05 · Evaluate the LLM extractor (MLflow)
# MAGIC Never trust AI output blindly: compare the fields `ai_query` extracted from each OM against a labeled
# MAGIC ground truth, log field-level accuracy to MLflow, and fail the job if accuracy drops below threshold
# MAGIC (e.g. after switching the LLM endpoint or changing the prompt).

# COMMAND ----------

# MAGIC %run ./_config

# COMMAND ----------

dbutils.widgets.text("min_accuracy", "0.95", "Min field accuracy")
MIN_ACC = float(dbutils.widgets.get("min_accuracy"))

import mlflow
import pandas as pd

FIELDS = ["units", "asking_price", "claimed_occupancy_pct", "claimed_noi", "claimed_cap_rate_pct",
          "proposed_ltv_pct", "proposed_interest_rate_pct", "amortization_years"]

truth = pd.read_csv(f"{VOLUME}/om_ground_truth.csv")
pred = spark.table(f"{FQ}.om_claims").select("deal_id", *FIELDS).toPandas()
m = truth.merge(pred, on="deal_id", suffixes=("_true", "_pred"))

rows = []
for f in FIELDS:
    t, p = m[f"{f}_true"].astype(float), pd.to_numeric(m[f"{f}_pred"], errors="coerce")
    ok = ((p - t).abs() <= t.abs() * 0.005)  # 0.5% tolerance
    rows += [{"deal_id": d, "field": f, "expected": tv, "extracted": pv, "correct": bool(c)}
             for d, tv, pv, c in zip(m.deal_id, t, p, ok)]
results = pd.DataFrame(rows)
by_field = results.groupby("field")["correct"].mean()
overall = results["correct"].mean()

# COMMAND ----------

mlflow.set_experiment(f"/Users/{spark.sql('select current_user()').first()[0]}/cre_dd_extraction_eval")
with mlflow.start_run(run_name=f"om_extraction_{LLM}"):
    mlflow.log_params({"llm_endpoint": LLM, "n_deals": len(m), "tolerance": 0.005})
    mlflow.log_metric("field_accuracy", overall)
    for f, acc in by_field.items():
        mlflow.log_metric(f"acc_{f}", acc)
    mlflow.log_table(results, "extraction_results.json")

display(results[~results.correct] if (~results.correct).any() else by_field.reset_index())
print(f"Overall field accuracy: {overall:.1%}")
assert overall >= MIN_ACC, f"Extraction accuracy {overall:.1%} below threshold {MIN_ACC:.0%}"
