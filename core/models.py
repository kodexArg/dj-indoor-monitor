from django.db import models
from django.utils import timezone

class SensorData(models.Model):
    timestamp = models.DateTimeField(default=timezone.now)
    sensor = models.CharField(max_length=255)
    t = models.FloatField()
    h = models.FloatField()

    def __str__(self):
        return f"{self.sensor} at {self.timestamp}"
