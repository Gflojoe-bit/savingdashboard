"""Hardcoded placeholder data for the UI scaffold.

These dicts fill the templates while the real subsystems (accounts,
transactions, goals) are still being built. Each subsystem branch will
replace its slice of this with real querysets.
"""

# Keyed by account id.
TRANSACTIONS_BY_ACCOUNT = {
    1: [
        {"name": "Grocery store", "date": "Apr 19, 2026", "amount": "−$84.00",   "credit": False},
        {"name": "Paycheck",      "date": "Apr 15, 2026", "amount": "+$2,400.00", "credit": True},
        {"name": "Rent",          "date": "Apr 1, 2026",  "amount": "−$1,200.00", "credit": False},
        {"name": "Grocery store", "date": "Mar 28, 2026", "amount": "−$61.00",   "credit": False},
        {"name": "Paycheck",      "date": "Mar 15, 2026", "amount": "+$2,400.00", "credit": True},
        {"name": "Rent",          "date": "Mar 1, 2026",  "amount": "−$1,200.00", "credit": False},
    ],
    2: [
        {"name": "Transfer from Checking", "date": "Mar 15, 2026", "amount": "+$500.00", "credit": True},
    ],
}

# Flat list of all transactions, already grouped by month for the main list view.
TRANSACTIONS_BY_MONTH = [
    {
        "label": "April 2026",
        "transactions": [
            {"name": "Grocery store", "date": "Apr 19", "account": "Checking (Bank A)", "amount": "−$84.00",    "credit": False},
            {"name": "Paycheck",      "date": "Apr 15", "account": "Checking (Bank A)", "amount": "+$2,400.00", "credit": True},
            {"name": "Rent",          "date": "Apr 1",  "account": "Checking (Bank A)", "amount": "−$1,200.00", "credit": False},
        ],
    },
    {
        "label": "March 2026",
        "transactions": [
            {"name": "Grocery store",      "date": "Mar 28", "account": "Checking (Bank A)", "amount": "−$61.00",    "credit": False},
            {"name": "Paycheck",           "date": "Mar 15", "account": "Checking (Bank A)", "amount": "+$2,400.00", "credit": True},
            {"name": "Transfer to Savings","date": "Mar 15", "account": "Savings (Bank B)",  "amount": "+$500.00",   "credit": True},
            {"name": "Rent",               "date": "Mar 1",  "account": "Checking (Bank A)", "amount": "−$1,200.00", "credit": False},
        ],
    },
]

# The 3 most recent across all accounts — shown on the home dashboard.
RECENT_TRANSACTIONS = TRANSACTIONS_BY_MONTH[0]["transactions"]

GOALS = [
    {
        "id": 1,
        "name": "Emergency Fund",
        "saved": 3200,
        "target": 5000,
        "pct": 64,
        "remaining": "1,800",
        "due": "Dec 31, 2026",
    },
    {
        "id": 2,
        "name": "Vacation",
        "saved": 900,
        "target": 2000,
        "pct": 45,
        "remaining": "1,100",
        "due": "Aug 1, 2026",
    },
]

TOTAL_SAVINGS = "12,400"

# Monthly summary numbers for the 3 home-page cards.
MONTH_SUMMARY = {
    "label": "April 2026",
    "income":   "2,400",
    "spending": "1,284",
    "savings":  "1,116",  # income − spending
}

# Savings progress against a goal — three time periods, toggleable on the home
# page like a brokerage chart's 1W / 1M / 1Y. Displayed as progress-in-a-tile.
SAVINGS_GOAL_PERIODS = [
    {
        "key": "week",
        "label": "Week",
        "saved":  250,
        "target": 400,
        "saved_display":  "250",
        "target_display": "400",
        "pct": 63,
    },
    {
        "key": "month",
        "label": "Month",
        "saved":  1116,
        "target": 1500,
        "saved_display":  "1,116",
        "target_display": "1,500",
        "pct": 74,
    },
    {
        "key": "year",
        "label": "Year",
        "saved":  12400,
        "target": 20000,
        "saved_display":  "12,400",
        "target_display": "20,000",
        "pct": 62,
    },
]
