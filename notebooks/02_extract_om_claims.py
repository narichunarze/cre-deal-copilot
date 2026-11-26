# Databricks notebook source
# MAGIC %md
# MAGIC # 02 · Extract the seller's *claims* from the OM with `ai_query`
# MAGIC The LLM returns strict-schema JSON (`responseFormat`). These are the seller's claims,
# MAGIC verified against actual data in notebook 03 and evaluated for accuracy in notebook 05.

# COMMAND ----------

# MAGIC %run ./_config

# COMMAND ----------

import json

num = {"type": ["number", "null"]}
OM_SCHEMA = {
    "type": "json_schema",
    "json_schema": {
        "name": "om_claims",
        "strict": True,
        "schema": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "property_name": {"type": "string"},
                "city": {"type": "string"},
                "state": {"type": "string"},
                "units": num, "year_built": num, "asking_price": num,
                "claimed_occupancy_pct": num, "claimed_noi": num, "claimed_cap_rate_pct": num,
                "proposed_ltv_pct": num, "proposed_interest_rate_pct": num, "amortization_years": num,
                "investment_highlights": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["property_name", "city", "state", "units", "year_built", "asking_price",
                         "claimed_occupancy_pct", "claimed_noi", "claimed_cap_rate_pct", "proposed_ltv_pct",
                         "proposed_interest_rate_pct", "amortization_years", "investment_highlights"],
        },
    },
}
DDL = """property_name STRING, city STRING, state STRING, units DOUBLE, year_built DOUBLE, asking_price DOUBLE,
claimed_occupancy_pct DOUBLE, claimed_noi DOUBLE, claimed_cap_rate_pct DOUBLE, proposed_ltv_pct DOUBLE,
proposed_interest_rate_pct DOUBLE, amortization_years DOUBLE, investment_highlights ARRAY<STRING>""".replace("\n", " ")

PROMPT = """You are a commercial real estate analyst. Extract the seller's claims from this Offering Memorandum.
Percentages as numbers 0-100 (e.g. 95.0), money in USD without symbols. Use null if not stated.

OFFERING MEMORANDUM:
"""

# COMMAND ----------

spark.sql(f"""
  CREATE OR REPLACE TABLE {FQ}.om_claims AS
  SELECT deal_id, c.*, raw
  FROM (
    SELECT deal_id, raw, from_json(raw, '{DDL}') AS c
    FROM (
      SELECT deal_id,
             ai_query(:llm, concat(:prompt, om_text), responseFormat => :fmt) AS raw
      FROM {FQ}.om_documents
    )
  )
""", args={"llm": LLM, "prompt": PROMPT, "fmt": json.dumps(OM_SCHEMA)})

display(spark.table(f"{FQ}.om_claims"))
