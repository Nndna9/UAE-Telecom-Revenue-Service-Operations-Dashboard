
import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="UAE Telecom Revenue & Operations Dashboard", layout="wide")

@st.cache_data
def load():
    subs = pd.read_csv("subscribers.csv", parse_dates=["activation_date","churn_date"])
    billing = pd.read_csv("billing.csv", parse_dates=["billing_month"])
    tickets = pd.read_csv("tickets.csv")
    outages = pd.read_csv("network_outages.csv")

    tickets["ticket_date"] = pd.to_datetime(tickets["ticket_date"], errors="coerce")
    tickets["resolution_date"] = pd.to_datetime(tickets["resolution_date"], errors="coerce")
    return subs, billing, tickets, outages

subs, billing, tickets, outages = load()

st.sidebar.title("Filters")
view = st.sidebar.radio("View", ["Executive (COO)", "Managerial & Operational"])

# -------- EXECUTIVE --------
if view == "Executive (COO)":
    st.title("Executive (COO) – Revenue Overview")

    monthly = billing.groupby("billing_month")["bill_amount"].sum().reset_index()
    active = []
    for m in monthly["billing_month"]:
        cnt = subs[(subs["activation_date"]<=m) & ((subs["churn_date"].isna()) | (subs["churn_date"]>m))]
        active.append(len(cnt))

    monthly["ARPU"] = monthly["bill_amount"] / pd.Series(active)

    st.subheader("Monthly ARPU Trend")
    st.line_chart(monthly.set_index("billing_month")["ARPU"])

    st.subheader("Payment Status Distribution")
    fig = px.pie(billing, names="payment_status", title="Payment Status")
    st.plotly_chart(fig, use_container_width=True)

# -------- MANAGER --------
else:
    st.title("Managerial & Operational Dashboard")

    resolved = tickets[tickets["status"]=="Resolved"].copy()
    resolved["res_hours"] = (resolved["resolution_date"] - resolved["ticket_date"]).dt.total_seconds()/3600

    st.subheader("Daily Ticket Volume")
    st.line_chart(tickets.groupby(tickets["ticket_date"].dt.date).size())

    st.subheader("SLA by Channel")
    st.bar_chart(resolved.groupby("ticket_channel")["res_hours"].mean())

    st.subheader("Outages vs Tickets")
    corr = pd.DataFrame({
        "Outage Minutes": outages.groupby("zone")["outage_duration_mins"].sum(),
        "Ticket Count": tickets.groupby("subscriber_id").count()["ticket_id"]
    })
    st.scatter_chart(corr)
