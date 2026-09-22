from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("rdgenerator", "0004_githubrun_deleted_at"),
    ]

    operations = [
        migrations.CreateModel(
            name="BuildVersionSequence",
            fields=[
                (
                    "base_version",
                    models.CharField(max_length=32, primary_key=True, serialize=False),
                ),
                ("last_revision", models.PositiveIntegerField(default=0)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={"ordering": ["base_version"]},
        ),
        migrations.AddField(
            model_name="githubrun",
            name="base_version",
            field=models.CharField(blank=True, max_length=32),
        ),
        migrations.AddField(
            model_name="githubrun",
            name="pit_revision",
            field=models.PositiveIntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="githubrun",
            name="pit_version",
            field=models.CharField(blank=True, max_length=64),
        ),
    ]
