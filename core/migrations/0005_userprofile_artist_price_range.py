from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0004_artist_onboarding_fields"),
    ]

    operations = [
        migrations.AddField(
            model_name="userprofile",
            name="artist_price_range",
            field=models.CharField(blank=True, max_length=80),
        ),
    ]
