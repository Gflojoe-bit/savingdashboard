"""Seed a local dev DB with realistic demo data.

Generates a demo user with 4 accounts (checking + savings + 2 credit cards),
~12 months of varied transactions including transfer pairs, and 4 balanced
goals. Idempotent via `external_id="demo:*"` keys; pass `--reset` to wipe and
re-seed.

Not for production. Bails out if `settings.DEBUG` is False.

Spec: docs/dev-fixtures-handoff.md.
"""
import random
from calendar import monthrange
from datetime import date, timedelta
from decimal import Decimal

from django.conf import settings as django_settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction as db_transaction

from accounts.models import Account
from auth_app.models import Space, SpaceMembership, current_space
from goals.models import Goal
from transactions.models import Transaction


SEED = 42

ACCOUNT_FIXTURES = [
    {
        "key": "checking",
        "name": "Everyday Checking",
        "type": Account.CHECKING,
        "institution": "Chase",
        "balance": Decimal("2400.00"),
    },
    {
        "key": "savings",
        "name": "Emergency Fund",
        "type": Account.SAVINGS,
        "institution": "Ally",
        "balance": Decimal("8500.00"),
    },
    {
        "key": "visa",
        "name": "Sapphire Visa",
        "type": Account.CREDIT,
        "institution": "Chase",
        "balance": Decimal("1250.00"),
    },
    {
        "key": "costco",
        "name": "Costco Anywhere",
        "type": Account.CREDIT,
        "institution": "Citi",
        "balance": Decimal("340.00"),
    },
]

GROCERY_MERCHANTS = ["Trader Joe's", "Whole Foods", "Safeway"]
DINING_MERCHANTS = [
    "Chipotle",
    "Sweetgreen",
    "Olive Garden",
    "The Cheesecake Factory",
    "Local Diner",
    "Sushi House",
    "Tacos El Gordo",
    "Thai Spice",
    "Burger Joint",
    "Pho Saigon",
]
GAS_MERCHANTS = ["Shell", "Chevron"]
UTILITIES = [
    ("Comcast", 60, 90),
    ("PG&E", 80, 180),
    ("Water", 30, 60),
]
STREAMING = [
    ("Netflix", Decimal("15.99")),
    ("Spotify", Decimal("10.99")),
]


