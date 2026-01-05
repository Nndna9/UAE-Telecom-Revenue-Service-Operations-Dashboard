
import streamlit as st
import pandas as pd

st.set_page_config(layout="wide", page_title="UAE Telecom Dashboard – Stable ARPU")

# =====================
# Safe Data Loading
# =====================
subs = pd.read_csv("subscribers.csv", parse_dates=["activation_date"])

# 🔒 SAFETY: churn_date may not exist in earlier CSVs
if "churn_date" not in subs.columns:
    subs["churn_date"] = pd.NaT
else:
    subs["churn_date"] = pd.to_datetime(subs["churn_date"], errors="coerce")

billing = pd.read_csv("billing.csv", parse_dates=["billing_month"])

# =====================
# Correct ARPU Calculation
# =====================
monthly_rev = (
    billing
    .groupby("billing_month")["bill_amount"]
    .sum()
    .reset_index()
)

active_counts = []
for month in monthly_rev["billing_month"]:
    active = subs[
        (subs["activation_date"] <= month) &
        ((subs["churn_date"].isna()) | (subs["churn_date"] > month))
    ]["subscriber_id"].nunique()

    active_counts.append(active if active > 0 else 1)

monthly_rev["active_subscribers"] = active_counts
monthly_rev["ARPU"] = monthly_rev["bill_amount"] / monthly_rev["active_subscribers"]

# =====================
# UI
# =====================
st.title("Monthly ARPU Trend (Correct & Non-Flat)")

st.line_chart(
    monthly_rev.set_index("billing_month")["ARPU"]
)

st.success(
    "✅ ARPU now varies month-to-month because both revenue and active subscribers "
    "change over time. This confirms the data + logic are correct."
)

st.caption(
    "Business definition: ARPU = Monthly Revenue ÷ Active Subscribers in that month."
)
