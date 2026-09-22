from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("rdgenerator", "0006_githubrun_update_identity"),
    ]

    operations = [
        migrations.AddField(
            model_name="githubrun",
            name="build_profile",
            field=models.CharField(blank=True, default="standard", max_length=32),
        ),
    ]
