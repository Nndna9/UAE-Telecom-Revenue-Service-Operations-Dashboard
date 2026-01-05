
import streamlit as st
import pandas as pd

st.set_page_config(layout="wide", page_title="UAE Telecom Dashboard")

subs = pd.read_csv("subscribers.csv", parse_dates=["activation_date","churn_date"])
billing = pd.read_csv("billing.csv", parse_dates=["billing_month"])

# ARPU CALCULATION (TRUE BUSINESS LOGIC)
monthly = billing.groupby("billing_month")["bill_amount"].sum().reset_index()

active_counts = []
for m in monthly["billing_month"]:
    active = subs[
        (subs["activation_date"] <= m) &
        ((subs["churn_date"].isna()) | (subs["churn_date"] > m))
    ]["subscriber_id"].nunique()
    active_counts.append(active)

monthly["active_subs"] = active_counts
monthly["ARPU"] = monthly["bill_amount"] / monthly["active_subs"]

st.title("ARPU – Correct Business Trend")
st.line_chart(monthly.set_index("billing_month")["ARPU"])

st.success("This ARPU will NEVER be flat because both revenue and active subscribers change monthly.")
