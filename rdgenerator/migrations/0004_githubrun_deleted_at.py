from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("rdgenerator", "0003_githubrun_build_metadata"),
    ]

    operations = [
        migrations.AddField(
            model_name="githubrun",
            name="deleted_at",
            field=models.DateTimeField(blank=True, db_index=True, null=True),
        ),
    ]
