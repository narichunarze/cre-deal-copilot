"""Generate synthetic data for 3 multifamily deals: rent roll (CSV), T-12 (CSV), Offering Memorandum (PDF + .md)
and the OM ground truth used to evaluate the LLM extractor.

Usage: python scripts/generate_sample_data.py  -> writes to data/deals/
OM figures are derived from the actual data with a per-deal "seller bias", so the copilot has
real discrepancies to catch.
"""
from __future__ import annotations

import os
from datetime import date, timedelta

import numpy as np
import pandas as pd
from reportlab import rl_config
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table

rl_config.invariant = 1  # byte-identical PDFs across runs
AS_OF = date(2026, 10, 31)
OUT = os.path.join(os.path.dirname(__file__), "..", "data", "deals")

DEALS = [
    dict(deal_id="D001", name="Lakeview Apartments", city="Dallas", state="TX", units=240, year_built=2008,
         price=40_000_000, base_rent=1650, ltl=0.03, occ_start=0.94, occ_end=0.94, conc=0.01, bad_debt=0.01,
         delinq_share=0.02, rm=900, ins=700, ltv=0.60, rate=0.0625, amort=30, rollover_90=0.15,
         om_occ_bias=0.005, om_noi_bias=1.01,
         highlights=["Class B+ asset in a high-growth Dallas submarket",
                     "Stable occupancy with in-place rents near market",
                     "Professional management in place since 2019"]),
    dict(deal_id="D002", name="Riverbend Commons", city="Houston", state="TX", units=180, year_built=1985,
         price=15_500_000, base_rent=1250, ltl=0.04, occ_start=0.93, occ_end=0.85, conc=0.02, bad_debt=0.025,
         delinq_share=0.06, rm=2100, ins=900, ltv=0.75, rate=0.065, amort=30, rollover_90=0.20,
         om_occ_bias=None, om_occ_claim=0.95, om_noi_bias=1.30,
         highlights=["Stabilized 95% occupied asset with strong cash flow",
                     "Recently renovated clubhouse and pool",
                     "Attractive going-in cap rate above market average"]),
    dict(deal_id="D003", name="Cedar Ridge Residences", city="San Antonio", state="TX", units=150, year_built=1999,
         price=16_500_000, base_rent=1350, ltl=0.11, occ_start=0.93, occ_end=0.93, conc=0.01, bad_debt=0.03,
         delinq_share=0.025, rm=950, ins=750, ltv=0.60, rate=0.064, amort=30, rollover_90=0.38,
         om_occ_bias=0.01, om_noi_bias=1.03,
         highlights=["Value-add opportunity: in-place rents ~12% below market",
                     "Interior upgrade program can lift rents $150-$200/unit",
                     "Near major employers and Joint Base San Antonio"]),
]

UNIT_MIX = [("1BR", 720, 0.85, 0.45), ("2BR", 1050, 1.15, 0.40), ("3BR", 1300, 1.40, 0.15)]


def rent_roll(d: dict, rng: np.random.Generator) -> pd.DataFrame:
    rows = []
    n = d["units"]
    types = rng.choice(len(UNIT_MIX), size=n, p=[m[3] for m in UNIT_MIX])
    occupied = rng.random(n) < d["occ_end"]
    delinquent = rng.random(n) < d["delinq_share"]
    rolling = rng.random(n) < d["rollover_90"]
    for i in range(n):
        utype, sqft, mult, _ = UNIT_MIX[types[i]]
        market = round(d["base_rent"] * mult * rng.uniform(0.97, 1.03), 0)
        if occupied[i]:
            actual = round(market * (1 - d["ltl"]) * rng.uniform(0.97, 1.03), 0)
            start = AS_OF - timedelta(days=int(rng.integers(30, 700)))
            if rolling[i]:
                end = AS_OF + timedelta(days=int(rng.integers(1, 90)))
            else:
                end = AS_OF + timedelta(days=int(rng.integers(91, 365)))
            status = "Occupied"
            balance = round(actual * rng.uniform(0.5, 2.0), 2) if delinquent[i] else 0.0
        else:
            actual, start, end, status, balance = 0.0, None, None, "Vacant", 0.0
        rows.append(dict(deal_id=d["deal_id"], unit=f"{100 + i}", unit_type=utype,
                         sqft=int(sqft * rng.uniform(0.95, 1.05)), market_rent=market, actual_rent=actual,
                         status=status, lease_start=start, lease_end=end, balance_due=balance))
    return pd.DataFrame(rows)


