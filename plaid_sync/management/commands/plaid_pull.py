"""Sandbox-only Plaid sync.

v1: mints (or reuses) a sandbox access_token, pulls accounts and transactions
once, and upserts them into our models. No auth, no token encryption — both
land in v2 (see docs/security-plan.md).

Mapping rules per docs/plaid-data-shape.md:
  - amount is sign-flipped at the boundary (Plaid: +debit, ours: +income).
  - is_savings_transfer ← personal_finance_category.primary starts with TRANSFER_.
  - Account match by external_id (= Plaid account_id).
  - Transaction dedup by external_id (= Plaid transaction_id).

Account scope: depository checking and savings only. Sandbox returns 12 accounts
spanning credit/loan/investment too; those map onto the credit-cards subsystem
(not yet built) and would fail the Account.type choices today, so we skip them
with a warning.
"""
import json
import time
import urllib.error
import urllib.request
from decimal import Decimal
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction as db_transaction

from accounts.models import Account
from transactions.models import Transaction

PLAID_HOST = "https://sandbox.plaid.com"
SANDBOX_INSTITUTION_ID = "ins_109508"
PRODUCTS = ["transactions"]

SUPPORTED_SUBTYPES = {"checking", "savings"}


def _load_env(path: Path) -> dict:
    if not path.exists():
        return {}
    env = {}
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        env[k.strip()] = v.strip()
    return env


def _post(path: str, body: dict) -> dict:
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
        raise CommandError(
            f"Plaid {path} returned HTTP {e.code}: {e.read().decode()}"
        )


