from django.db import models
from django.utils import timezone

class GithubRun(models.Model):
    id = models.IntegerField(verbose_name="ID",primary_key=True)
    uuid = models.CharField(verbose_name="uuid", max_length=100)
    status = models.CharField(verbose_name="status", max_length=100)
    github_run_id = models.BigIntegerField(null=True, blank=True)
    filename = models.CharField(max_length=255, blank=True)
    platform = models.CharField(max_length=32, blank=True)
    created_at = models.DateTimeField(default=timezone.now, db_index=True)
