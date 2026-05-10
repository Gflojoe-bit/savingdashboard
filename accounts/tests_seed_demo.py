"""Tests for the seed_demo management command (docs/dev-fixtures-handoff.md)."""
from decimal import Decimal
from io import StringIO

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.db.models import Sum
from django.test import TestCase, override_settings

from accounts.models import Account
from auth_app.models import current_space
from goals.models import Goal, period_savings
from transactions.models import Transaction


def _seed(**kwargs):
    out = StringIO()
    call_command("seed_demo", stdout=out, **kwargs)
    return out.getvalue()


@override_settings(DEBUG=True)
class SeedDemoTests(TestCase):
    def test_creates_expected_counts(self):
        _seed()
        user = get_user_model().objects.get(username="demo")
        self.assertEqual(user.accounts.count(), 4)
        self.assertEqual(user.goals.count(), 4)
        # Spec target: ~200-300, threshold per handoff: ≥150.
        self.assertGreaterEqual(
            Transaction.objects.filter(account__owner=user).count(), 150
        )

    def test_idempotent_without_reset(self):
        _seed()
        accts = Account.objects.count()
        txns = Transaction.objects.count()
        goals = Goal.objects.count()

        _seed()  # second run

        self.assertEqual(Account.objects.count(), accts)
        self.assertEqual(Transaction.objects.count(), txns)
        self.assertEqual(Goal.objects.count(), goals)

    def test_reset_replaces_data(self):
        _seed()
        accts_first = Account.objects.count()
        txns_first = Transaction.objects.count()
        goals_first = Goal.objects.count()

        _seed(reset=True)

        # Same counts after reset (deterministic seed).
        self.assertEqual(Account.objects.count(), accts_first)
        self.assertEqual(Transaction.objects.count(), txns_first)
        self.assertEqual(Goal.objects.count(), goals_first)

    def test_personal_space_contains_all_accounts(self):
        _seed()
        user = get_user_model().objects.get(username="demo")
        space = current_space(user)
        self.assertIsNotNone(space)
        self.assertEqual(space.accounts.count(), 4)

    def test_basket_percent_sums_to_100(self):
        _seed()
        user = get_user_model().objects.get(username="demo")
        total = user.goals.aggregate(s=Sum("basket_percent"))["s"]
        self.assertEqual(total, Decimal(100))

    def test_transfer_pair_present(self):
        _seed()
        user = get_user_model().objects.get(username="demo")
        checking = user.accounts.get(external_id="demo:account:checking")
        visa = user.accounts.get(external_id="demo:account:visa")

        out_rows = Transaction.objects.filter(
            account=checking,
            is_savings_transfer=True,
            description__startswith="Payment to Sapphire",
        )
        in_rows = Transaction.objects.filter(
            account=visa,
            is_savings_transfer=True,
            amount__gt=0,
        )
        self.assertGreater(out_rows.count(), 0)
        self.assertGreater(in_rows.count(), 0)

        # At least one matched pair: same date, equal absolute amount.
        for out in out_rows:
            match = in_rows.filter(date=out.date, amount=-out.amount).first()
            if match is not None:
                return
        self.fail("Expected at least one Checking → Sapphire transfer pair.")

    def test_period_savings_positive(self):
        _seed()
        user = get_user_model().objects.get(username="demo")
        space = current_space(user)
        result = period_savings(base_qs=space.transactions_qs())
        self.assertIsInstance(result["all"], Decimal)
        self.assertGreater(result["all"], Decimal(0))


class SeedDemoDebugGuardTests(TestCase):
    @override_settings(DEBUG=False)
    def test_refuses_to_run_with_debug_false(self):
        _seed()
        self.assertFalse(
            get_user_model().objects.filter(username="demo").exists(),
            "seed_demo should bail out when DEBUG=False without creating data.",
        )
