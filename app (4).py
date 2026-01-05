
import streamlit as st
import pandas as pd
import numpy as np

st.set_page_config(
    page_title="UAE Telecom Revenue & Service Operations Dashboard",
    layout="wide"
)

# =====================
# Load & Prepare Data
# =====================
@st.cache_data
def load_data():
    subs = pd.read_csv("subscribers.csv", parse_dates=["activation_date"])
    billing = pd.read_csv("billing.csv", parse_dates=["billing_month"])
    tickets = pd.read_csv("tickets.csv")
    outages = pd.read_csv("network_outages.csv", parse_dates=["outage_date"])

    tickets["ticket_date"] = pd.to_datetime(tickets["ticket_date"], errors="coerce")
    tickets["resolution_date"] = pd.to_datetime(tickets["resolution_date"], errors="coerce")

    return subs, billing, tickets, outages

subs, billing, tickets, outages = load_data()

# =====================
# Global Filters
# =====================
st.sidebar.title("Global Filters")

date_range = st.sidebar.date_input(
    "Billing Period",
    [billing["billing_month"].min(), billing["billing_month"].max()]
)

city_filter = st.sidebar.multiselect(
    "City",
    subs["city"].unique(),
    default=subs["city"].unique()
)

plan_filter = st.sidebar.multiselect(
    "Plan Type",
    subs["plan_type"].unique(),
    default=subs["plan_type"].unique()
)

status_filter = st.sidebar.multiselect(
    "Subscriber Status",
    subs["status"].unique(),
    default=subs["status"].unique()
)

view = st.sidebar.radio("Dashboard View", ["COO View", "Manager View"])

# Apply global filters
subs_f = subs[
    (subs["city"].isin(city_filter)) &
    (subs["plan_type"].isin(plan_filter)) &
    (subs["status"].isin(status_filter))
]

billing_f = billing[
    (billing["billing_month"] >= pd.to_datetime(date_range[0])) &
    (billing["billing_month"] <= pd.to_datetime(date_range[1])) &
    (billing["subscriber_id"].isin(subs_f["subscriber_id"]))
]

tickets_f = tickets[tickets["subscriber_id"].isin(subs_f["subscriber_id"])]

# =====================
# COO VIEW
# =====================
if view == "COO View":
    st.title("COO Executive Dashboard")

    # ---- KPIs ----
    total_revenue = billing_f["bill_amount"].sum()
    overdue_revenue = billing_f[billing_f["payment_status"]=="Overdue"]["bill_amount"].sum()

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Revenue (AED)", f"{total_revenue:,.0f}")
    col2.metric("Overdue Revenue (AED)", f"{overdue_revenue:,.0f}")
    col3.metric("Active Subscribers", subs_f[subs_f["status"]=="Active"]["subscriber_id"].nunique())
    col4.metric("Cities Covered", subs_f["city"].nunique())

    # ---- Chart 1: Monthly ARPU Trend ----
    st.subheader("1️⃣ Monthly ARPU Trend")

    monthly_rev = billing_f.groupby("billing_month")["bill_amount"].sum().reset_index()

    active_counts = []
    for m in monthly_rev["billing_month"]:
        cnt = subs_f[(subs_f["activation_date"] <= m) & (subs_f["status"]=="Active")]["subscriber_id"].nunique()
        active_counts.append(cnt)

    monthly_rev["active_subscribers"] = active_counts
    monthly_rev["ARPU"] = monthly_rev["bill_amount"] / monthly_rev["active_subscribers"]

    st.line_chart(monthly_rev.set_index("billing_month")["ARPU"])

    st.caption("📉 Insight: ARPU fluctuates month-to-month based on revenue performance and changes in active subscriber base.")

    # ---- Chart 2: Revenue by Plan Type ----
    st.subheader("2️⃣ Revenue Mix by Plan Type")

    plan_local = st.selectbox("Select Plan Name (Local Filter)", ["All"] + list(subs_f["plan_name"].unique()))

    temp_subs = subs_f if plan_local=="All" else subs_f[subs_f["plan_name"]==plan_local]

    rev_plan = billing_f[billing_f["subscriber_id"].isin(temp_subs["subscriber_id"])]         .merge(temp_subs, on="subscriber_id")         .groupby(["billing_month","plan_type"])["bill_amount"].sum().unstack().fillna(0)

    st.bar_chart(rev_plan)

    st.caption("💡 Insight: Postpaid plans generally contribute a higher and more stable share of revenue.")

    # ---- Chart 3: Revenue by City ----
    st.subheader("3️⃣ Revenue Contribution by City")

    rev_city = billing_f.merge(subs_f, on="subscriber_id")         .groupby("city")["bill_amount"].sum().sort_values(ascending=False)

    st.bar_chart(rev_city)

    st.caption("🏙️ Insight: A small number of cities contribute a majority of total telecom revenue.")

    # ---- Chart 4: Payment Status Distribution ----
    st.subheader("4️⃣ Payment Status Distribution")

    pay_dist = billing_f["payment_status"].value_counts()
    st.bar_chart(pay_dist)

    st.caption("⚠️ Insight: Overdue and partial payments indicate potential cash-flow risk.")

