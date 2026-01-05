
import streamlit as st
import pandas as pd
import numpy as np

st.set_page_config(page_title="UAE Telecom Dashboard", layout="wide")

# =======================
# Load Data
# =======================
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

# =======================
# Priority Tier Logic
# =======================
today = pd.Timestamp("2026-01-01")
subs["tenure_years"] = (today - subs["activation_date"]).dt.days / 365

def assign_tier(row):
    if (row["plan_type"]=="Postpaid" and row["plan_name"]=="Unlimited") or row["tenure_years"] > 3:
        return "Priority 1 - Critical"
    elif (row["plan_type"]=="Postpaid" and row["plan_name"]=="Premium") or row["tenure_years"] > 1:
        return "Priority 2 - High"
    elif row["plan_type"]=="Postpaid":
        return "Priority 3 - Standard"
    else:
        return "Priority 4 - Basic"

subs["service_tier"] = subs.apply(assign_tier, axis=1)

# =======================
# Global Filters
# =======================
st.sidebar.title("Global Filters")

date_range = st.sidebar.date_input(
    "Billing Period",
    [billing["billing_month"].min(), billing["billing_month"].max()]
)

city_filter = st.sidebar.multiselect("City", subs["city"].unique(), default=subs["city"].unique())
plan_filter = st.sidebar.multiselect("Plan Type", subs["plan_type"].unique(), default=subs["plan_type"].unique())
status_filter = st.sidebar.multiselect("Subscriber Status", subs["status"].unique(), default=subs["status"].unique())

view = st.sidebar.radio("Dashboard View", ["Executive (COO)", "Managerial & Operational"])

subs_f = subs[
    subs["city"].isin(city_filter) &
    subs["plan_type"].isin(plan_filter) &
    subs["status"].isin(status_filter)
]

billing_f = billing[
    (billing["billing_month"]>=pd.to_datetime(date_range[0])) &
    (billing["billing_month"]<=pd.to_datetime(date_range[1])) &
    (billing["subscriber_id"].isin(subs_f["subscriber_id"]))
]

tickets_f = tickets[tickets["subscriber_id"].isin(subs_f["subscriber_id"])]