class Command(BaseCommand):
    help = "Pull Plaid sandbox accounts + transactions into the local DB."

    def add_arguments(self, parser):
        parser.add_argument(
            "--access-token",
            help=(
                "Reuse an existing sandbox access_token. If omitted, a fresh "
                "sandbox item is minted and the new token is printed."
            ),
        )
        parser.add_argument(
            "--max-poll",
            type=int,
            default=20,
            help="Max /transactions/sync poll attempts while waiting for HISTORICAL_UPDATE_COMPLETE.",
        )

    def handle(self, *args, **opts):
        env = _load_env(Path(settings.BASE_DIR) / ".env")
        client_id = env.get("PLAID_CLIENT_ID")
        secret = env.get("PLAID_SECRET")
        if not client_id or not secret:
            raise CommandError(
                "PLAID_CLIENT_ID and PLAID_SECRET must be set in .env"
            )
        auth = {"client_id": client_id, "secret": secret}

        access_token = opts["access_token"] or env.get("PLAID_ACCESS_TOKEN")
        if not access_token:
            access_token = self._mint_sandbox_item(auth)
            self.stdout.write(self.style.WARNING(
                f"Minted new sandbox access_token: {access_token}\n"
                f"Save it as PLAID_ACCESS_TOKEN in .env to reuse on the next run."
            ))

        self._sync_accounts(auth, access_token)
        self._sync_transactions(auth, access_token, max_poll=opts["max_poll"])

    # ---- Plaid API steps ----

    def _mint_sandbox_item(self, auth: dict) -> str:
        self.stdout.write("Minting sandbox public_token...")
        pub = _post("/sandbox/public_token/create", {
            **auth,
            "institution_id": SANDBOX_INSTITUTION_ID,
            "initial_products": PRODUCTS,
        })
        exch = _post("/item/public_token/exchange", {
            **auth,
            "public_token": pub["public_token"],
        })
        return exch["access_token"]

    def _sync_accounts(self, auth: dict, access_token: str) -> None:
        self.stdout.write("Fetching accounts...")
        resp = _post("/accounts/get", {**auth, "access_token": access_token})
        accounts = resp["accounts"]
        institution_name = self._lookup_institution_name(auth, resp.get("item", {}))

        kept = skipped = 0
        for acct in accounts:
            subtype = (acct.get("subtype") or "").lower()
            if acct.get("type") != "depository" or subtype not in SUPPORTED_SUBTYPES:
                self.stdout.write(self.style.WARNING(
                    f"  skip {acct['name']} ({acct.get('type')}/{acct.get('subtype')}): "
                    "unsupported account type for v1"
                ))
                skipped += 1
                continue

            balances = acct.get("balances") or {}
            currency = balances.get("iso_currency_code") or "USD"
            if currency != "USD":
                self.stdout.write(self.style.WARNING(
                    f"  skip {acct['name']}: non-USD ({currency})"
                ))
                skipped += 1
                continue

            obj, created = Account.objects.update_or_create(
                external_id=acct["account_id"],
                defaults={
                    "name": acct["name"],
                    "type": Account.CHECKING if subtype == "checking" else Account.SAVINGS,
                    "institution": institution_name,
                    "balance": Decimal(str(balances.get("current") or 0)),
                },
            )
            kept += 1
            verb = "created" if created else "updated"
            self.stdout.write(f"  {verb}: {obj.name} ({subtype}) bal={obj.balance}")

        self.stdout.write(self.style.SUCCESS(
            f"Accounts: {kept} synced, {skipped} skipped"
        ))

    def _lookup_institution_name(self, auth: dict, item: dict) -> str:
        ins_id = item.get("institution_id")
        if not ins_id:
            return ""
        try:
            resp = _post("/institutions/get_by_id", {
                **auth,
                "institution_id": ins_id,
                "country_codes": ["US"],
            })
            return resp.get("institution", {}).get("name", "")
        except CommandError:
            return ""

    def _sync_transactions(self, auth: dict, access_token: str, *, max_poll: int) -> None:
        self.stdout.write("Syncing transactions (cursor=\"\", polling for HISTORICAL_UPDATE_COMPLETE)...")
        cursor = ""
        added: list[dict] = []
        modified: list[dict] = []
        removed: list[dict] = []

        for attempt in range(max_poll):
            resp = _post("/transactions/sync", {
                **auth,
                "access_token": access_token,
                "cursor": cursor,
            })
            status = resp.get("transactions_update_status")
            added.extend(resp.get("added", []))
            modified.extend(resp.get("modified", []))
            removed.extend(resp.get("removed", []))
            cursor = resp["next_cursor"]
            self.stdout.write(
                f"  attempt {attempt + 1}: status={status} "
                f"+{len(resp.get('added', []))} ~{len(resp.get('modified', []))} "
                f"-{len(resp.get('removed', []))} has_more={resp['has_more']}"
            )
            if resp["has_more"]:
                continue
            if status == "HISTORICAL_UPDATE_COMPLETE":
                break
            time.sleep(2)
        else:
            self.stdout.write(self.style.WARNING(
                f"  gave up after {max_poll} polls; importing what we have"
            ))

        self._import_transactions(added + modified, removed)

    # ---- DB upsert ----

    @db_transaction.atomic
    def _import_transactions(self, upserts: list[dict], removed: list[dict]) -> None:
        accounts_by_ext = {
            a.external_id: a for a in Account.objects.exclude(external_id__isnull=True)
        }

        imported = skipped_no_account = skipped_currency = 0
        for tx in upserts:
            account = accounts_by_ext.get(tx["account_id"])
            if not account:
                skipped_no_account += 1
                continue
            if (tx.get("iso_currency_code") or "USD") != "USD":
                skipped_currency += 1
                continue

            primary = ((tx.get("personal_finance_category") or {}).get("primary") or "")
            is_transfer = primary.startswith("TRANSFER_")

            Transaction.objects.update_or_create(
                external_id=tx["transaction_id"],
                defaults={
                    "account": account,
                    "date": tx["date"],
                    # Sign flip: Plaid +debit → ours +income
                    "amount": -Decimal(str(tx["amount"])),
                    "description": tx.get("name") or "",
                    "merchant": tx.get("merchant_name") or "",
                    "category": primary,
                    "pending": tx.get("pending", False),
                    "is_savings_transfer": is_transfer,
                },
            )
            imported += 1

        deleted = 0
        if removed:
            ext_ids = [r["transaction_id"] for r in removed]
            deleted, _ = Transaction.objects.filter(external_id__in=ext_ids).delete()

        self.stdout.write(self.style.SUCCESS(
            f"Transactions: {imported} upserted, {deleted} removed"
        ))
        if skipped_no_account:
            self.stdout.write(self.style.WARNING(
                f"  {skipped_no_account} skipped (account not in DB — "
                "likely an unsupported subtype like credit/loan/investment)"
            ))
        if skipped_currency:
            self.stdout.write(self.style.WARNING(
                f"  {skipped_currency} skipped (non-USD)"
            ))