# =====================
# MANAGER VIEW
# =====================
else:
    st.title("Manager Operations Dashboard")

    # ---- Local Filters ----
    ticket_cat = st.selectbox(
        "Ticket Category (Local Filter)",
        ["All"] + list(tickets_f["ticket_category"].dropna().unique())
    )

    if ticket_cat != "All":
        tickets_f = tickets_f[tickets_f["ticket_category"]==ticket_cat]

    # ---- KPIs ----
    backlog = tickets_f[tickets_f["status"].isin(["Open","In Progress","Escalated"])]
    resolved = tickets_f[
        (tickets_f["status"]=="Resolved") &
        (tickets_f["resolution_date"].notna())
    ].copy()

    resolved["resolution_hours"] = (
        (resolved["resolution_date"] - resolved["ticket_date"]).dt.total_seconds()/3600
    )

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Tickets", len(tickets_f))
    col2.metric("Ticket Backlog", len(backlog))
    col3.metric("Avg Resolution Time (hrs)", f"{resolved['resolution_hours'].mean():.1f}")
    col4.metric("SLA Compliance (%)", f"{(resolved['resolution_hours']<=resolved['sla_target_hours']).mean()*100:.1f}")

    # ---- Chart 1: Daily Ticket Trend ----
    st.subheader("1️⃣ Daily Ticket Volume")

    daily_tickets = tickets_f.groupby(tickets_f["ticket_date"].dt.date).size()
    st.line_chart(daily_tickets)

    st.caption("📈 Insight: Sudden spikes often correspond to outages or service disruptions.")

    # ---- Chart 2: Ticket Backlog by Zone ----
    st.subheader("2️⃣ Ticket Backlog by Zone")

    backlog_zone = backlog.merge(subs_f, on="subscriber_id").groupby("zone").size().sort_values(ascending=False)
    st.bar_chart(backlog_zone)

    st.caption("🛠️ Insight: Zones with high backlog require immediate operational attention.")

    # ---- Chart 3: SLA Compliance by Channel ----
    st.subheader("3️⃣ SLA Performance by Support Channel")

    sla_channel = resolved.groupby("ticket_channel")["resolution_hours"].mean()
    st.bar_chart(sla_channel)

    st.caption("☎️ Insight: Certain channels consistently resolve tickets faster than others.")

    # ---- Chart 4: Outages vs Ticket Volume ----
    st.subheader("4️⃣ Outages vs Ticket Volume (Zone-wise)")

    outage_zone = outages.groupby("zone")["outage_duration_mins"].sum()
    ticket_zone = tickets_f.merge(subs_f, on="subscriber_id").groupby("zone").size()

    corr_df = pd.DataFrame({
        "Outage Minutes": outage_zone,
        "Ticket Count": ticket_zone
    }).fillna(0)

    st.scatter_chart(corr_df)

    st.caption("🚨 Insight: Strong correlation suggests network instability directly drives customer complaints.")
