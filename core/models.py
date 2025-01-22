# Django
from django.db import models
from django.utils import timezone
from django.conf import settings

class SensorDataManager(models.Manager):
    """Custom manager that automatically filters out ignored sensors"""
    def get_queryset(self):
        qs = super().get_queryset()
        if getattr(settings, 'IGNORE_SENSORS', None):
            qs = qs.exclude(sensor__in=settings.IGNORE_SENSORS)
        return qs

class SensorData(models.Model):
    """
    Modelo para almacenar datos de sensores con timestamp, identificador del sensor,
    temperatura (t) y humedad (h).
    """
    timestamp = models.DateTimeField(default=timezone.now)
    sensor = models.CharField(max_length=255)
    t = models.FloatField()
    h = models.FloatField()

    # Replace default manager with custom manager
    objects = SensorDataManager()

    def __str__(self) -> str:
        return f"{self.sensor} at {self.timestamp}"
