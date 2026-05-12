from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase

from accounts.models import Account, net_worth
from transactions.models import Transaction


class AccountQuerySetFiltersTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        User = get_user_model()
        cls.user = User.objects.create_user(username="alice", password="x")
        cls.checking = Account.objects.create(
            owner=cls.user, name="Chk", type=Account.CHECKING, balance=Decimal("100")
        )
        cls.savings = Account.objects.create(
            owner=cls.user, name="Sav", type=Account.SAVINGS, balance=Decimal("200")
        )
        cls.credit = Account.objects.create(
            owner=cls.user, name="Card", type=Account.CREDIT, balance=Decimal("50")
        )

    def test_savings_assets_includes_checking_and_savings(self):
        qs = Account.objects.filter(owner=self.user).savings_assets()
        self.assertCountEqual(list(qs), [self.checking, self.savings])

    def test_debt_includes_only_credit(self):
        qs = Account.objects.filter(owner=self.user).debt()
        self.assertCountEqual(list(qs), [self.credit])


class NetWorthTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        User = get_user_model()
        cls.user = User.objects.create_user(username="bob", password="x")
        cls.other = User.objects.create_user(username="eve", password="x")

    def test_empty_returns_zero(self):
        self.assertEqual(net_worth(self.user), Decimal("0.00"))

    def test_assets_minus_debt(self):
        Account.objects.create(
            owner=self.user, name="Chk", type=Account.CHECKING, balance=Decimal("1000")
        )
        Account.objects.create(
            owner=self.user, name="Sav", type=Account.SAVINGS, balance=Decimal("4000")
        )
        Account.objects.create(
            owner=self.user, name="Card", type=Account.CREDIT, balance=Decimal("750")
        )
        # 1000 + 4000 - 750 = 4250
        self.assertEqual(net_worth(self.user), Decimal("4250.00"))

    def test_debt_subtracts_does_not_add(self):
        # Debt-only user: net worth must be negative, not positive.
        Account.objects.create(
            owner=self.user, name="Card", type=Account.CREDIT, balance=Decimal("500")
        )
        self.assertEqual(net_worth(self.user), Decimal("-500.00"))

    def test_uses_current_balance_not_starting_balance(self):
        # current_balance = balance + sum(transactions.amount)
        chk = Account.objects.create(
            owner=self.user, name="Chk", type=Account.CHECKING, balance=Decimal("100")
        )
        Transaction.objects.create(
            account=chk, date="2026-01-01", amount=Decimal("50")
        )
        card = Account.objects.create(
            owner=self.user, name="Card", type=Account.CREDIT, balance=Decimal("0")
        )
        Transaction.objects.create(
            account=card, date="2026-01-02", amount=Decimal("-30")
        )
        # assets: 100 + 50 = 150; debt: 0 + (-30) = -30; net: 150 - (-30) = 180
        self.assertEqual(net_worth(self.user), Decimal("180.00"))

    def test_scoped_to_user(self):
        Account.objects.create(
            owner=self.other, name="Other", type=Account.CHECKING, balance=Decimal("9999")
        )
        self.assertEqual(net_worth(self.user), Decimal("0.00"))
