"""Backfill existing Accounts and Goals onto a seed user + Personal Space.

Per CLAUDE.md (`auth` Phase 1): existing data is claimed by a seed Space so
the app remains functional after login is required. Strategy:

1. Pick the first existing superuser as the owner. If none exists, create
   a `seed` user with an unusable password — the dev sets one via
   `python manage.py changepassword seed` (or `createsuperuser`) before
   first login. Logging into the seed user surfaces the existing data.
2. Create that user's Personal Space (the post_save signal isn't wired
   into migrations, so we do it explicitly here for any pre-existing
   users too).
3. Assign the seed user as owner of every Account and Goal row.
4. Opt every Account into the seed user's Personal Space — Phase 1 has
   exactly one Space per user, so per-account opt-in collapses to "all".

Reverse migration unsets owners (ownerless rows) but does not delete the
seed user — manual cleanup if you really need to undo.
"""
from django.db import migrations


SEED_USERNAME = "seed"


def _resolve_seed_user(User):
    superuser = User.objects.filter(is_superuser=True).order_by("pk").first()
    if superuser:
        return superuser, False
    user, created = User.objects.get_or_create(
        username=SEED_USERNAME,
        defaults={"is_staff": False, "is_superuser": False},
    )
    if created:
        user.set_unusable_password()
        user.save(update_fields=["password"])
    return user, created


def backfill(apps, schema_editor):
    User = apps.get_model("auth", "User")
    Account = apps.get_model("accounts", "Account")
    Goal = apps.get_model("goals", "Goal")
    Space = apps.get_model("auth_app", "Space")
    SpaceMembership = apps.get_model("auth_app", "SpaceMembership")

    has_data = Account.objects.exists() or Goal.objects.exists()
    if not has_data and not User.objects.exists():
        # Fresh DB — nothing to claim, no need to manufacture a seed user.
        return

    seed, created = _resolve_seed_user(User)

    # Ensure every existing user has a Personal Space (the post_save signal
    # only fires for users created *after* this migration runs).
    for user in User.objects.all():
        space = Space.objects.filter(owner=user, is_personal=True).first()
        if space is None:
            space = Space.objects.create(
                name=f"{user.get_username()}'s Space",
                owner=user,
                is_personal=True,
            )
        SpaceMembership.objects.get_or_create(space=space, user=user)

    seed_space = Space.objects.get(owner=seed, is_personal=True)

    Account.objects.filter(owner__isnull=True).update(owner=seed)
    Goal.objects.filter(owner__isnull=True).update(owner=seed)

    seed_space.accounts.add(*Account.objects.filter(owner=seed))


def unbackfill(apps, schema_editor):
    Account = apps.get_model("accounts", "Account")
    Goal = apps.get_model("goals", "Goal")
    # Allow `migrate auth_app 0001` by clearing the owner FKs we set; the
    # follow-up AlterField migrations will be reverted in turn.
    Account.objects.update(owner=None)
    Goal.objects.update(owner=None)


class Migration(migrations.Migration):

    dependencies = [
        ("auth_app", "0001_initial"),
        ("accounts", "0003_account_owner"),
        ("goals", "0002_goal_owner"),
    ]

    operations = [
        migrations.RunPython(backfill, unbackfill),
    ]
