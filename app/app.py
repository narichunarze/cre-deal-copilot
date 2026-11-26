"""Databricks App (Streamlit): deal screening workspace for the acquisitions team.

Reads the scorecard, red flags and IC memos produced by the screening job and lets an analyst
ask follow-up questions about a deal. Set DD_LOCAL_SNAPSHOT to a folder of parquet files
(deal_scorecard, deal_red_flags, ic_memos) to preview the UI without a SQL warehouse.
"""
import html
import json
import os

import pandas as pd
import streamlit as st

FQ = os.getenv("DD_SCHEMA", "main.cre_dd")
LLM = os.getenv("LLM_ENDPOINT", "databricks-gpt-oss-120b")
SNAPSHOT = os.getenv("DD_LOCAL_SNAPSHOT")

st.set_page_config(page_title="CRE Deal Screening", layout="wide", initial_sidebar_state="collapsed")

# --------------------------------------------------------------------------- styles
st.markdown("""
<style>
:root{--bg:#F5F6F8;--surface:#FFFFFF;--line:#E4E7EC;--text:#101828;--muted:#667085;--navy:#0F2A4A;
--red:#B42318;--red-bg:#FEF3F2;--amber:#B54708;--amber-bg:#FFFAEB;--green:#067647;--green-bg:#ECFDF3;}
html,body,[class*="css"],.stApp{font-family:Inter,system-ui,sans-serif;color:var(--text)}
.stApp{background:var(--bg)}
#MainMenu,footer,header[data-testid="stHeader"],[data-testid="stToolbar"],[data-testid="stDecoration"]{display:none!important}
.block-container{padding-top:0!important;margin-top:-16px;padding-bottom:48px;max-width:1240px}
.topbar{background:var(--navy);color:#fff;margin:0 -100vw 28px;padding:14px 100vw;display:flex;justify-content:space-between;align-items:center}
.topbar .brand{font-weight:600;font-size:15px;letter-spacing:.02em}
.topbar .brand span{opacity:.6;font-weight:400;margin-left:10px}
.topbar .env{font-size:12px;opacity:.75;letter-spacing:.04em}
div.page{font-size:26px;font-weight:600;margin:0 0 4px;letter-spacing:-.01em}
div.lead{color:var(--muted);font-size:14px;margin:0 0 22px}
.eyebrow{font-size:11px;font-weight:600;letter-spacing:.08em;text-transform:uppercase;color:var(--muted);margin:0 0 10px}
.card{background:var(--surface);border:1px solid var(--line);border-radius:10px;padding:18px 20px}
.grid{display:grid;gap:14px}.g4{grid-template-columns:repeat(4,minmax(0,1fr))}.g5{grid-template-columns:repeat(5,minmax(0,1fr))}
.stat .v{font-size:26px;font-weight:600;letter-spacing:-.01em;margin-top:6px;font-variant-numeric:tabular-nums}
.stat .l{font-size:13px;color:var(--muted)}
.kpi .v{font-size:24px;font-weight:600;margin:6px 0 8px;font-variant-numeric:tabular-nums}
.kpi .s{font-size:12.5px;color:var(--muted);display:flex;flex-direction:column;gap:2px}
.neg{color:var(--red);font-weight:600}.pos{color:var(--green);font-weight:600}.neu{color:var(--muted);font-weight:600}
table.dt{width:100%;border-collapse:collapse;border:none!important;margin:0!important;font-size:13.5px;font-variant-numeric:tabular-nums}
table.dt th,table.dt td{border:none!important;border-bottom:1px solid var(--line)!important}
table.dt tr{border:none!important;background:transparent}
table.dt th{white-space:nowrap;font-size:11px;font-weight:600;letter-spacing:.06em;text-transform:uppercase;color:var(--muted);text-align:left;padding:10px 14px;border-bottom:1px solid var(--line);background:#F9FAFB}
table.dt td{padding:12px 14px;border-bottom:1px solid var(--line);vertical-align:middle}
table.dt tr:last-child td{border-bottom:none!important}
table.dt td.r,table.dt th.r{text-align:right}
table.dt .name{font-weight:600}table.dt .sub{color:var(--muted);font-size:12px;white-space:nowrap}
.tablewrap{background:var(--surface);border:1px solid var(--line);border-radius:10px;overflow:hidden}
.badge{display:inline-block;font-size:11.5px;font-weight:600;padding:3px 10px;border-radius:999px;white-space:nowrap;letter-spacing:.02em}
.b-red{background:var(--red-bg);color:var(--red)}.b-amber{background:var(--amber-bg);color:var(--amber)}.b-green{background:var(--green-bg);color:var(--green)}
.dealhead{display:flex;justify-content:space-between;align-items:flex-start;gap:16px}
.dealhead .dh{font-size:22px;font-weight:600;margin:0 0 4px}
.dealhead .meta{color:var(--muted);font-size:13.5px}
.flag{display:grid;grid-template-columns:120px 1fr;gap:14px;padding:13px 0;border-bottom:1px solid var(--line);font-size:14px;align-items:center}
.flag:last-child{border-bottom:none}
.note code{color:var(--muted);background:#EEF0F3;font-size:11.5px;padding:1px 6px;border-radius:4px}
.note{color:var(--muted);font-size:12px;margin-top:28px;border-top:1px solid var(--line);padding-top:14px}
.qa{border-left:3px solid var(--navy);padding:2px 0 2px 14px;margin:14px 0}
.qa .q{font-weight:600;font-size:14px;margin-bottom:6px}
div[data-testid="stTabs"] button p{font-size:14px;font-weight:500}
div[data-testid="stSelectbox"] label p,div[data-testid="stTextInput"] label p{font-size:12px;font-weight:600;color:var(--muted);text-transform:uppercase;letter-spacing:.06em}
.stButton button,.stFormSubmitButton button{background:var(--navy)!important;color:#fff!important;border:none!important;border-radius:8px;padding:8px 22px;font-weight:500}
.stButton button:hover,.stFormSubmitButton button:hover{background:#163B66!important}
[data-testid="stVerticalBlockBorderWrapper"]{background:var(--surface);border-color:var(--line)!important;border-radius:10px}
.st-key-memo{padding:8px 12px}
.st-key-memo h1,.st-key-memo h2,.st-key-memo h3,.st-key-memo h4{font-size:15px!important;font-weight:600!important;margin:20px 0 8px!important;padding:0!important}
.st-key-memo p,.st-key-memo li{font-size:14px;line-height:1.6}
.st-key-memo hr{margin:14px 0;border-color:var(--line)}
.st-key-memo table{font-size:13px;border-collapse:collapse;width:100%;max-width:820px}
.st-key-memo th{background:#F9FAFB;font-weight:600;color:var(--muted)}
.st-key-memo th,.st-key-memo td{border:1px solid var(--line)!important;padding:7px 12px!important}
[data-testid='stHeaderActionElements']{display:none}
[class*='st-key-qa_'] p,[class*='st-key-qa_'] li{font-size:14px;line-height:1.6}
[class*='st-key-qa_'] h1,[class*='st-key-qa_'] h2,[class*='st-key-qa_'] h3{font-size:15px!important;font-weight:600!important}
</style>
""", unsafe_allow_html=True)


