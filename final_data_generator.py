
import pandas as pd
import numpy as np
from datetime import timedelta

np.random.seed(42)

MONTHS = pd.date_range("2025-09-01", periods=4, freq="MS")
N_SUBS = 5000

# SUBSCRIBERS
subs = []
for i in range(N_SUBS):
    activation = pd.Timestamp("2023-01-01") + timedelta(days=np.random.randint(0,900))
    churn = None
    if np.random.rand() < 0.15:
        churn = activation + timedelta(days=np.random.randint(300,900))

    subs.append({
        "subscriber_id": f"SUB_{i:05d}",
        "subscriber_name": f"User_{i}",
        "city": np.random.choice(["Dubai","Abu Dhabi","Sharjah","Ajman","Fujairah"],
                                 p=[0.35,0.3,0.2,0.1,0.05]),
        "zone": np.random.randint(1,9),
        "plan_type": np.random.choice(["Prepaid","Postpaid"], p=[0.6,0.4]),
        "plan_name": np.random.choice(["Basic","Standard","Premium","Unlimited"],
                                      p=[0.3,0.35,0.25,0.1]),
        "monthly_charge": np.random.choice([75,120,180,250,350]),
        "activation_date": activation,
        "churn_date": churn,
        "status": "Active" if churn is None or churn > MONTHS[-1] else "Churned"
    })

subs = pd.DataFrame(subs)
subs.to_csv("subscribers.csv", index=False)

# BILLING (MONTH VARIATION)
billing = []
for m in MONTHS:
    promo = np.random.uniform(0.85,1.2)
    active = subs[(subs["activation_date"]<=m) & ((subs["churn_date"].isna()) | (subs["churn_date"]>m))]

    for _, s in active.iterrows():
        amt = s["monthly_charge"] * promo * np.random.uniform(0.9,1.1)
        billing.append({
            "bill_id": f"BILL_{np.random.randint(1e6)}",
            "subscriber_id": s["subscriber_id"],
            "billing_month": m,
            "bill_amount": round(amt,2),
            "payment_status": np.random.choice(["Paid","Overdue","Partial","Pending"],
                                               p=[0.7,0.15,0.1,0.05])
        })

pd.DataFrame(billing).to_csv("billing.csv", index=False)

# TICKETS
tickets = []
for _ in range(6000):
    open_date = pd.Timestamp("2025-09-01") + timedelta(days=np.random.randint(0,120))
    resolved = np.random.rand()<0.65
    tickets.append({
        "ticket_id": f"TIC_{np.random.randint(1e6)}",
        "subscriber_id": np.random.choice(subs["subscriber_id"]),
        "ticket_date": open_date,
        "ticket_channel": np.random.choice(["App","Call Center","Online Chat","Retail Store"]),
        "ticket_category": np.random.choice(["Network Issue","Billing Query","Technical Support","Plan Change","Complaint"]),
        "priority": np.random.choice(["Low","Medium","High","Critical"]),
        "status": "Resolved" if resolved else np.random.choice(["Open","In Progress","Escalated"]),
        "resolution_date": open_date + timedelta(hours=np.random.randint(6,96)) if resolved else None,
        "sla_target_hours": np.random.choice([24,48,72])
    })

pd.DataFrame(tickets).to_csv("tickets.csv", index=False)

# OUTAGES
outages = []
for _ in range(200):
    start = pd.Timestamp("2025-09-01") + timedelta(days=np.random.randint(0,120))
    outages.append({
        "outage_id": f"OUT_{np.random.randint(1e6)}",
        "zone": np.random.randint(1,9),
        "city": np.random.choice(["Dubai","Abu Dhabi","Sharjah","Ajman","Fujairah"]),
        "outage_date": start.date(),
        "outage_duration_mins": np.random.randint(30,900)
    })

pd.DataFrame(outages).to_csv("network_outages.csv", index=False)
