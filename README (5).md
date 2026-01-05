
# UAE Telecom Revenue & Service Operations Dashboard

## Overview
This Streamlit dashboard provides strategic and operational visibility into a UAE-based telecom provider.

## Views
### COO View
- Revenue & ARPU trends
- Overdue revenue risk
- City-wise revenue contribution

### Manager View
- Ticket backlog & SLA performance
- Resolution time analysis
- Network outage vs ticket correlation

## Features
- Global & local filters
- Interactive, labeled visualizations
- Tooltips for KPIs
- Realistic business ups & downs in data

## How to Run
```bash
pip install -r requirements.txt
streamlit run app.py
```

## Data Files
Ensure the following CSV files are in the same folder:
- subscribers.csv
- billing.csv
- tickets.csv
- network_outages.csv
- usage_records.csv