# --------------------------------------------------------------------------- data
@st.cache_data(ttl=300)
def load(table: str) -> pd.DataFrame:
    if SNAPSHOT:
        return pd.read_parquet(os.path.join(SNAPSHOT, f"{table}.parquet"))
    from databricks import sql
    from databricks.sdk.core import Config
    cfg = Config()
    with sql.connect(server_hostname=cfg.host,
                     http_path=f"/sql/1.0/warehouses/{os.getenv('DATABRICKS_WAREHOUSE_ID')}",
                     credentials_provider=lambda: cfg.authenticate) as conn, conn.cursor() as cur:
        cur.execute(f"SELECT * FROM {FQ}.{table}")
        return cur.fetchall_arrow().to_pandas()


def ask_llm(system: str, question: str) -> str:
    from databricks.sdk import WorkspaceClient
    from databricks.sdk.service.serving import ChatMessage, ChatMessageRole
    resp = WorkspaceClient().serving_endpoints.query(name=LLM, messages=[
        ChatMessage(role=ChatMessageRole.SYSTEM, content=system),
        ChatMessage(role=ChatMessageRole.USER, content=question)])
    return resp.choices[0].message.content


scores = load("deal_scorecard").sort_values("deal_id").reset_index(drop=True)
flags = load("deal_red_flags")
memos = load("ic_memos")

