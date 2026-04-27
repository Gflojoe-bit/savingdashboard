"""One-off exploration script for Plaid Sandbox.

Flow:
  1. /sandbox/public_token/create  - mint a fake public_token for an institution
  2. /item/public_token/exchange    - swap for a real access_token
  3. /accounts/get                  - list accounts on the item
  4. /transactions/sync             - pull transactions

Dumps full JSON for each step to scripts/plaid_dump/ so we can study the shape
without re-hitting the API. Reads creds from ../.env.

Run from repo root:
  python scripts/plaid_explore.py
"""
import json
import os
import sys
import urllib.request
import urllib.error
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DUMP_DIR = REPO_ROOT / "scripts" / "plaid_dump"
ENV_FILE = REPO_ROOT / ".env"

PLAID_HOST = "https://sandbox.plaid.com"
INSTITUTION_ID = "ins_109508"  # "First Platypus Bank" - the canonical sandbox bank
PRODUCTS = ["transactions"]


def load_env(path: Path) -> dict:
    env = {}
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        env[k.strip()] = v.strip()
    return env


def post(path: str, body: dict) -> dict:
    req = urllib.request.Request(
        PLAID_HOST + path,
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        print(f"HTTP {e.code} on {path}", file=sys.stderr)
        print(e.read().decode(), file=sys.stderr)
        raise


def dump(name: str, data: dict) -> None:
    DUMP_DIR.mkdir(parents=True, exist_ok=True)
    out = DUMP_DIR / f"{name}.json"
    out.write_text(json.dumps(data, indent=2, default=str))
    print(f"  -> {out.relative_to(REPO_ROOT)}")


def main() -> None:
    env = load_env(ENV_FILE)
    client_id = env["PLAID_CLIENT_ID"]
    secret = env["PLAID_SECRET"]
    auth = {"client_id": client_id, "secret": secret}

    print("1. Creating sandbox public_token...")
    pub = post("/sandbox/public_token/create", {
        **auth,
        "institution_id": INSTITUTION_ID,
        "initial_products": PRODUCTS,
    })
    dump("01_public_token", pub)

    print("2. Exchanging for access_token...")
    exch = post("/item/public_token/exchange", {
        **auth,
        "public_token": pub["public_token"],
    })
    dump("02_access_token", exch)
    access_token = exch["access_token"]

    print("3. Fetching accounts...")
    accts = post("/accounts/get", {**auth, "access_token": access_token})
    dump("03_accounts", accts)
    print(f"   {len(accts['accounts'])} accounts")

    print("4. Syncing transactions (poll until HISTORICAL_UPDATE_COMPLETE, then drain)...")
    import time
    cursor = ""
    all_added = []
    sync = None
    for attempt in range(20):
        sync = post("/transactions/sync", {
            **auth,
            "access_token": access_token,
            "cursor": cursor,
        })
        status = sync.get("transactions_update_status")
        added_n = len(sync.get("added", []))
        print(f"   attempt {attempt + 1}: status={status} added={added_n} has_more={sync['has_more']}")
        all_added.extend(sync["added"])
        cursor = sync["next_cursor"]
        if status == "HISTORICAL_UPDATE_COMPLETE" and not sync["has_more"]:
            break
        if status in ("NOT_READY", "INITIAL_UPDATE_COMPLETE") and not sync["has_more"]:
            time.sleep(2)
            continue
        if sync["has_more"]:
            continue
    dump("04_transactions_sync_last_page", sync)
    dump("04_transactions_sync_all_added", {"added": all_added, "count": len(all_added)})
    print(f"   /sync total: {len(all_added)} transactions")

    print("5. /transactions/get with explicit date range (older endpoint, for comparison)...")
    from datetime import date, timedelta
    end = date.today()
    start = end - timedelta(days=730)  # 2 years
    tx_get = post("/transactions/get", {
        **auth,
        "access_token": access_token,
        "start_date": start.isoformat(),
        "end_date": end.isoformat(),
        "options": {"count": 500, "offset": 0},
    })
    dump("05_transactions_get", tx_get)
    print(f"   /get returned: {len(tx_get.get('transactions', []))} transactions "
          f"(total_transactions={tx_get.get('total_transactions')})")

    sample_pool = all_added or tx_get.get("transactions", [])
    if sample_pool:
        print("\nSample transaction:")
        print(json.dumps(sample_pool[0], indent=2, default=str))


if __name__ == "__main__":
    main()
