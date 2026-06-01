from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0007_artistportfolio_address_artistportfolio_image_and_more"),
    ]

    operations = [
        migrations.RenameField(
            model_name="artistportfolio",
            old_name="likes",
            new_name="views",
        ),
    ]