# --------------------------------------------------------------------------- helpers
esc = html.escape
pct = lambda x, d=1: "n/a" if pd.isna(x) else f"{x * 100:.{d}f}%"
usd = lambda x: "n/a" if pd.isna(x) else (f"${x / 1e6:,.2f}M" if abs(x) >= 1e5 else f"${x:,.0f}")
VERDICT = {"PROCEED": ("Proceed", "b-green"), "PROCEED WITH CAUTION": ("Proceed with caution", "b-amber"),
           "PASS / RE-PRICE": ("Pass / re-price", "b-red")}
SEV = {"HIGH": ("High", "b-red"), "MEDIUM": ("Medium", "b-amber"), "OPPORTUNITY": ("Opportunity", "b-green")}


def badge(text, cls):
    return f'<span class="badge {cls}">{esc(text)}</span>'


def verdict(rec):
    label, cls = VERDICT.get(rec, (rec, "b-amber"))
    return badge(label, cls)


def variance(actual, claim, kind="pct"):
    """Verified vs. seller claim. Lower than claimed is adverse for every metric shown."""
    if pd.isna(claim) or pd.isna(actual) or not claim:
        return '<span class="neu">no seller figure</span>'
    if kind == "pp":
        d = (actual - claim) * 100
        txt = f"{d:+.1f} pp"
        bad = d < -1
    else:
        d = actual / claim - 1
        txt = f"{d * 100:+.0f}%"
        bad = d < -0.03
    return f'<span class="{"neg" if bad else "neu"}">{txt} vs. seller</span>'


def html_block(s: str):
    st.markdown(s, unsafe_allow_html=True)


# --------------------------------------------------------------------------- header
run_at = pd.to_datetime(memos["generated_at"]).max() if "generated_at" in memos else None
html_block('<div class="topbar"><div class="brand">CRE Deal Screening<span>Acquisitions</span></div>'
           f'<div class="env">INVESTMENT COMMITTEE PRE-SCREEN · {esc(FQ)}</div></div>')
html_block('<div class="page">Deal pipeline</div>'
           '<div class="lead">Seller claims from each Offering Memorandum, verified against the rent roll and T-12'
           + (f' · last run {run_at:%b %d, %Y %H:%M} UTC' if run_at is not None and not pd.isna(run_at) else '') + '</div>')

n_proceed = int((scores.recommendation == "PROCEED").sum())
n_high = int((flags.severity == "HIGH").sum())
html_block('<div class="grid g4">'
           f'<div class="card stat"><div class="l">Deals screened</div><div class="v">{len(scores)}</div></div>'
           f'<div class="card stat"><div class="l">Total asking price</div><div class="v">{usd(scores.asking_price.sum())}</div></div>'
           f'<div class="card stat"><div class="l">Cleared to proceed</div><div class="v">{n_proceed} of {len(scores)}</div></div>'
           f'<div class="card stat"><div class="l">High-severity flags</div><div class="v">{n_high}</div></div></div>')

# --------------------------------------------------------------------------- pipeline table
rows = "".join(
    f'<tr><td><div class="name">{esc(r.property_name)}</div><div class="sub">{esc(r.deal_id)} · {esc(r.location)} · {int(r.units)} units</div></td>'
    f'<td class="r">{usd(r.asking_price)}</td>'
    f'<td class="r">{pct(r.om_occupancy)}</td><td class="r"><b>{pct(r.physical_occupancy)}</b></td>'
    f'<td class="r">{usd(r.om_noi)}</td><td class="r"><b>{usd(r.t12_noi)}</b></td>'
    f'<td class="r"><b>{r.dscr:.2f}x</b></td><td>{verdict(r.recommendation)}</td></tr>'
    for r in scores.itertuples())
html_block('<div class="eyebrow" style="margin-top:26px">Pipeline</div><div class="tablewrap"><table class="dt">'
           '<tr><th>Property</th><th class="r">Asking</th><th class="r">Occ. seller</th><th class="r">Occ. verified</th>'
           '<th class="r">NOI seller</th><th class="r">NOI T-12</th><th class="r">DSCR</th><th>Recommendation</th></tr>'
           f'{rows}</table></div>')

