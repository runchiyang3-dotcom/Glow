from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0003_userprofile_avatar"),
    ]

    operations = [
        migrations.AddField(
            model_name="userprofile",
            name="payment_enabled",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="userprofile",
            name="social_media",
            field=models.CharField(blank=True, max_length=240),
        ),
        migrations.AddField(
            model_name="userprofile",
            name="stripe_onboarding_started",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="artistportfolio",
            name="price_range",
            field=models.CharField(blank=True, max_length=80),
        ),
        migrations.AddField(
            model_name="artistportfolio",
            name="style_tags",
            field=models.CharField(blank=True, max_length=180),
        ),
    ]
