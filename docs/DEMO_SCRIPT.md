# 5-Minute Demo Script

1. **The problem (30s).** "Every deal comes as an OM, a rent roll and a T-12. Analysts spend days re-keying them, and the seller's numbers are optimistic."
2. **Drop a package (30s).** Show the UC volume, then the Workflow DAG: ingest → extract → evaluate → underwrite → memo.
3. **Catch the seller (90s).** Riverbend Commons: the OM says 95% occupancy, the rent roll says 85.6%, NOI is overstated by 30%, and on actual NOI the DSCR is 1.10x. The verdict is **PASS / RE-PRICE**.
4. **Find the upside (45s).** Cedar Ridge: rents about 11% below market (~$240K/yr upside) but 38% of leases roll in 90 days. The verdict is **PROCEED WITH CAUTION**.
5. **Trust (45s).** The LLM never does the math. Show the MLflow extraction accuracy run and the failing quality gate on a corrupted rent roll.
6. **Ask a question (30s).** In the app: "What price would get DSCR to 1.30x?"
7. **Next (30s).** Retail and hospitality, comps from the firm's past deals with Vector Search, and a hook into the real deal inbox.