def t12(d: dict, rr: pd.DataFrame, rng: np.random.Generator) -> pd.DataFrame:
    gpr_m = rr["market_rent"].sum()
    rows = []
    months = pd.period_range(end=pd.Period(AS_OF, "M"), periods=12, freq="M")
    taxes = d["price"] * 0.016
    for k, m in enumerate(months):
        occ = d["occ_start"] + (d["occ_end"] - d["occ_start"]) * k / 11
        noise = lambda: rng.uniform(0.97, 1.03)
        rev = {
            "Gross Potential Rent": gpr_m,
            "Loss to Lease": -gpr_m * d["ltl"] * noise(),
            "Vacancy Loss": -gpr_m * (1 - occ),
            "Concessions": -gpr_m * d["conc"] * noise(),
            "Bad Debt": -gpr_m * d["bad_debt"] * noise(),
            "Other Income": d["units"] * 65 * noise(),
        }
        egi = sum(rev.values())
        exp = {
            "Payroll": d["units"] * 1400 / 12 * noise(),
            "Repairs & Maintenance": d["units"] * d["rm"] / 12 * noise(),
            "Utilities": d["units"] * 1100 / 12 * noise(),
            "Insurance": d["units"] * d["ins"] / 12,
            "Property Taxes": taxes / 12,
            "Management Fee": egi * 0.03,
            "Administrative": d["units"] * 250 / 12 * noise(),
            "Marketing": d["units"] * 150 / 12 * noise(),
            "Contract Services": d["units"] * 300 / 12 * noise(),
        }
        for li, v in rev.items():
            rows.append(dict(deal_id=d["deal_id"], month=str(m), category="Revenue", line_item=li, amount=round(v, 2)))
        for li, v in exp.items():
            rows.append(dict(deal_id=d["deal_id"], month=str(m), category="Expense", line_item=li, amount=round(v, 2)))
    return pd.DataFrame(rows)


def om_text(d: dict, rr: pd.DataFrame, t: pd.DataFrame) -> tuple[str, list]:
    actual_occ = (rr["status"] == "Occupied").mean()
    occ_claim = d.get("om_occ_claim") or (actual_occ + d["om_occ_bias"])
    rev = t[t.category == "Revenue"].amount.sum()
    exp = t[t.category == "Expense"].amount.sum()
    noi_claim = round((rev - exp) * d["om_noi_bias"], -3)
    cap = noi_claim / d["price"]
    sections = [
        ("title", f"{d['name']} - Confidential Offering Memorandum"),
        ("p", f"{d['units']}-unit multifamily community | {d['city']}, {d['state']} | Built {d['year_built']}"),
        ("h", "Offering Summary"),
        ("table", [["Asking Price", f"${d['price']:,.0f}"],
                   ["Price per Unit", f"${d['price'] / d['units']:,.0f}"],
                   ["Current Occupancy", f"{occ_claim:.1%}"],
                   ["Net Operating Income (T-12)", f"${noi_claim:,.0f}"],
                   ["Going-in Cap Rate", f"{cap:.2%}"]]),
        ("h", "Investment Highlights"),
        *[("bullet", h) for h in d["highlights"]],
        ("h", "Proposed Financing"),
        ("p", f"Agency loan at {d['ltv']:.0%} LTV, {d['rate']:.2%} fixed interest rate, "
              f"{d['amort']}-year amortization, 10-year term."),
        ("h", "Disclosures"),
        ("p", "Information herein was obtained from sources deemed reliable but is not guaranteed. "
              "Buyers should conduct their own due diligence."),
    ]
    md = []
    for kind, content in sections:
        if kind == "title": md.append(f"# {content}")
        elif kind == "h": md.append(f"\n## {content}")
        elif kind == "bullet": md.append(f"- {content}")
        elif kind == "table": md += [f"- **{k}:** {v}" for k, v in content]
        else: md.append(content)
    truth = dict(deal_id=d["deal_id"], property_name=d["name"], units=d["units"], asking_price=d["price"],
                 claimed_occupancy_pct=round(occ_claim * 100, 1), claimed_noi=noi_claim,
                 claimed_cap_rate_pct=round(cap * 100, 2), proposed_ltv_pct=d["ltv"] * 100,
                 proposed_interest_rate_pct=d["rate"] * 100, amortization_years=d["amort"])
    return "\n".join(md), sections, truth


def write_pdf(path: str, sections: list) -> None:
    ss = getSampleStyleSheet()
    flow = []
    for kind, content in sections:
        if kind == "title": flow.append(Paragraph(content, ss["Title"]))
        elif kind == "h": flow += [Spacer(1, 10), Paragraph(content, ss["Heading2"])]
        elif kind == "bullet": flow.append(Paragraph(f"&bull; {content}", ss["BodyText"]))
        elif kind == "table": flow.append(Table(content, colWidths=[220, 180]))
        else: flow.append(Paragraph(content, ss["BodyText"]))
    SimpleDocTemplate(path, pagesize=letter).build(flow)


def main() -> None:
    os.makedirs(OUT, exist_ok=True)
    rng = np.random.default_rng(1999)
    rrs, t12s, truths = [], [], []
    for d in DEALS:
        rr = rent_roll(d, rng)
        t = t12(d, rr, rng)
        md, sections, truth = om_text(d, rr, t)
        truths.append(truth)
        write_pdf(os.path.join(OUT, f"{d['deal_id']}_offering_memorandum.pdf"), sections)
        with open(os.path.join(OUT, f"{d['deal_id']}_offering_memorandum.md"), "w") as f:
            f.write(md)
        rrs.append(rr); t12s.append(t)
    pd.concat(rrs).to_csv(os.path.join(OUT, "rent_roll.csv"), index=False)
    pd.concat(t12s).to_csv(os.path.join(OUT, "t12.csv"), index=False)
    # Ground truth for evaluating the LLM extractor (notebook 05)
    pd.DataFrame(truths).to_csv(os.path.join(OUT, "om_ground_truth.csv"), index=False)
    print(f"OK -> {os.path.abspath(OUT)}")


if __name__ == "__main__":
    main()
