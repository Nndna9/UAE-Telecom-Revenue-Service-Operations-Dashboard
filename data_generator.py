
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

np.random.seed(7)

# ------------------
# CONFIG
# ------------------
START_DATE = pd.to_datetime("2025-09-01")
MONTHS = pd.date_range(START_DATE, periods=4, freq="MS")
N_SUBS = 5000

# ------------------
# SUBSCRIBERS
# ------------------
subs = []
for i in range(N_SUBS):
    activation = START_DATE - timedelta(days=np.random.randint(0, 900))
    churn_prob = np.random.rand()

    status = "Active"
    churn_date = None
    if churn_prob < 0.15:
        churn_date = activation + timedelta(days=np.random.randint(180, 700))
        status = "Churned" if churn_date < MONTHS[-1] else "Active"

    subs.append({
        "subscriber_id": f"SUB_{i:05d}",
        "subscriber_name": f"User_{i}",
        "city": np.random.choice(["Dubai","Abu Dhabi","Sharjah","Ajman","Fujairah"], p=[0.35,0.3,0.2,0.1,0.05]),
        "zone": np.random.randint(1,9),
        "plan_type": np.random.choice(["Prepaid","Postpaid"], p=[0.6,0.4]),
        "plan_name": np.random.choice(["Basic","Standard","Premium","Unlimited"], p=[0.3,0.35,0.25,0.1]),
        "monthly_charge": np.random.choice([80,120,180,250,350]),
        "activation_date": activation,
        "churn_date": churn_date,
        "status": status
    })

subs = pd.DataFrame(subs)
subs.to_csv("subscribers.csv", index=False)

# ------------------
# BILLING (MONTHLY VARIATION)
# ------------------
billing = []
for month in MONTHS:
    promo_factor = np.random.uniform(0.85, 1.15)

    active_subs = subs[
        (subs["activation_date"] <= month) &
        ((subs["churn_date"].isna()) | (subs["churn_date"] > month))
    ]

    for _, s in active_subs.iterrows():
        bill = s["monthly_charge"] * promo_factor * np.random.uniform(0.9,1.1)

        billing.append({
            "bill_id": f"BILL_{np.random.randint(1e6)}",
            "subscriber_id": s["subscriber_id"],
            "billing_month": month,
            "bill_amount": round(bill,2),
            "payment_status": np.random.choice(["Paid","Overdue","Partial","Pending"], p=[0.7,0.15,0.1,0.05]),
            "payment_date": month + timedelta(days=np.random.randint(1,20)),
            "credit_adjustment": np.random.choice([0,0,0,20,50]),
            "adjustment_reason": np.random.choice(["Promo","Billing Error","Service Issue",None], p=[0.2,0.1,0.2,0.5])
        })

billing = pd.DataFrame(billing)
billing.to_csv("billing.csv", index=False)

# ------------------
# TICKETS
# ------------------
tickets = []
for _ in range(6000):
    sid = np.random.choice(subs["subscriber_id"])
    open_date = START_DATE + timedelta(days=np.random.randint(0,120))

    resolved = np.random.rand() < 0.65
    tickets.append({
        "ticket_id": f"TIC_{np.random.randint(1e6)}",
        "subscriber_id": sid,
        "ticket_date": open_date,
        "ticket_channel": np.random.choice(["App","Call Center","Online Chat","Retail Store"]),
        "ticket_category": np.random.choice(["Network Issue","Billing Query","Technical Support","Plan Change","Complaint"]),
        "priority": np.random.choice(["Low","Medium","High","Critical"], p=[0.4,0.35,0.2,0.05]),
        "status": "Resolved" if resolved else np.random.choice(["Open","In Progress","Escalated"]),
        "resolution_date": open_date + timedelta(hours=np.random.randint(6,96)) if resolved else None,
        "sla_target_hours": np.random.choice([24,48,72]),
        "assigned_team": np.random.choice(["Tier 1","Tier 2","Tier 3","Field Ops"])
    })

tickets = pd.DataFrame(tickets)
tickets.to_csv("tickets.csv", index=False)

# ------------------
# OUTAGES
# ------------------
outages = []
for _ in range(200):
    start = START_DATE + timedelta(days=np.random.randint(0,120))
    duration = np.random.randint(30,900)

    outages.append({
        "outage_id": f"OUT_{np.random.randint(1e6)}",
        "zone": np.random.randint(1,9),
        "city": np.random.choice(["Dubai","Abu Dhabi","Sharjah","Ajman","Fujairah"]),
        "outage_date": start.date(),
        "outage_start_time": start,
        "outage_end_time": start + timedelta(minutes=duration),
        "outage_duration_mins": duration,
        "outage_type": np.random.choice(["Planned Maintenance","Equipment Failure","Power Outage","Fiber Cut","Weather"]),
        "affected_subscribers": np.random.randint(100,5000)
    })

pd.DataFrame(outages).to_csv("network_outages.csv", index=False)

# ------------------
# USAGE
# ------------------
usage = []
for _ in range(50000):
    usage.append({
        "usage_id": f"USG_{np.random.randint(1e6)}",
        "subscriber_id": np.random.choice(subs["subscriber_id"]),
        "usage_date": START_DATE + timedelta(days=np.random.randint(0,120)),
        "data_usage_gb": round(np.random.exponential(6),2),
        "voice_minutes": np.random.randint(0,600),
        "sms_count": np.random.randint(0,120),
        "roaming_charges": round(np.random.exponential(12),2),
        "addon_charges": round(np.random.exponential(6),2)
    })

pd.DataFrame(usage).to_csv("usage_records.csv", index=False)
