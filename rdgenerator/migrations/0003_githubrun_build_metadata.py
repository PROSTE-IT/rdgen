from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):
    dependencies = [
        ("rdgenerator", "0002_githubrun_github_run_id"),
    ]

    operations = [
        migrations.AddField(
            model_name="githubrun",
            name="created_at",
            field=models.DateTimeField(
                db_index=True,
                default=django.utils.timezone.now,
            ),
        ),
        migrations.AddField(
            model_name="githubrun",
            name="filename",
            field=models.CharField(blank=True, max_length=255),
        ),
        migrations.AddField(
            model_name="githubrun",
            name="platform",
            field=models.CharField(blank=True, max_length=32),
        ),
    ]
