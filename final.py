import streamlit as st
import pandas as pd

st.set_page_config(
    page_title="UAE Telecom Revenue & Service Operations Dashboard",
    layout="wide"
)

# =====================================================
# LOAD DATA (ROBUST)
# =====================================================
@st.cache_data
def load_data():
    subs = pd.read_csv("subscribers.csv", parse_dates=["activation_date"])
    if "churn_date" not in subs.columns:
        subs["churn_date"] = pd.NaT
    else:
        subs["churn_date"] = pd.to_datetime(subs["churn_date"], errors="coerce")

    billing = pd.read_csv("billing.csv", parse_dates=["billing_month"])
    tickets = pd.read_csv("tickets.csv")
    outages = pd.read_csv("network_outages.csv", parse_dates=["outage_date"])

    tickets["ticket_date"] = pd.to_datetime(tickets["ticket_date"], errors="coerce")
    tickets["resolution_date"] = pd.to_datetime(tickets["resolution_date"], errors="coerce")

    return subs, billing, tickets, outages

subs, billing, tickets, outages = load_data()

# =====================================================
# SERVICE PRIORITY TIERS
# =====================================================
today = pd.Timestamp("2026-01-01")
subs["tenure_years"] = (today - subs["activation_date"]).dt.days / 365

def assign_tier(r):
    if (r["plan_type"] == "Postpaid" and r["plan_name"] == "Unlimited") or r["tenure_years"] > 3:
        return "Priority 1 – Critical"
    elif (r["plan_type"] == "Postpaid" and r["plan_name"] == "Premium") or r["tenure_years"] > 1:
        return "Priority 2 – High"
    elif r["plan_type"] == "Postpaid":
        return "Priority 3 – Standard"
    else:
        return "Priority 4 – Basic"

subs["service_tier"] = subs.apply(assign_tier, axis=1)

# =====================================================
# GLOBAL FILTERS
# =====================================================
st.sidebar.title("Global Filters")

date_range = st.sidebar.date_input(
    "Billing Period",
    [billing["billing_month"].min(), billing["billing_month"].max()]
)

city_f = st.sidebar.multiselect("City", subs["city"].unique(), default=subs["city"].unique())
plan_type_f = st.sidebar.multiselect("Plan Type", subs["plan_type"].unique(), default=subs["plan_type"].unique())
status_f = st.sidebar.multiselect("Subscriber Status", subs["status"].unique(), default=subs["status"].unique())

view = st.sidebar.radio(
    "Dashboard View",
    ["Executive (COO)", "Managerial & Operational"]
)

subs_f = subs[
    subs["city"].isin(city_f) &
    subs["plan_type"].isin(plan_type_f) &
    subs["status"].isin(status_f)
]

billing_f = billing[
    (billing["billing_month"] >= pd.to_datetime(date_range[0])) &
    (billing["billing_month"] <= pd.to_datetime(date_range[1])) &
    (billing["subscriber_id"].isin(subs_f["subscriber_id"]))
]

tickets_f = tickets[tickets["subscriber_id"].isin(subs_f["subscriber_id"])]

