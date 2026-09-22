from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("rdgenerator", "0005_buildversionsequence_githubrun_version"),
    ]

    operations = [
        migrations.AddField(
            model_name="githubrun",
            name="connection_direction",
            field=models.CharField(blank=True, max_length=16),
        ),
        migrations.AddField(
            model_name="githubrun",
            name="update_channel",
            field=models.CharField(blank=True, db_index=True, max_length=32),
        ),
    ]