# --------------------------------------------------------------------------- deal detail
html_block('<div class="eyebrow" style="margin-top:30px">Deal review</div>')
c1, _ = st.columns([1, 2])
with c1:
    deal = st.selectbox("Deal", scores.deal_id,
                        format_func=lambda d: f"{d} · {scores.set_index('deal_id').loc[d, 'property_name']}")
s = scores.set_index("deal_id").loc[deal]
# Max price that reaches a target DSCR, keeping the proposed LTV and loan terms (computed here, not by the LLM):
# DSCR = NOI / (price * LTV * debt_constant)  ->  price = NOI / (DSCR * LTV * debt_constant)
ltv = s.loan_amount / s.asking_price
const = s.annual_debt_service / s.loan_amount
price_at = {t: s.t12_noi / (t * ltv * const) for t in (1.25, 1.30, 1.35)}
deal_flags = flags[flags.deal_id == deal]

html_block('<div class="card" style="margin-top:6px"><div class="dealhead"><div>'
           f'<div class="dh">{esc(s.property_name)}</div><div class="meta">{esc(s.location)} · {int(s.units)} units · '
           f'Asking {usd(s.asking_price)} · {usd(s.price_per_unit)} per unit · Proposed loan {usd(s.loan_amount)}</div></div>'
           f'<div>{verdict(s.recommendation)}</div></div></div>')

dscr_cls = "neg" if s.dscr < 1.25 else ("neu" if s.dscr < 1.35 else "pos")
html_block('<div class="grid g5" style="margin-top:14px">'
           f'<div class="card kpi"><div class="eyebrow" style="margin:0">Occupancy</div><div class="v">{pct(s.physical_occupancy)}</div>'
           f'<div class="s"><span>Seller {pct(s.om_occupancy)}</span>{variance(s.physical_occupancy, s.om_occupancy, "pp")}</div></div>'
           f'<div class="card kpi"><div class="eyebrow" style="margin:0">T-12 NOI</div><div class="v">{usd(s.t12_noi)}</div>'
           f'<div class="s"><span>Seller {usd(s.om_noi)}</span>{variance(s.t12_noi, s.om_noi)}</div></div>'
           f'<div class="card kpi"><div class="eyebrow" style="margin:0">Cap rate</div><div class="v">{pct(s.cap_rate_actual, 2)}</div>'
           f'<div class="s"><span>Seller {pct(s.om_cap_rate, 2)}</span>{variance(s.cap_rate_actual, s.om_cap_rate, "pp")}</div></div>'
           f'<div class="card kpi"><div class="eyebrow" style="margin:0">DSCR</div><div class="v">{s.dscr:.2f}x</div>'
           f'<div class="s"><span>Lender minimum 1.25x</span><span class="{dscr_cls}">{"below" if s.dscr < 1.25 else "thin" if s.dscr < 1.35 else "meets"}</span></div></div>'
           f'<div class="card kpi"><div class="eyebrow" style="margin:0">Delinquency</div><div class="v">{pct(s.delinquency_pct)}</div>'
           f'<div class="s"><span>of monthly rent</span><span class="neu">{int(s.delinquent_units)} units</span></div></div></div>')

st.write("")
t_flags, t_uw, t_memo, t_ask = st.tabs(["Risk flags", "Underwriting", "IC memo", "Ask the analyst"])

with t_flags:
    order = {"HIGH": 0, "MEDIUM": 1, "OPPORTUNITY": 2}
    items = "".join(f'<div class="flag"><div>{badge(*SEV.get(f.severity, (f.severity, "b-amber")))}</div><div>{esc(f.message)}</div></div>'
                    for f in deal_flags.assign(o=deal_flags.severity.map(order)).sort_values("o").itertuples())
    html_block(f'<div class="card">{items or "<p>No flags raised for this deal.</p>"}</div>')

