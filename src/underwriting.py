"""Deterministic underwriting: verified metrics (rent roll + T-12) vs. what the OM claims.

Design decision: the LLM only *reads* the OM and *writes* the memo. Every number is computed here,
so results are auditable, reproducible and unit-tested.
"""
from __future__ import annotations

from datetime import date, timedelta

import pandas as pd


def annual_debt_service(loan: float, rate: float, amort_years: int) -> float:
    r, n = rate / 12, amort_years * 12
    if r == 0:
        return loan / amort_years
    return loan * r / (1 - (1 + r) ** -n) * 12


def rent_roll_metrics(rr: pd.DataFrame, as_of: date) -> dict:
    occ = rr[rr["status"] == "Occupied"]
    lease_end = pd.to_datetime(occ["lease_end"])
    expiring = ((lease_end > pd.Timestamp(as_of)) & (lease_end <= pd.Timestamp(as_of + timedelta(days=90)))).sum()
    market_occ = occ["market_rent"].sum()
    return {
        "units": int(len(rr)),
        "physical_occupancy": len(occ) / len(rr),
        "economic_occupancy": occ["actual_rent"].sum() / rr["market_rent"].sum(),
        "avg_market_rent": rr["market_rent"].mean(),
        "avg_in_place_rent": occ["actual_rent"].mean(),
        "loss_to_lease_pct": 1 - occ["actual_rent"].sum() / market_occ if market_occ else 0.0,
        "delinquency_pct": rr["balance_due"].sum() / occ["actual_rent"].sum() if len(occ) else 0.0,
        "delinquent_units": int((rr["balance_due"] > 0).sum()),
        "rollover_90d_pct": expiring / len(occ) if len(occ) else 0.0,
    }


def t12_metrics(t12: pd.DataFrame) -> dict:
    rev = t12[t12["category"] == "Revenue"]
    exp = t12[t12["category"] == "Expense"]
    egi, opex = rev["amount"].sum(), exp["amount"].sum()
    by_line = exp.groupby("line_item")["amount"].sum()
    monthly = t12.assign(signed=t12["amount"].where(t12["category"] == "Revenue", -t12["amount"])) \
                 .groupby("month")["signed"].sum().sort_index()
    return {
        "t12_egi": egi,
        "t12_opex": opex,
        "t12_noi": egi - opex,
        "expense_ratio": opex / egi if egi else 0.0,
        "rm_per_unit_share": by_line.get("Repairs & Maintenance", 0.0) / opex if opex else 0.0,
        # Last-3-months annualized NOI (T-3) vs. T-12: catches deteriorating trends
        "t3_annualized_noi": monthly.tail(3).sum() * 4,
    }


def compute_scorecard(rr: pd.DataFrame, t12: pd.DataFrame, om: dict, as_of: date) -> dict:
    sc = {**rent_roll_metrics(rr, as_of), **t12_metrics(t12)}
    price = om.get("asking_price") or 0
    sc["asking_price"] = price
    sc["price_per_unit"] = price / sc["units"] if price else None
    sc["cap_rate_actual"] = sc["t12_noi"] / price if price else None
    sc["cap_rate_t3"] = sc["t3_annualized_noi"] / price if price else None
    ltv, rate, amort = om.get("proposed_ltv_pct"), om.get("proposed_interest_rate_pct"), om.get("amortization_years")
    if price and ltv and rate and amort:
        loan = price * ltv / 100
        ds = annual_debt_service(loan, rate / 100, int(amort))
        sc.update(loan_amount=loan, annual_debt_service=ds, dscr=sc["t12_noi"] / ds, dscr_t3=sc["t3_annualized_noi"] / ds)
    # Seller claims (for comparison)
    sc["om_occupancy"] = (om.get("claimed_occupancy_pct") or 0) / 100 or None
    sc["om_noi"] = om.get("claimed_noi")
    sc["om_cap_rate"] = (om.get("claimed_cap_rate_pct") or 0) / 100 or None
    return sc


def red_flags(sc: dict) -> list[dict]:
    """Simple, explainable rules. severity: HIGH | MEDIUM | OPPORTUNITY."""
    flags: list[dict] = []

    def add(sev, code, msg):
        flags.append({"severity": sev, "code": code, "message": msg})

    if sc.get("om_occupancy"):
        gap = sc["om_occupancy"] - sc["physical_occupancy"]
        if gap > 0.02:
            add("HIGH" if gap > 0.05 else "MEDIUM", "OCCUPANCY_OVERSTATED",
                f"OM claims {sc['om_occupancy']:.1%} occupancy; rent roll shows {sc['physical_occupancy']:.1%} ({gap:.1%} gap).")
    if sc.get("om_noi") and sc["t12_noi"] > 0:
        gap = sc["om_noi"] / sc["t12_noi"] - 1
        if gap > 0.05:
            add("HIGH" if gap > 0.10 else "MEDIUM", "NOI_OVERSTATED",
                f"OM NOI ${sc['om_noi']:,.0f} is {gap:.0%} above T-12 NOI ${sc['t12_noi']:,.0f}.")
    if sc["t3_annualized_noi"] < sc["t12_noi"] * 0.95:
        add("MEDIUM", "NOI_DECLINING",
            f"Last-3-months annualized NOI ${sc['t3_annualized_noi']:,.0f} is "
            f"{1 - sc['t3_annualized_noi'] / sc['t12_noi']:.0%} below T-12.")
    if "dscr" in sc:
        if sc["dscr"] < 1.25:
            add("HIGH", "LOW_DSCR", f"DSCR {sc['dscr']:.2f}x on actual T-12 NOI is below 1.25x lender minimum.")
        elif sc["dscr"] < 1.35:
            add("MEDIUM", "THIN_DSCR", f"DSCR {sc['dscr']:.2f}x leaves little cushion.")
    if sc["delinquency_pct"] > 0.03:
        add("HIGH" if sc["delinquency_pct"] > 0.05 else "MEDIUM", "DELINQUENCY",
            f"Outstanding balances equal {sc['delinquency_pct']:.1%} of monthly rent ({sc['delinquent_units']} units).")
    if sc["rollover_90d_pct"] > 0.25:
        add("MEDIUM", "LEASE_ROLLOVER", f"{sc['rollover_90d_pct']:.0%} of occupied leases expire in the next 90 days.")
    if sc["expense_ratio"] > 0.55:
        add("MEDIUM", "HIGH_OPEX", f"Expense ratio {sc['expense_ratio']:.0%} of EGI "
            f"(R&M is {sc['rm_per_unit_share']:.0%} of OpEx).")
    if sc["loss_to_lease_pct"] > 0.08:
        add("OPPORTUNITY", "LOSS_TO_LEASE",
            f"In-place rents are {sc['loss_to_lease_pct']:.1%} below market: "
            f"~${(sc['avg_market_rent'] - sc['avg_in_place_rent']) * sc['units'] * sc['physical_occupancy'] * 12:,.0f}/yr upside.")
    return flags


def recommendation(flags: list[dict]) -> str:
    highs = sum(f["severity"] == "HIGH" for f in flags)
    meds = sum(f["severity"] == "MEDIUM" for f in flags)
    if highs >= 2:
        return "PASS / RE-PRICE"
    if highs == 1 or meds >= 2:
        return "PROCEED WITH CAUTION"
    return "PROCEED"
