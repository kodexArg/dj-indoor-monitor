# Django
from django.db import models
from django.utils import timezone
from django.conf import settings


class SiteConfiguration(models.Model):
    key = models.CharField(max_length=100, unique=True)
    value = models.TextField()

    def __str__(self):
        return f"{self.key}: {self.value}"

    @classmethod
    def get_all_parameters(cls):
        """Devuelve todos los parámetros como un diccionario."""
        return {config.key: config.value for config in cls.objects.all()}


class Room(models.Model):
    name = models.CharField(max_length=255)
    sensors = models.TextField()

    def __str__(self):
        return self.name
    
    def get_sensor_list(self):
        return [sensor.strip() for sensor in self.sensors.split(',')]


class SensorDataManager(models.Manager):
    """Custom manager that automatically filters out ignored sensors"""
    def get_queryset(self):
        qs = super().get_queryset()
        if getattr(settings, 'IGNORE_SENSORS', None):
            qs = qs.exclude(sensor__in=settings.IGNORE_SENSORS)

        # ATENCIÓN: Los datos con temperatura y humedad 0 en la base de datos no se consideran en todo este sitio
        qs = qs.exclude(t__lte=1, h__lte=1)

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
