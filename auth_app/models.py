from django.conf import settings
from django.db import models


class Space(models.Model):
    """A combined view over the union of opted-in accounts from member users.

    Per CLAUDE.md "Decisions": each User privately owns their Accounts and
    Goals; Spaces are *views*, not shared ownership. Phase 1 ships only the
    Personal Space (auto-created on user creation), so there's exactly one
    Space per user and `accounts` opts in everything that user owns. Phase 2
    will introduce multi-member Spaces with selective per-account opt-in.
    """

    name = models.CharField(max_length=100)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="owned_spaces",
    )
    is_personal = models.BooleanField(
        default=False,
        help_text="True for the auto-created Personal Space; only one per user.",
    )
    accounts = models.ManyToManyField(
        "accounts.Account",
        related_name="spaces",
        blank=True,
        help_text="Per-account opt-in into this Space's combined view.",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["owner"],
                condition=models.Q(is_personal=True),
                name="auth_app_one_personal_space_per_owner",
            ),
        ]

    def __str__(self):
        return self.name

    def transactions_qs(self):
        """Transactions on accounts opted into this Space."""
        from transactions.models import Transaction

        return Transaction.objects.filter(account__in=self.accounts.all())


class SpaceMembership(models.Model):
    space = models.ForeignKey(
        Space, on_delete=models.CASCADE, related_name="memberships"
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="space_memberships",
    )
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["space", "user"], name="auth_app_unique_space_member"
            ),
        ]

    def __str__(self):
        return f"{self.user} in {self.space}"


def current_space(user):
    """Resolve the active Space for a user.

    Phase 1: every user has exactly one Space (their Personal Space, auto-
    created on signup), so we return it directly. Phase 2 will introduce a
    Space switcher (session-stored selection) and this becomes the lookup
    indirection.
    """
    return Space.objects.filter(memberships__user=user, is_personal=True).first()