# =====================================================
# EXECUTIVE (COO) VIEW
# =====================================================
if view == "Executive (COO)":
    st.title("Executive (COO) – Revenue & Subscriber Health")

    total_revenue = billing_f["bill_amount"].sum()
    overdue_revenue = billing_f[billing_f["payment_status"] == "Overdue"]["bill_amount"].sum()
    active_now = subs_f[subs_f["status"] == "Active"]["subscriber_id"].nunique()
    retention = (active_now / subs_f["subscriber_id"].nunique()) * 100 if len(subs_f) else 0

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Revenue (AED)", f"{total_revenue:,.0f}")
    c2.metric("ARPU (AED)", f"{total_revenue/active_now:.2f}" if active_now else "0")
    c3.metric("Retention Ratio (%)", f"{retention:.1f}")
    c4.metric("Overdue Revenue (AED)", f"{overdue_revenue:,.0f}")

    plan_name_f = st.selectbox(
        "Local Filter – Plan Name",
        ["All"] + list(subs_f["plan_name"].unique())
    )

    subs_l = subs_f if plan_name_f == "All" else subs_f[subs_f["plan_name"] == plan_name_f]
    billing_l = billing_f[billing_f["subscriber_id"].isin(subs_l["subscriber_id"])]

    # 1. ARPU TREND
    st.subheader("1️⃣ Monthly ARPU Trend")

    monthly = billing_l.groupby("billing_month")["bill_amount"].sum().reset_index()
    active_counts = []

    for m in monthly["billing_month"]:
        active_m = subs_l[
            (subs_l["activation_date"] <= m) &
            ((subs_l["churn_date"].isna()) | (subs_l["churn_date"] > m))
        ]["subscriber_id"].nunique()
        active_counts.append(active_m if active_m > 0 else 1)

    monthly["ARPU"] = monthly["bill_amount"] / active_counts
    st.line_chart(monthly.set_index("billing_month")["ARPU"])
    st.caption("ARPU varies month-wise due to churn, promotions, and plan mix changes.")

    # 2. Revenue by Plan Type
    st.subheader("2️⃣ Revenue Mix by Plan Type")
    st.bar_chart(
        billing_l.merge(subs_l, on="subscriber_id")
        .groupby("plan_type")["bill_amount"].sum()
    )

    # 3. Revenue by City
    st.subheader("3️⃣ Revenue by City")
    st.bar_chart(
        billing_l.merge(subs_l, on="subscriber_id")
        .groupby("city")["bill_amount"].sum()
        .sort_values(ascending=False)
    )

    # 4. Payment Status Pie
    st.subheader("4️⃣ Payment Status Distribution")
    st.pyplot(
        billing_l["payment_status"]
        .value_counts()
        .plot.pie(autopct="%1.1f%%", ylabel="")
        .figure
    )

    # Service Tiers
    st.subheader("🔐 Subscriber Service Priority Analysis")

    t1, t2, t3 = st.columns(3)

    with t1:
        st.bar_chart(subs_l["service_tier"].value_counts())

    with t2:
        st.bar_chart(
            tickets_f[tickets_f["status"].isin(["Open","In Progress","Escalated"])]
            .merge(subs_l, on="subscriber_id")["service_tier"].value_counts()
        )

    with t3:
        resolved = tickets_f[tickets_f["status"]=="Resolved"].merge(subs_l, on="subscriber_id")
        resolved["res_hours"] = (
            (resolved["resolution_date"] - resolved["ticket_date"])
            .dt.total_seconds()/3600
        )
        st.bar_chart(
            resolved.groupby("service_tier")
            .apply(lambda x: (x["res_hours"] <= x["sla_target_hours"]).mean()*100)
        )

# =====================================================
# MANAGERIAL & OPERATIONAL VIEW
# =====================================================
else:
    st.title("Managerial & Operational Dashboard")

    zone_f = st.multiselect(
        "Local Filter – Zone",
        sorted(subs_f["zone"].unique()),
        default=sorted(subs_f["zone"].unique())
    )

    tickets_m = tickets_f.merge(subs_f, on="subscriber_id")
    tickets_m = tickets_m[tickets_m["zone"].isin(zone_f)]

    resolved = tickets_m[tickets_m["status"]=="Resolved"].copy()
    resolved["res_hours"] = (
        (resolved["resolution_date"] - resolved["ticket_date"])
        .dt.total_seconds()/3600
    )

    m1,m2,m3,m4 = st.columns(4)
    m1.metric("Total Tickets", len(tickets_m))
    m2.metric("Ticket Backlog", len(tickets_m[tickets_m["status"].isin(["Open","In Progress","Escalated"])]))
    m3.metric("Avg Resolution Time (hrs)", f"{resolved['res_hours'].mean():.1f}")
    m4.metric("SLA Compliance (%)", f"{(resolved['res_hours']<=resolved['sla_target_hours']).mean()*100:.1f}")

    st.subheader("1️⃣ Daily Ticket Volume Trend")
    st.line_chart(tickets_m.groupby(tickets_m["ticket_date"].dt.date).size())

    st.subheader("2️⃣ Ticket Backlog by Zone")
    st.bar_chart(
        tickets_m[tickets_m["status"].isin(["Open","In Progress","Escalated"])]
        .groupby("zone").size()
    )

    st.subheader("3️⃣ SLA Performance by Channel")
    st.bar_chart(resolved.groupby("ticket_channel")["res_hours"].mean())

    st.subheader("4️⃣ Outage Minutes vs Ticket Volume")
    st.scatter_chart(pd.DataFrame({
        "Outage Minutes": outages.groupby("zone")["outage_duration_mins"].sum(),
        "Ticket Count": tickets_m.groupby("zone").size()
    }).fillna(0))
