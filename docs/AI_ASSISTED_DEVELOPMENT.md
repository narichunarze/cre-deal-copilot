# How This Was Built (AI-First, Human-Verified)

I built this with an AI coding agent (Claude Code), used across the lifecycle: discovery framing, architecture,
code generation, synthetic data, tests and documentation. The rule throughout: **AI accelerates, engineering judgment decides.**

## Where AI was used
- **Discovery and design:** drafting user stories, the KPIs and the split between LLM and deterministic code.
- **Code:** a first draft of the notebooks, the underwriting module, the app and the bundle/CI config.
- **Data:** a synthetic deal generator with planted discrepancies, so the system has real issues to catch.
- **Tests and docs:** unit tests, data-quality tests, the README and this document.

## Design guardrails (applied to the product, not only the dev process)
- **The LLM never computes numbers.** It reads (extraction into a strict JSON schema) and writes (the memo). Underwriting math lives in `src/underwriting.py` and is unit-tested.
- **AI output is measured.** `05_evaluate_extraction` scores field accuracy in MLflow and fails the job under threshold, so a model or prompt change cannot silently break it.
- **Bad data fails fast.** Quality gates run before underwriting.

## AI-generated issues caught in review
| Issue in the AI draft | How it was caught | Fix |
|---|---|---|
| Invalid Spark SQL: `from_json(...) AS claims.*` | Code review against the Spark SQL grammar | Nested subquery with `c.*` |
| `collect_list` over a LEFT JOIN added a `{null, null}` flag for deals with no flags | Reasoning through the clean deal (D001) | `filter(..., x -> x.severity IS NOT NULL)` |
| The patched query then failed on Databricks with `MISSING_AGGREGATION` (`GROUP BY ALL` + `struct(s.*)`) | First end-to-end run of the Workflow on a live workspace | Aggregate flags in their own CTE, then join |
| Empty flag list would crash `createDataFrame` (no schema to infer) | Edge-case review | Explicit schema |
| PDFs differed on every run (embedded timestamps), so the CI reproducibility check failed | A CI-style `git diff --exit-code` check | `rl_config.invariant = 1` |
| First live memo invented a submarket comp ("~$100k/unit in Houston") and called the proposed loan "current debt" | Reading the generated memo against the input JSON | Explicit prompt rules; re-ran and checked the memo no longer cites comps |
| The value-add deal scored PASS, which is unrealistic | Domain sanity check of the output | Re-tuned the synthetic data and verified that the rules behave as an analyst would expect |

## Still to verify in a live workspace
- Endpoint names available in the workspace's Serving page (`llm_endpoint` is a parameter).
- That `ai_parse_document` is enabled in the region (Beta). A fallback path exists if it is not.
