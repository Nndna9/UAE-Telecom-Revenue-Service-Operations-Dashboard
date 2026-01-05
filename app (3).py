
import streamlit as st
import pandas as pd
import numpy as np

st.set_page_config(page_title="UAE Telecom Operations Dashboard", layout="wide")

# ---------------- Load Data ----------------
@st.cache_data
def load_data():
    subscribers = pd.read_csv("subscribers.csv", parse_dates=["activation_date"])
    billing = pd.read_csv("billing.csv", parse_dates=["billing_month","payment_date"])
    tickets = pd.read_csv("tickets.csv", parse_dates=["ticket_date","resolution_date"])
    outages = pd.read_csv("network_outages.csv", parse_dates=["outage_date","outage_start_time","outage_end_time"])
    return subscribers, billing, tickets, outages

subscribers, billing, tickets, outages = load_data()

# ---------------- Sidebar (Global Filters) ----------------
st.sidebar.title("Global Filters")

date_range = st.sidebar.date_input(
    "Select Date Range",
    [billing["billing_month"].min(), billing["billing_month"].max()]
)

city_filter = st.sidebar.multiselect(
    "City",
    options=subscribers["city"].unique(),
    default=subscribers["city"].unique()
)

plan_filter = st.sidebar.multiselect(
    "Plan Type",
    options=subscribers["plan_type"].unique(),
    default=subscribers["plan_type"].unique()
)

status_filter = st.sidebar.multiselect(
    "Subscriber Status",
    options=subscribers["status"].unique(),
    default=subscribers["status"].unique()
)

view = st.sidebar.radio("Select View", ["COO View", "Manager View"])

# ---------------- Apply Global Filters ----------------
subs_f = subscribers[
    (subscribers["city"].isin(city_filter)) &
    (subscribers["plan_type"].isin(plan_filter)) &
    (subscribers["status"].isin(status_filter))
]

billing_f = billing[
    (billing["billing_month"] >= pd.to_datetime(date_range[0])) &
    (billing["billing_month"] <= pd.to_datetime(date_range[1])) &
    (billing["subscriber_id"].isin(subs_f["subscriber_id"]))
]

tickets_f = tickets[tickets["subscriber_id"].isin(subs_f["subscriber_id"])]

# ---------------- COO VIEW ----------------
if view == "COO View":
    st.title("COO Executive Overview")

    total_revenue = billing_f["bill_amount"].sum()
    active_subs = subs_f[subs_f["status"]=="Active"]["subscriber_id"].nunique()
    arpu = total_revenue / active_subs if active_subs > 0 else 0
    overdue_rev = billing_f[billing_f["payment_status"]=="Overdue"]["bill_amount"].sum()

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Revenue (AED)", f"{total_revenue:,.0f}", help="Total billed revenue in selected period")
    col2.metric("ARPU (AED)", f"{arpu:,.2f}", help="Average revenue per active subscriber")
    col3.metric("Active Subscribers", f"{active_subs:,}", help="Subscribers currently active")
    col4.metric("Overdue Revenue (AED)", f"{overdue_rev:,.0f}", help="Revenue at risk due to overdue bills")

    st.subheader("Revenue Trends & Mix")

    colA, colB = st.columns(2)

    with colA:
        arpu_trend = billing_f.groupby("billing_month")["bill_amount"].sum().reset_index()
        arpu_trend["ARPU"] = arpu_trend["bill_amount"] / active_subs
        st.line_chart(arpu_trend.set_index("billing_month")["ARPU"])

    with colB:
        rev_city = billing_f.merge(subscribers, on="subscriber_id")             .groupby("city")["bill_amount"].sum().sort_values(ascending=False)
        st.bar_chart(rev_city)

    st.subheader("Payment Status Distribution")
    pay_dist = billing_f["payment_status"].value_counts()
    st.write("Hover to understand payment risk distribution")
    st.bar_chart(pay_dist)

    st.info(
        f"📊 Insight: ARPU is AED {arpu:,.2f}. Overdue revenue of AED {overdue_rev:,.0f} "
        "indicates potential cash flow risk requiring attention."
    )

# ---------------- MANAGER VIEW ----------------
else:
    st.title("Manager Operations Dashboard")

    ticket_category = st.selectbox(
        "Ticket Category (Local Filter)",
        options=["All"] + list(tickets_f["ticket_category"].unique())
    )

    if ticket_category != "All":
        tickets_f = tickets_f[tickets_f["ticket_category"] == ticket_category]

    total_tickets = len(tickets_f)
    backlog = len(tickets_f[tickets_f["status"].isin(["Open","In Progress","Escalated"])])
    resolved = tickets_f[tickets_f["status"]=="Resolved"].copy()
    resolved["resolution_hours"] = (
        (resolved["resolution_date"] - resolved["ticket_date"]).dt.total_seconds() / 3600
    )

    avg_res_time = resolved["resolution_hours"].mean()
    sla_compliance = (resolved["resolution_hours"] <= resolved["sla_target_hours"]).mean() * 100

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Tickets", total_tickets, help="Tickets raised in selected scope")
    col2.metric("Ticket Backlog", backlog, help="Unresolved tickets")
    col3.metric("Avg Resolution Time (hrs)", f"{avg_res_time:.1f}", help="Average time to resolve tickets")
    col4.metric("SLA Compliance (%)", f"{sla_compliance:.1f}", help="Tickets resolved within SLA")

    st.subheader("Ticket & SLA Analysis")

    colA, colB = st.columns(2)

    with colA:
        daily_tickets = tickets_f.groupby(tickets_f["ticket_date"].dt.date).size()
        st.line_chart(daily_tickets)

    with colB:
        sla_by_channel = resolved.groupby("ticket_channel")["resolution_hours"].mean()
        st.bar_chart(sla_by_channel)

    st.subheader("Outages vs Ticket Volume")

    outage_zone = outages.groupby("zone")["outage_duration_mins"].sum()
    ticket_zone = tickets_f.merge(subscribers, on="subscriber_id")         .groupby("zone").size()

    corr_df = pd.DataFrame({
        "Outage Minutes": outage_zone,
        "Ticket Count": ticket_zone
    }).fillna(0)

    st.scatter_chart(corr_df)

    st.info(
        "⚠️ Insight: Zones with higher outage minutes generally show higher ticket volumes, "
        "indicating network stability directly impacts customer complaints."
    )
