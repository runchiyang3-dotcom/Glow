from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0008_rename_likes_to_views"),
    ]

    operations = [
        migrations.AlterField(
            model_name="messageitem",
            name="category",
            field=models.CharField(
                choices=[
                    ("booking", "Appointment"),
                    ("review", "Post comment"),
                    ("private", "Private message"),
                    ("payment", "Payment"),
                ],
                max_length=20,
            ),
        ),
    ]
