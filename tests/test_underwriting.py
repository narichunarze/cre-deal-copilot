import os, re, sys
from datetime import date

import pandas as pd

ROOT = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, ROOT)
from src.underwriting import annual_debt_service, compute_scorecard, recommendation, red_flags  # noqa: E402

DATA = os.path.join(ROOT, "data", "deals")
AS_OF = date(2026, 10, 31)


def om_from_md(deal_id: str) -> dict:
    """Local stand-in for the LLM extractor: regex over the OM markdown."""
    txt = open(os.path.join(DATA, f"{deal_id}_offering_memorandum.md")).read()
    num = lambda p: float(re.search(p, txt).group(1).replace(",", ""))
    return dict(asking_price=num(r"Asking Price:\*\* \$([\d,]+)"),
                claimed_occupancy_pct=num(r"Occupancy:\*\* ([\d.]+)%"),
                claimed_noi=num(r"T-12\):\*\* \$([\d,]+)"),
                claimed_cap_rate_pct=num(r"Cap Rate:\*\* ([\d.]+)%"),
                proposed_ltv_pct=num(r"at (\d+)% LTV"),
                proposed_interest_rate_pct=num(r"([\d.]+)% fixed"),
                amortization_years=num(r"(\d+)-year amortization"))


def run(deal_id):
    rr = pd.read_csv(os.path.join(DATA, "rent_roll.csv")).query("deal_id == @deal_id")
    t12 = pd.read_csv(os.path.join(DATA, "t12.csv")).query("deal_id == @deal_id")
    sc = compute_scorecard(rr, t12, om_from_md(deal_id), AS_OF)
    flags = red_flags(sc)
    return sc, flags, recommendation(flags)


def test_debt_service():
    assert round(annual_debt_service(1_000_000, 0.06, 30)) == 71946


def test_clean_deal_proceeds():
    _, flags, rec = run("D001")
    assert rec == "PROCEED", flags


def test_bad_deal_flags():
    _, flags, rec = run("D002")
    codes = {f["code"] for f in flags}
    assert {"OCCUPANCY_OVERSTATED", "NOI_OVERSTATED", "LOW_DSCR"} <= codes
    assert rec == "PASS / RE-PRICE"


def test_value_add_opportunity():
    _, flags, _ = run("D003")
    codes = {f["code"] for f in flags}
    assert "LOSS_TO_LEASE" in codes and "LEASE_ROLLOVER" in codes


if __name__ == "__main__":
    for d in ["D001", "D002", "D003"]:
        sc, flags, rec = run(d)
        print(f"\n== {d}: {rec} | occ {sc['physical_occupancy']:.1%} | NOI ${sc['t12_noi']:,.0f} | "
              f"cap {sc['cap_rate_actual']:.2%} | DSCR {sc['dscr']:.2f}x")
        for f in flags:
            print(f"  [{f['severity']}] {f['message']}")
