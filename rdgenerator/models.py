from django.db import models
from django.utils import timezone

class GithubRun(models.Model):
    id = models.IntegerField(verbose_name="ID",primary_key=True)
    uuid = models.CharField(verbose_name="uuid", max_length=100)
    status = models.CharField(verbose_name="status", max_length=100)
    github_run_id = models.BigIntegerField(null=True, blank=True)
    filename = models.CharField(max_length=255, blank=True)
    platform = models.CharField(max_length=32, blank=True)
    base_version = models.CharField(max_length=32, blank=True)
    pit_revision = models.PositiveIntegerField(null=True, blank=True)
    pit_version = models.CharField(max_length=64, blank=True)
    created_at = models.DateTimeField(default=timezone.now, db_index=True)
    deleted_at = models.DateTimeField(null=True, blank=True, db_index=True)


class BuildVersionSequence(models.Model):
    base_version = models.CharField(max_length=32, primary_key=True)
    last_revision = models.PositiveIntegerField(default=0)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["base_version"]

    def __str__(self):
        return f"{self.base_version}-pit.{self.last_revision}"
