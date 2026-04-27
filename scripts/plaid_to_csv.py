"""Take the Plaid sandbox dump and emit per-account CSVs in a shape close to
what real bank exports look like. Output goes to scripts/plaid_dump/csv/.

Two columns that wouldn't appear in a real bank export are included anyway:
  - plaid_transaction_id (for dedup testing)
  - pending (for testing the pending-row filter, once we have one)

Sign convention in the CSV is Plaid's native: positive = debit/spending,
negative = credit/refund/deposit. The importer will be the place that flips
to our internal positive=income convention; keeping the CSV in source-native
form means the importer has to face the real-world sign question rather than
having it pre-solved.

Run:
  python3 scripts/plaid_to_csv.py [--days 30]
"""
import argparse
import csv
import json
import re
from datetime import date, timedelta
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DUMP_DIR = REPO_ROOT / "scripts" / "plaid_dump"
OUT_DIR = DUMP_DIR / "csv"

COLUMNS = [
    "date",
    "description",
    "amount",
    "merchant",
    "category",
    "pending",
    "plaid_transaction_id",
]


def slug(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", s.lower()).strip("_")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=30,
                    help="window of recent transactions (default 30)")
    ap.add_argument("--all", action="store_true",
                    help="ignore --days and export everything in the dump")
    args = ap.parse_args()

    accts_blob = json.loads((DUMP_DIR / "03_accounts.json").read_text())
    txs_blob = json.loads((DUMP_DIR / "05_transactions_get.json").read_text())
    accounts = {a["account_id"]: a for a in accts_blob["accounts"]}
    txs = txs_blob["transactions"]

    if not args.all:
        cutoff = (date.today() - timedelta(days=args.days)).isoformat()
        txs = [t for t in txs if t["date"] >= cutoff]

    by_account: dict[str, list] = {}
    for t in txs:
        by_account.setdefault(t["account_id"], []).append(t)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Writing {len(txs)} transactions across {len(by_account)} accounts to {OUT_DIR.relative_to(REPO_ROOT)}/")

    for account_id, rows in by_account.items():
        acct = accounts.get(account_id, {})
        name = slug(acct.get("name", account_id))
        mask = acct.get("mask", "")
        fname = f"{name}_{mask}.csv" if mask else f"{name}.csv"
        path = OUT_DIR / fname

        rows.sort(key=lambda r: r["date"], reverse=True)
        with path.open("w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=COLUMNS)
            w.writeheader()
            for t in rows:
                pfc = t.get("personal_finance_category") or {}
                w.writerow({
                    "date": t["date"],
                    "description": t["name"],
                    "amount": t["amount"],
                    "merchant": t.get("merchant_name") or "",
                    "category": pfc.get("primary") or "",
                    "pending": "true" if t["pending"] else "false",
                    "plaid_transaction_id": t["transaction_id"],
                })
        print(f"  {fname:40} {len(rows):4d} rows  ({acct.get('type')}/{acct.get('subtype')})")


if __name__ == "__main__":
    main()
