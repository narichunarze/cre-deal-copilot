# CRE Deal Due-Diligence Copilot (Databricks + GenAI)

An end-to-end Databricks solution that turns a broker deal package (Offering Memorandum PDF, rent roll, T-12)
into a **verified underwriting scorecard, red flags and an IC pre-screen memo in minutes instead of days**.
It is designed for the acquisitions team of a diversified real estate investment firm.

**Business problem and user stories:** [docs/DISCOVERY.md](docs/DISCOVERY.md)
**How AI was used and validated:** [docs/AI_ASSISTED_DEVELOPMENT.md](docs/AI_ASSISTED_DEVELOPMENT.md)
**Demo script:** [docs/DEMO_SCRIPT.md](docs/DEMO_SCRIPT.md)

## Architecture
```
 UC Volume (deal package)  ──file-arrival trigger──►  Databricks Workflow (Asset Bundle)
   OM.pdf, rent_roll.csv, t12.csv
        │
        ├─ 01 ingest_and_parse   Delta tables + data-quality gate; OM text via ai_parse_document
        ├─ 02 extract_om_claims  ai_query + strict JSON schema → seller claims
        ├─ 05 evaluate           MLflow field accuracy vs. labeled OMs → fails below 95%
        ├─ 03 underwrite         tested Python: occupancy, NOI T-12/T-3, cap rate, DSCR, delinquency,
        │                        rollover, loss-to-lease → red flags + recommendation
        └─ 04 ic_memo            ai_query writes the memo from computed numbers only
                                   │
         Databricks App (Streamlit) ◄─ deal_scorecard / deal_red_flags / ic_memos ─► Genie (optional)
```

### Key decisions
- **LLM for language, code for math.** Extraction and memo writing use AI. Every metric is computed in `src/underwriting.py` with unit tests, so it is auditable for the IC and for investors.
- **AI output is evaluated, not trusted.** A labeled ground-truth set plus MLflow tracks the extractor, and the job fails on regressions when the model or prompt changes.
- **SQL AI Functions over custom serving.** `ai_query` and `ai_parse_document` keep the MVP serverless, cheap and quick to ship. An agent framework can come later if the workflow needs multi-step reasoning.
- **Everything as code.** Asset Bundle (job + app), GitHub Actions (tests, reproducible data, deploy on `main`), Unity Catalog for governance.

## Results on the sample deals
| Deal | Finding | Verdict |
|---|---|---|
| D001 Lakeview (Dallas) | OM matches the data; DSCR 1.54x | PROCEED |
| D002 Riverbend (Houston) | OM says 95% occupancy, actual is 85.6%; NOI overstated by 30%; DSCR 1.10x | PASS / RE-PRICE |
| D003 Cedar Ridge (San Antonio) | Rents 10.7% below market (~$240K/yr upside); 38% of leases roll in 90 days | PROCEED WITH CAUTION |

## Run it
**Local (no Databricks needed):**
```bash
pip install -r requirements-dev.txt
python tests/test_underwriting.py   # prints the scorecard for the 3 deals
pytest -q tests
```

**Databricks (Asset Bundle):**
```bash
databricks bundle deploy -t dev --var warehouse_id=<sql-warehouse-id>
```
1. Run `notebooks/00_setup` once to create the schema and volume and load the sample package.
2. Run the job with `databricks bundle run deal_screening -t dev`, or unpause its file-arrival trigger.
3. Grant the app's service principal `SELECT` on the schema, then open the **cre-deal-copilot** app.

Parameters: `catalog`, `schema`, `llm_endpoint` (check **Serving** for the endpoints available in your workspace).

**CI/CD:** set the repo variables `DATABRICKS_HOST` and `DATABRICKS_WAREHOUSE_ID` and the secret `DATABRICKS_TOKEN`. A push to `main` then tests, validates and deploys.

## Repo layout
```
notebooks/   00 setup · 01 ingest+parse · 02 extract · 03 underwrite · 04 memo · 05 evaluate
src/         underwriting.py (metrics + rules) · quality.py (data-quality gates)
app/         Databricks App (Streamlit + chat)
tests/       unit tests for underwriting and data quality
scripts/     synthetic deal generator (with planted seller discrepancies + ground truth)
docs/        discovery, AI-assisted development log, demo script
```

## Roadmap
Retail and hospitality underwriting · market comps with Vector Search over the firm's past deals ·
connect the real deal inbox (SharePoint/email) · post-close tracking of actuals vs. underwriting.