with t_uw:
    def table(title, rows_):
        body = "".join(f'<tr><td>{esc(a)}</td>' + "".join(f'<td class="r">{b}</td>' for b in rest) + '</tr>' for a, *rest in rows_)
        return f'<div class="eyebrow">{title}</div><div class="tablewrap" style="margin-bottom:18px"><table class="dt">{body}</table></div>'
    claims = [("", "<b>Seller</b>", "<b>Verified</b>", "<b>Variance</b>"),
              ("Physical occupancy", pct(s.om_occupancy), pct(s.physical_occupancy), variance(s.physical_occupancy, s.om_occupancy, "pp")),
              ("Net operating income", usd(s.om_noi), usd(s.t12_noi), variance(s.t12_noi, s.om_noi)),
              ("Cap rate at asking price", pct(s.om_cap_rate, 2), pct(s.cap_rate_actual, 2), variance(s.cap_rate_actual, s.om_cap_rate, "pp"))]
    ops = [("Effective gross income (T-12)", usd(s.t12_egi)), ("Operating expenses (T-12)", usd(s.t12_opex)),
           ("Expense ratio", pct(s.expense_ratio)), ("NOI, last 3 months annualized", usd(s.t3_annualized_noi)),
           ("Economic occupancy", pct(s.economic_occupancy)), ("Average rent: market / in-place", f"{usd(s.avg_market_rent)} / {usd(s.avg_in_place_rent)}"),
           ("Loss to lease", pct(s.loss_to_lease_pct)), ("Leases expiring in 90 days", pct(s.rollover_90d_pct))]
    debt = [("Loan amount", usd(s.loan_amount)), ("Annual debt service", usd(s.annual_debt_service)),
            ("DSCR on T-12 NOI", f"{s.dscr:.2f}x"), ("DSCR on last-3-months NOI", f"{s.dscr_t3:.2f}x")]
    sens = [(f"Max price for {t:.2f}x DSCR", f"{usd(v)} ({v / s.asking_price - 1:+.0%})") for t, v in price_at.items()]
    a, b = st.columns([3, 2])
    with a:
        html_block(table("Seller claims vs. verified", claims) + table("Operations", ops))
    with b:
        html_block(table("Debt", debt) + table("Price sensitivity · same LTV and loan terms", sens) + '<div class="note" style="margin-top:4px">All figures are computed by deterministic, '
                   'unit-tested underwriting code from the rent roll and T-12. The language model does not calculate any metric.</div>')

with t_memo:
    m = memos[memos.deal_id == deal]
    with st.container(border=True, key="memo"):
        if len(m):
            st.markdown(m.memo_md.iloc[0].replace("$", "\\$"))
        else:
            st.markdown("No memo has been generated for this deal yet.")
    html_block('<div class="note">Drafted by a language model from the verified figures above. Review before circulating to the committee.</div>')

with t_ask:
    hist = st.session_state.setdefault("qa", {}).setdefault(deal, [])
    with st.form(f"ask_{deal}", clear_on_submit=True, border=False):
        q = st.text_input("Question", placeholder="What purchase price would bring DSCR to 1.30x?")
        sent = st.form_submit_button("Ask")
    if sent and q.strip():
        ctx = json.dumps({"scorecard": s.to_dict(), "red_flags": deal_flags.to_dict("records"),
                          "computed": {"ltv": round(ltv, 4), "debt_constant": round(const, 4),
                                       "max_price_for_dscr": {f"{t:.2f}x": round(v) for t, v in price_at.items()}}}, default=str)
        with st.spinner("Analyzing"):
            try:
                ans = ask_llm("You are a commercial real estate underwriting analyst. Answer using only this deal's data, "
                              "show your math briefly in plain text (no LaTeX), keep it under 180 words, and say when the data does not support an answer. "
                              "Percentages are fractions. Values under \"computed\" were calculated by the underwriting code: "
                              "quote them as given, do not recompute them and do not add new arithmetic; explain the drivers in words.\n" + ctx, q.strip())
            except Exception as e:  # surface a clean message instead of a stack trace
                ans = f"The model endpoint is not available ({type(e).__name__})."
        hist.insert(0, (q.strip(), ans))
    for i, (question, answer) in enumerate(hist):
        with st.container(border=True, key=f"qa_{deal}_{i}"):
            html_block(f'<div class="qa"><div class="q">{esc(question)}</div></div>')
            st.markdown(answer.replace("$", "\\$"))

html_block('<div class="note">Synthetic deals for demonstration. Data: Unity Catalog '
           f'<code>{esc(FQ)}</code> · Model: <code>{esc(LLM)}</code></div>')
