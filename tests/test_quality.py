import os, sys

import pandas as pd

ROOT = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, ROOT)
from src.quality import check_rent_roll, check_t12  # noqa: E402

DATA = os.path.join(ROOT, "data", "deals")


def test_sample_data_is_clean():
    assert check_rent_roll(pd.read_csv(os.path.join(DATA, "rent_roll.csv"))) == []
    assert check_t12(pd.read_csv(os.path.join(DATA, "t12.csv"))) == []


def test_catches_bad_rent_roll():
    rr = pd.read_csv(os.path.join(DATA, "rent_roll.csv")).head(5)
    rr = pd.concat([rr, rr.head(1)])               # duplicate unit
    rr.loc[rr.index[1], "actual_rent"] = -10       # negative rent
    errors = check_rent_roll(rr)
    assert any("duplicate" in e for e in errors) and any("negative" in e for e in errors)


def test_catches_incomplete_t12():
    t12 = pd.read_csv(os.path.join(DATA, "t12.csv"))
    t12 = t12[t12["month"] != t12["month"].max()]
    assert any("11 months" in e for e in check_t12(t12))
