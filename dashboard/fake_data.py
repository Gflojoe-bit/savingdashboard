"""Hardcoded placeholder data for the UI scaffold.

These dicts fill the templates while the real subsystems (accounts,
transactions, goals) are still being built. Each subsystem branch will
replace its slice of this with real querysets.
"""

ACCOUNTS = [
    {"id": 1, "name": "Checking (Bank A)", "type": "Checking", "balance": "3,200.00"},
    {"id": 2, "name": "Savings (Bank B)", "type": "Savings",  "balance": "9,200.00"},
]

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