class Command(BaseCommand):
    help = "Seed a local dev DB with a demo user, accounts, transactions, and goals."

    def add_arguments(self, parser):
        parser.add_argument(
            "--username",
            default="demo",
            help="Demo user to create or reuse (default: demo).",
        )
        parser.add_argument(
            "--reset",
            action="store_true",
            help="Delete the user's existing accounts and goals before seeding.",
        )
        parser.add_argument(
            "--months",
            type=int,
            default=12,
            help="How many months of transaction history to generate (default: 12).",
        )

    def handle(self, *args, **opts):
        if not django_settings.DEBUG:
            self.stderr.write(
                self.style.ERROR(
                    "seed_demo refuses to run with DEBUG=False. "
                    "This command is for local development only."
                )
            )
            return

        username = opts["username"]
        months = opts["months"]
        reset = opts["reset"]

        User = get_user_model()
        user, created = User.objects.get_or_create(username=username)
        if created:
            user.set_unusable_password()
            user.save()

        space = current_space(user)
        if space is None:
            # The post_save signal in auth_app should have created this; safety net
            # in case the signal was disabled or the user pre-existed without one.
            space = Space.objects.create(
                name=f"{user.get_username()}'s Space",
                owner=user,
                is_personal=True,
            )
            SpaceMembership.objects.create(space=space, user=user)

        with db_transaction.atomic():
            if reset:
                user.accounts.all().delete()  # cascades to transactions
                user.goals.all().delete()

            accounts_by_key = self._upsert_accounts(user, space)
            txn_count = self._upsert_transactions(user, accounts_by_key, months)
            goal_count = self._upsert_goals(user)

        self.stdout.write(
            self.style.SUCCESS(
                f"Seeded {len(accounts_by_key)} accounts, {txn_count} transactions, "
                f"{goal_count} goals for user {username}."
            )
        )

    def _upsert_accounts(self, user, space):
        accounts_by_key = {}
        for fx in ACCOUNT_FIXTURES:
            ext_id = f"demo:account:{fx['key']}"
            acct, _ = Account.objects.update_or_create(
                external_id=ext_id,
                defaults={
                    "owner": user,
                    "name": fx["name"],
                    "type": fx["type"],
                    "institution": fx["institution"],
                    "balance": fx["balance"],
                },
            )
            space.accounts.add(acct)
            accounts_by_key[fx["key"]] = acct
        return accounts_by_key

    def _upsert_transactions(self, user, accounts_by_key, months):
        events = self._generate_events(accounts_by_key, months)
        # Deterministic order so external_id assignment is stable across runs.
        events.sort(
            key=lambda e: (
                e["date"],
                e["account_key"],
                str(e["amount"]),
                e["description"],
            )
        )

        seen = set()
        for idx, e in enumerate(events):
            ext_id = f"demo:txn:{idx:04d}"
            seen.add(ext_id)
            Transaction.objects.update_or_create(
                external_id=ext_id,
                defaults={
                    "account": accounts_by_key[e["account_key"]],
                    "date": e["date"],
                    "amount": e["amount"],
                    "description": e["description"],
                    "merchant": e["merchant"],
                    "category": e["category"],
                    "is_savings_transfer": e["is_savings_transfer"],
                },
            )

        # Drop demo rows that fell out of the seed (e.g. after editing the
        # generator). Scoped to this user's accounts so we never touch other
        # demo users' data.
        Transaction.objects.filter(
            external_id__startswith="demo:txn:",
            account__owner=user,
        ).exclude(external_id__in=seen).delete()

        return len(events)

    def _generate_events(self, accounts_by_key, months):
        rng = random.Random(SEED)
        today = date.today()
        events = []

        def add(account_key, d, amount, desc, merchant="", category="", transfer=False):
            events.append(
                {
                    "account_key": account_key,
                    "date": d,
                    "amount": Decimal(str(amount)),
                    "description": desc,
                    "merchant": merchant,
                    "category": category,
                    "is_savings_transfer": transfer,
                }
            )

        def safe_date(year, month, day):
            return date(year, month, min(day, monthrange(year, month)[1]))

        def money(value):
            return Decimal(str(round(value, 2))).quantize(Decimal("0.01"))

        months_list = self._months_iter(today, months)
        bonus_idx = months // 2

        for i, (year, month) in enumerate(months_list):
            # Paychecks on the 1st and 15th
            for day in (1, 15):
                d = safe_date(year, month, day)
                if d <= today:
                    add("checking", d, "3400.00", "Paycheck", "Acme Corp", "Income")

            # Rent on the 1st
            d = safe_date(year, month, 1)
            if d <= today:
                add("checking", d, "-1400.00", "Rent", "Landlord", "Housing")

            # Utilities mid-month
            for util_name, lo, hi in UTILITIES:
                day = rng.randint(10, 20)
                d = safe_date(year, month, day)
                if d <= today:
                    amt = -money(rng.uniform(lo, hi))
                    add("checking", d, amt, util_name, util_name, "Utilities")

            # Streaming subscriptions, mostly on the Visa
            for sub_name, sub_amt in STREAMING:
                day = rng.randint(5, 25)
                d = safe_date(year, month, day)
                if d <= today:
                    add("visa", d, -sub_amt, sub_name, sub_name, "Subscriptions")

            # Groceries — 6 per month, split between Checking and Visa
            for _ in range(6):
                day = rng.randint(1, 28)
                d = safe_date(year, month, day)
                if d > today:
                    continue
                merchant = rng.choice(GROCERY_MERCHANTS)
                amt = -money(rng.uniform(40, 140))
                acct_key = "checking" if rng.random() < 0.4 else "visa"
                add(acct_key, d, amt, merchant, merchant, "Groceries")

            # Dining — 10 per month, mostly on Visa
            for _ in range(10):
                day = rng.randint(1, 28)
                d = safe_date(year, month, day)
                if d > today:
                    continue
                merchant = rng.choice(DINING_MERCHANTS)
                amt = -money(rng.uniform(15, 80))
                acct_key = "visa" if rng.random() < 0.85 else "checking"
                add(acct_key, d, amt, merchant, merchant, "Dining")

            # Gas — 2 per month
            for _ in range(2):
                day = rng.randint(1, 28)
                d = safe_date(year, month, day)
                if d > today:
                    continue
                merchant = rng.choice(GAS_MERCHANTS)
                amt = -money(rng.uniform(30, 60))
                add("visa", d, amt, merchant, merchant, "Gas")

            # Costco run
            day = rng.randint(1, 28)
            d = safe_date(year, month, day)
            if d <= today:
                amt = -money(rng.uniform(80, 220))
                add("costco", d, amt, "Costco", "Costco", "Shopping")

            # Monthly transfer to Emergency Fund (saver's reflex)
            d = safe_date(year, month, 16)
            if d <= today:
                add(
                    "checking",
                    d,
                    "-400.00",
                    "Transfer to Emergency Fund",
                    "",
                    "Transfer",
                    transfer=True,
                )
                add(
                    "savings",
                    d,
                    "400.00",
                    "Transfer from Checking",
                    "",
                    "Transfer",
                    transfer=True,
                )

            # Card payments — variable amount, both cards
            for card_key, card_name in (
                ("visa", "Sapphire Visa"),
                ("costco", "Costco Anywhere"),
            ):
                day = rng.randint(20, 28)
                d = safe_date(year, month, day)
                if d > today:
                    continue
                amt = money(rng.uniform(200, 800))
                add(
                    "checking",
                    d,
                    -amt,
                    f"Payment to {card_name}",
                    "",
                    "Transfer",
                    transfer=True,
                )
                add(
                    card_key,
                    d,
                    amt,
                    "Payment from Checking",
                    "",
                    "Transfer",
                    transfer=True,
                )

            # Bonus paycheck around month 6
            if i == bonus_idx:
                day = rng.randint(10, 20)
                d = safe_date(year, month, day)
                if d <= today:
                    add(
                        "checking", d, "1200.00", "Annual Bonus", "Acme Corp", "Income"
                    )

        # Refunds — one in the past 30 days, one earlier in the year. Refund
        # convention today is amount > 0 on a spending category (see CLAUDE.md
        # "Not yet decided") — surface that edge case in the seed so the design
        # pass sees it.
        refund_recent = today - timedelta(days=rng.randint(5, 25))
        add("visa", refund_recent, "60.00", "Refund - Online Order", "Online Store", "Refund")
        refund_older_offset = rng.randint(120, 240)
        refund_older = today - timedelta(days=refund_older_offset)
        earliest = today - timedelta(days=months * 30)
        if refund_older >= earliest:
            add("visa", refund_older, "60.00", "Refund - Returned Item", "Local Store", "Refund")

        return events

    @staticmethod
    def _months_iter(today, months):
        """Yield (year, month) pairs for the past `months` calendar months
        ending in today's month, oldest first."""
        year, month = today.year, today.month
        pairs = []
        for _ in range(months):
            pairs.append((year, month))
            month -= 1
            if month == 0:
                month = 12
                year -= 1
        return list(reversed(pairs))

    def _upsert_goals(self, user):
        today = date.today()
        # "New Bike" was specced as category="recreation" but the Goal model
        # only ships emergency/investing/vacation/home/other choices, and this
        # branch is data-only. Map to OTHER.
        goal_specs = [
            ("6-month Emergency Fund", Goal.EMERGENCY, Decimal("15000.00"), None, Decimal(40)),
            ("Hawaii Trip", Goal.VACATION, Decimal("4000.00"), today + timedelta(days=270), Decimal(25)),
            ("New Bike", Goal.OTHER, Decimal("1800.00"), None, Decimal(15)),
            ("Brokerage Top-up", Goal.INVESTING, Decimal("6000.00"), None, Decimal(20)),
        ]
        for name, category, target, target_date, basket in goal_specs:
            Goal.objects.update_or_create(
                owner=user,
                name=name,
                defaults={
                    "category": category,
                    "target_amount": target,
                    "target_date": target_date,
                    "basket_percent": basket,
                },
            )
        return len(goal_specs)
