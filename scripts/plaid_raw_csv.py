"""Emit a single CSV that mirrors the raw Plaid /transactions JSON payload
one row per transaction. Use this as the importer's input fixture when
designing 'import a Plaid export' handling.

Top-level scalar fields become columns directly. Nested objects/arrays
(personal_finance_category, location, payment_meta, counterparties) are
serialized as JSON strings in their cells so nothing is lost. The importer
can choose what to flatten / drop / parse.

Output: scripts/plaid_dump/plaid_transactions_raw.csv
"""
import csv
import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DUMP = REPO_ROOT / "scripts" / "plaid_dump" / "05_transactions_get.json"
OUT = REPO_ROOT / "scripts" / "plaid_dump" / "plaid_transactions_raw.csv"

# Full set of fields Plaid returns on a transaction, in a stable order.
COLUMNS = [
    "transaction_id",
    "account_id",
    "account_owner",
    "date",
    "datetime",
    "authorized_date",
    "authorized_datetime",
    "amount",
    "iso_currency_code",
    "unofficial_currency_code",
    "name",
    "merchant_name",
    "merchant_entity_id",
    "logo_url",
    "website",
    "pending",
    "pending_transaction_id",
    "transaction_type",
    "transaction_code",
    "payment_channel",
    "check_number",
    "category",                # legacy, usually null in v2
    "category_id",             # legacy
    "personal_finance_category",
    "personal_finance_category_icon_url",
    "counterparties",
    "location",
    "payment_meta",
]


def cell(v):
    if v is None:
        return ""
    if isinstance(v, (dict, list)):
        return json.dumps(v, separators=(",", ":"))
    return v


def main() -> None:
    txs = json.loads(DUMP.read_text())["transactions"]
    txs.sort(key=lambda t: t["date"], reverse=True)
    with OUT.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=COLUMNS)
        w.writeheader()
        for t in txs:
            w.writerow({k: cell(t.get(k)) for k in COLUMNS})
    print(f"Wrote {len(txs)} rows -> {OUT.relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    main()
