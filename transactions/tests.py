from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase

from accounts.models import Account
from transactions.models import Transaction


class ChargedToCardsTests(TestCase):
    """`.charged_to_cards()` is the data behind the (not-yet-rendered) home
    tile that surfaces credit-card debt taken on this period. It must:
      - count card swipes (negative txn on a credit account)
      - ignore cash/checking spending (negative txn on non-credit account)
      - ignore card refunds (positive txn on a credit account)
      - ignore card payments (transfer pair) once `.operational()` is chained
    """

    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="cardholder", password="x"
        )
        self.checking = Account.objects.create(
            owner=self.user, name="Checking", type=Account.CHECKING
        )
        self.card = Account.objects.create(
            owner=self.user, name="Visa", type=Account.CREDIT
        )

    def _txn(self, account, amount, *, is_transfer=False, day=15):
        return Transaction.objects.create(
            account=account,
            date=date(2026, 5, day),
            amount=Decimal(amount),
            is_savings_transfer=is_transfer,
        )

    def test_card_swipe_counts(self):
        self._txn(self.card, "-42.00")
        self.assertEqual(
            Transaction.objects.charged_to_cards(), Decimal("42.00")
        )

    def test_checking_spend_ignored(self):
        self._txn(self.checking, "-42.00")
        self.assertEqual(Transaction.objects.charged_to_cards(), Decimal(0))

    def test_card_refund_ignored(self):
        # A merchant refund posts as a positive amount on the card. It reduces
        # debt but is not "debt taken on" — it should not count here.
        self._txn(self.card, "10.00")
        self.assertEqual(Transaction.objects.charged_to_cards(), Decimal(0))

    def test_card_payment_excluded_via_operational(self):
        # Bill payment: −X on checking, +X on card, both flagged as transfers.
        # Neither side should appear in `charged_to_cards` once .operational()
        # is chained — a payment isn't "debt taken on."
        self._txn(self.checking, "-100.00", is_transfer=True)
        self._txn(self.card, "100.00", is_transfer=True)
        self.assertEqual(
            Transaction.objects.operational().charged_to_cards(), Decimal(0)
        )

    def test_multiple_card_swipes_sum(self):
        self._txn(self.card, "-10.00", day=2)
        self._txn(self.card, "-25.50", day=10)
        self._txn(self.card, "-4.50", day=18)
        self.assertEqual(
            Transaction.objects.charged_to_cards(), Decimal("40.00")
        )

    def test_chains_with_in_range(self):
        self._txn(self.card, "-30.00", day=3)   # in range
        self._txn(self.card, "-5.00", day=25)   # out of range
        result = (
            Transaction.objects.in_range(date(2026, 5, 1), date(2026, 5, 15))
            .charged_to_cards()
        )
        self.assertEqual(result, Decimal("30.00"))
