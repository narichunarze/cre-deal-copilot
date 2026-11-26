"""Data-quality gates run before underwriting. Any error fails the job (bad data never reaches the IC)."""
from __future__ import annotations

import pandas as pd

RENT_ROLL_COLS = {"deal_id", "unit", "unit_type", "sqft", "market_rent", "actual_rent", "status",
                  "lease_start", "lease_end", "balance_due"}
T12_COLS = {"deal_id", "month", "category", "line_item", "amount"}
REQUIRED_T12_LINES = {"Gross Potential Rent", "Property Taxes", "Insurance"}


def check_rent_roll(rr: pd.DataFrame) -> list[str]:
    missing = RENT_ROLL_COLS - set(rr.columns)
    if missing:
        return [f"rent_roll missing columns: {sorted(missing)}"]
    errors = []
    dup = rr.duplicated(["deal_id", "unit"]).sum()
    if dup:
        errors.append(f"rent_roll has {dup} duplicate (deal_id, unit) rows")
    if (rr[["market_rent", "actual_rent", "balance_due"]] < 0).any().any():
        errors.append("rent_roll has negative rent or balance values")
    bad_status = set(rr["status"]) - {"Occupied", "Vacant"}
    if bad_status:
        errors.append(f"rent_roll has unknown status values: {sorted(bad_status)}")
    occ_zero = ((rr["status"] == "Occupied") & (rr["actual_rent"] <= 0)).sum()
    if occ_zero:
        errors.append(f"rent_roll has {occ_zero} occupied units with zero rent")
    return errors


def check_t12(t12: pd.DataFrame) -> list[str]:
    missing = T12_COLS - set(t12.columns)
    if missing:
        return [f"t12 missing columns: {sorted(missing)}"]
    errors = []
    for deal, g in t12.groupby("deal_id"):
        if g["month"].nunique() != 12:
            errors.append(f"{deal}: T-12 has {g['month'].nunique()} months (expected 12)")
        lines = REQUIRED_T12_LINES - set(g["line_item"])
        if lines:
            errors.append(f"{deal}: T-12 missing line items {sorted(lines)}")
    return errors
