from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0002_account_external_id"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        # Nullable in this migration so the backfill data migration in
        # auth_app can claim existing rows without a default. The
        # follow-up migration (0004) flips null=False once everything
        # has an owner.
        migrations.AddField(
            model_name="account",
            name="owner",
            field=models.ForeignKey(
                null=True,
                on_delete=models.deletion.CASCADE,
                related_name="accounts",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
    ]
