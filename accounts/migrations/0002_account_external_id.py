from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="account",
            name="external_id",
            field=models.CharField(max_length=64, blank=True, null=True, unique=True),
        ),
    ]
