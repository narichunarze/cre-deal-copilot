"""Databricks App (Streamlit): review deals, red flags and IC memo, and ask questions about a deal."""
import json
import os

import pandas as pd
import streamlit as st
from databricks import sql
from databricks.sdk import WorkspaceClient
from databricks.sdk.core import Config
from databricks.sdk.service.serving import ChatMessage, ChatMessageRole

FQ = os.getenv("DD_SCHEMA", "main.cre_dd")
LLM = os.getenv("LLM_ENDPOINT", "databricks-gpt-oss-120b")
cfg = Config()

st.set_page_config(page_title="CRE Deal Copilot", layout="wide")


@st.cache_data(ttl=300)
def q(query: str) -> pd.DataFrame:
    with sql.connect(server_hostname=cfg.host,
                     http_path=f"/sql/1.0/warehouses/{os.getenv('DATABRICKS_WAREHOUSE_ID')}",
                     credentials_provider=lambda: cfg.authenticate) as conn, conn.cursor() as cur:
        cur.execute(query)
        return cur.fetchall_arrow().to_pandas()


scores = q(f"SELECT * FROM {FQ}.deal_scorecard ORDER BY deal_id")
flags = q(f"SELECT * FROM {FQ}.deal_red_flags")
memos = q(f"SELECT deal_id, memo_md FROM {FQ}.ic_memos")

st.title("CRE Deal Due-Diligence Copilot")
st.dataframe(scores[["deal_id", "property_name", "location", "recommendation", "high_flags",
                     "physical_occupancy", "om_occupancy", "t12_noi", "om_noi", "cap_rate_actual", "dscr"]],
             hide_index=True, use_container_width=True)

deal = st.selectbox("Deal", scores["deal_id"], format_func=lambda d: f"{d} · {scores.set_index('deal_id').loc[d, 'property_name']}")
s = scores.set_index("deal_id").loc[deal]

c = st.columns(5)
c[0].metric("Occupancy (actual)", f"{s.physical_occupancy:.1%}", f"{s.physical_occupancy - (s.om_occupancy or 0):+.1%} vs OM")
c[1].metric("T-12 NOI", f"${s.t12_noi:,.0f}", f"{s.t12_noi / s.om_noi - 1:+.0%} vs OM" if s.om_noi else None)
c[2].metric("Cap rate (actual)", f"{s.cap_rate_actual:.2%}")
c[3].metric("DSCR", f"{s.dscr:.2f}x")
c[4].metric("Recommendation", s.recommendation)

left, right = st.columns(2)
with left:
    st.subheader("Red flags")
    color = {"HIGH": "red", "MEDIUM": "orange", "OPPORTUNITY": "green"}
    for _, f in flags[flags.deal_id == deal].iterrows():
        st.markdown(f":{color.get(f.severity, 'gray')}[**{f.severity}**] — {f.message}")
with right:
    st.subheader("IC memo")
    m = memos[memos.deal_id == deal]
    st.markdown(m.memo_md.iloc[0] if len(m) else "_Run notebook 04 to generate the memo._")

st.divider()
st.subheader("Ask about this deal")
if question := st.chat_input("e.g. What price would get DSCR to 1.30x?"):
    context = json.dumps({"scorecard": s.to_dict(), "red_flags": flags[flags.deal_id == deal].to_dict("records")},
                         default=str)
    resp = WorkspaceClient().serving_endpoints.query(name=LLM, messages=[
        ChatMessage(role=ChatMessageRole.SYSTEM, content="You are a CRE underwriting assistant. Answer using only "
                    "this deal data; show your math. Percentages are fractions.\n" + context),
        ChatMessage(role=ChatMessageRole.USER, content=question)])
    st.chat_message("user").write(question)
    st.chat_message("assistant").write(resp.choices[0].message.content)
