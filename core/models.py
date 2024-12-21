# Django
from django.db import models
from django.utils import timezone

class SensorData(models.Model):
    """
    Modelo para almacenar datos de sensores con timestamp, identificador del sensor,
    temperatura (t) y humedad (h).
    """
    timestamp = models.DateTimeField(default=timezone.now)
    sensor = models.CharField(max_length=255)
    t = models.FloatField()
    h = models.FloatField()

    def __str__(self) -> str:
        return f"{self.sensor} at {self.timestamp}"