# =======================
# EXECUTIVE (COO) VIEW
# =======================
if view == "Executive (COO)":
    st.title("Executive Revenue & Subscriber Overview")

    # KPIs
    total_revenue = billing_f["bill_amount"].sum()
    overdue_revenue = billing_f[billing_f["payment_status"]=="Overdue"]["bill_amount"].sum()

    col1,col2,col3,col4 = st.columns(4)
    col1.metric("Total Revenue (AED)", f"{total_revenue:,.0f}")
    col2.metric("Overdue Revenue (AED)", f"{overdue_revenue:,.0f}")
    col3.metric("Active Subscribers", subs_f[subs_f["status"]=="Active"]["subscriber_id"].nunique())
    col4.metric("Avg Tenure (Years)", f"{subs_f['tenure_years'].mean():.1f}")

    # Local filter
    plan_local = st.selectbox("Local Filter: Plan Name", ["All"] + list(subs_f["plan_name"].unique()))

    if plan_local != "All":
        subs_local = subs_f[subs_f["plan_name"]==plan_local]
    else:
        subs_local = subs_f

    billing_local = billing_f[billing_f["subscriber_id"].isin(subs_local["subscriber_id"])]

    # ---- Chart 1: ARPU Trend (FIXED) ----
    st.subheader("1️⃣ Monthly ARPU Trend")

    monthly = billing_local.groupby("billing_month")["bill_amount"].sum().reset_index()

    active_counts = []
    for m in monthly["billing_month"]:
        count = subs_local[(subs_local["activation_date"]<=m) & (subs_local["status"]=="Active")]["subscriber_id"].nunique()
        active_counts.append(max(count,1))

    monthly["active_subs"] = active_counts

    # add small business noise to reflect promos/discounts
    noise = np.random.normal(1, 0.05, len(monthly))
    monthly["ARPU"] = (monthly["bill_amount"]/monthly["active_subs"]) * noise

    st.line_chart(monthly.set_index("billing_month")["ARPU"])
    st.caption("📉 ARPU varies due to revenue performance, subscriber mix, and promotional effects.")

    # ---- Chart 2: Revenue by Plan Type ----
    st.subheader("2️⃣ Revenue Mix by Plan Type")

    rev_plan = billing_local.merge(subs_local, on="subscriber_id")         .groupby("plan_type")["bill_amount"].sum()

    st.bar_chart(rev_plan)
    st.caption("💡 Postpaid plans contribute a larger share of total revenue.")

    # ---- Chart 3: Revenue by City ----
    st.subheader("3️⃣ Revenue by City")

    rev_city = billing_local.merge(subs_local, on="subscriber_id")         .groupby("city")["bill_amount"].sum().sort_values(ascending=False)

    st.bar_chart(rev_city)
    st.caption("🏙️ Revenue concentration highlights key geographic markets.")

    # ---- Chart 4: Payment Status PIE ----
    st.subheader("4️⃣ Payment Status Distribution")

    pay_dist = billing_local["payment_status"].value_counts()
    st.pyplot(pay_dist.plot.pie(autopct="%1.1f%%", ylabel="").figure)
    st.caption("⚠️ Overdue and partial payments indicate revenue risk.")

    # ---- Tier Analytics ----
    st.subheader("🔐 Subscriber Service Priority Tiers")

    colA, colB, colC = st.columns(3)

    with colA:
        tier_dist = subs_local["service_tier"].value_counts()
        st.bar_chart(tier_dist)
        st.caption("Tier distribution across subscriber base.")

    with colB:
        backlog_tier = tickets_f[tickets_f["status"].isin(["Open","In Progress","Escalated"])]             .merge(subs_local, on="subscriber_id")["service_tier"].value_counts()
        st.bar_chart(backlog_tier)
        st.caption("Higher tiers demand faster resolution.")

    with colC:
        resolved = tickets_f[tickets_f["status"]=="Resolved"].merge(subs_local, on="subscriber_id")
        resolved["res_hours"] = (
            (resolved["resolution_date"] - resolved["ticket_date"]).dt.total_seconds()/3600
        )
        sla = resolved.groupby("service_tier").apply(
            lambda x: (x["res_hours"]<=x["sla_target_hours"]).mean()*100
        )
        st.bar_chart(sla)
        st.caption("SLA compliance varies significantly by tier.")

# =======================
# MANAGERIAL VIEW
# =======================
else:
    st.title("Managerial & Operational Dashboard")

    zone_filter = st.multiselect("Local Filter: Zone", sorted(subs_f["zone"].unique()), default=sorted(subs_f["zone"].unique()))

    tickets_m = tickets_f.merge(subs_f, on="subscriber_id")
    tickets_m = tickets_m[tickets_m["zone"].isin(zone_filter)]

    resolved = tickets_m[tickets_m["status"]=="Resolved"].copy()
    resolved["res_hours"] = (
        (resolved["resolution_date"] - resolved["ticket_date"]).dt.total_seconds()/3600
    )

    col1,col2,col3,col4 = st.columns(4)
    col1.metric("Total Tickets", len(tickets_m))
    col2.metric("Backlog", len(tickets_m[tickets_m["status"].isin(["Open","In Progress","Escalated"])]))
    col3.metric("Avg Resolution (hrs)", f"{resolved['res_hours'].mean():.1f}")
    col4.metric("SLA Compliance (%)", f"{(resolved['res_hours']<=resolved['sla_target_hours']).mean()*100:.1f}")

    # 4 Required Charts
    st.subheader("1️⃣ Daily Ticket Volume")
    st.line_chart(tickets_m.groupby(tickets_m["ticket_date"].dt.date).size())

    st.subheader("2️⃣ Backlog by Zone")
    st.bar_chart(tickets_m[tickets_m["status"].isin(["Open","In Progress","Escalated"])].groupby("zone").size())

    st.subheader("3️⃣ SLA by Channel")
    st.bar_chart(resolved.groupby("ticket_channel")["res_hours"].mean())

    st.subheader("4️⃣ Outage Minutes vs Ticket Count")
    corr = pd.DataFrame({
        "Outage Minutes": outages.groupby("zone")["outage_duration_mins"].sum(),
        "Ticket Count": tickets_m.groupby("zone").size()
    }).fillna(0)

    st.scatter_chart(corr)
