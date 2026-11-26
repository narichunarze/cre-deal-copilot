# Databricks notebook source
# MAGIC %md
# MAGIC # 04 · Investment Committee (IC) pre-screen memo with `ai_query`
# MAGIC The LLM writes using **only** the computed numbers and red flags; it never invents metrics.

# COMMAND ----------

# MAGIC %run ./_config

# COMMAND ----------

dbutils.widgets.dropdown("memo_language", "English", ["English", "Spanish"], "Memo language")
LANG = dbutils.widgets.get("memo_language")

PROMPT = f"""You are a senior acquisitions analyst at a diversified real estate investment firm.
Write a concise Investment Committee pre-screen memo in {LANG} (max ~350 words, Markdown) with sections:
1. Deal Snapshot  2. Seller Claims vs. Verified Data (a small table)  3. Key Risks  4. Upside
5. Recommendation & Next Diligence Steps (bulleted, specific).
Rules: use ONLY the numbers provided in the JSON; never invent figures; percentages are fractions (0.95 = 95%).
Do NOT cite market comps, benchmarks or per-unit values for the submarket: none are provided.
loan_amount / annual_debt_service describe the PROPOSED acquisition loan, not existing debt.
Keep the system recommendation unless the data clearly contradicts it.

DEAL DATA (JSON):
"""

# COMMAND ----------

spark.sql(f"""
  CREATE OR REPLACE TABLE {FQ}.ic_memos AS
  WITH flags AS (
    SELECT deal_id, collect_list(named_struct('severity', severity, 'message', message)) AS red_flags
    FROM {FQ}.deal_red_flags GROUP BY deal_id
  ),
  ctx AS (
    SELECT s.deal_id, s.property_name, s.recommendation,
           to_json(named_struct(
             'scorecard', struct(s.*),
             'red_flags', f.red_flags,
             'om_highlights', c.investment_highlights)) AS payload
    FROM {FQ}.deal_scorecard s
    LEFT JOIN flags f ON f.deal_id = s.deal_id
    LEFT JOIN {FQ}.om_claims c ON c.deal_id = s.deal_id
  )
  SELECT deal_id, property_name, recommendation,
         ai_query(:llm, concat(:prompt, payload)) AS memo_md,
         current_timestamp() AS generated_at
  FROM ctx
""", args={"llm": LLM, "prompt": PROMPT})

# COMMAND ----------

for r in spark.table(f"{FQ}.ic_memos").orderBy("deal_id").collect():
    displayHTML(f"<h2>{r.deal_id} · {r.property_name} — {r.recommendation}</h2><pre style='white-space:pre-wrap'>{r.memo_md}</pre>")
