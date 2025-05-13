from django.db import models
from django.utils import timezone


class SiteConfigurations(models.Model):
    key = models.CharField(max_length=100, unique=True)
    value = models.TextField()

    def __str__(self):
        return f"{self.key}: {self.value}"

    @classmethod
    def get_all_parameters(cls):
        return {config.key: config.value for config in cls.objects.all()}


class Room(models.Model):
    name = models.CharField(max_length=255)

    def __str__(self):
        return self.name


class Sensor(models.Model):
    name = models.CharField(max_length=255)
    room = models.ForeignKey(Room, on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.name} in {self.room}"


class DataPoint(models.Model):
    timestamp = models.DateTimeField(default=timezone.now, db_index=True)
    sensor = models.CharField(max_length=255, db_index=True)
    metric = models.CharField(max_length=1, db_index=True)
    value = models.FloatField()

    class Meta:
        indexes = [
            models.Index(fields=['sensor', 'timestamp']),
            models.Index(fields=['timestamp']),
            models.Index(fields=['sensor', 'metric', 'timestamp']),
            models.Index(fields=['sensor', 'metric', 'value']),
            models.Index(fields=['metric', 'timestamp']),
        ]

    def __str__(self):
        return f"{self.sensor} at {self.timestamp}"