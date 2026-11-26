# Business Discovery: Deal Pre-Screening for a Real Estate Investment Firm

## Context
The client is a privately held, diversified real estate investment firm. It buys commercial real estate across several
U.S. states (multifamily, retail, hospitality) and raises capital from accredited investors through an in-house investor
relations arm.

## Problem statement
Every deal arrives as a broker package: an Offering Memorandum (OM), a rent roll and a T-12.
Analysts re-key the figures into spreadsheets to check whether the seller's story holds up.
- It is **slow**: roughly 1–3 analyst days per deal before a go/no-go.
- It is **inconsistent**: each analyst applies different checks.
- It is **risky**: an inflated occupancy or NOI that slips through means overpaying, or committing debt the asset cannot cover.

## Stakeholders
| Role | Need |
|---|---|
| Acquisitions analyst | Skip the re-keying and get a first-pass verdict in minutes |
| Head of Acquisitions / IC | Consistent, comparable pre-screens with clear red flags |
| Asset management | The same metrics later serve as the post-close baseline |
| Investor relations / capital raising | Defensible numbers behind every offering presented to investors |

## User stories and acceptance criteria
1. **As an analyst**, I drop a deal package in a folder and get verified metrics without manual data entry.
   - *AC:* rent roll and T-12 are loaded to Delta. Malformed files fail loudly with the exact reason (duplicate units, missing months, negative rents).
2. **As an analyst**, I see where the OM disagrees with the actual data.
   - *AC:* occupancy, NOI and cap rate are shown side by side as OM vs. verified. Gaps above the threshold become HIGH/MEDIUM flags.
3. **As the IC**, I get a one-page memo with a recommendation and the next diligence steps.
   - *AC:* the memo uses only computed numbers and ends in one of PROCEED / PROCEED WITH CAUTION / PASS-RE-PRICE.
4. **As the head of acquisitions**, I can trust the AI output.
   - *AC:* extraction accuracy is measured against labeled OMs on every run, and the pipeline stops if it falls below 95%.
5. **As an analyst**, I can ask follow-ups ("what price gets DSCR to 1.30x?").
   - *AC:* a chat in the app answers using only that deal's data and shows its math.

## Success metrics (pilot)
- Time to first-pass screen: **days → under 15 minutes**.
- 100% of screened deals carry a standardized scorecard.
- Extraction field accuracy of at least 95% on the labeled set.
- Analyst adoption: share of new deals screened through the copilot.

## Assumptions and open questions for stakeholders
- Which asset classes come first? (The MVP covers multifamily. Retail and hospitality need tenant rent rolls and STR/ADR data.)
- What DSCR, occupancy and expense-ratio thresholds does the client's IC actually use? (These are configurable rules today.)
- Where do deal packages live today (email, SharePoint, Dealpath)? That decides the ingestion connector.
- Which lenders and loan terms should be the default when the OM gives none?
