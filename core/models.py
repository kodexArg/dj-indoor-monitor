# models.py
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
        return {config.key: config.value for config in cls.objects.all()}


class Room(models.Model):
    name = models.CharField(max_length=255)
    sensors = models.TextField()

    def __str__(self):
        return self.name
    
    def get_sensor_list(self):
        return [sensor.strip() for sensor in self.sensors.split(',')]


class SensorDataManager(models.Manager):
    def get_queryset(self):
        qs = super().get_queryset()
        if getattr(settings, 'IGNORE_SENSORS', None):
            qs = qs.exclude(sensor__in=settings.IGNORE_SENSORS)
        qs = qs.exclude(t__lte=1, h__lte=1)
        return qs


class SensorData(models.Model):
    timestamp = models.DateTimeField(default=timezone.now)
    sensor = models.CharField(max_length=255)
    t = models.FloatField(null=True, blank=True)
    h = models.FloatField(null=True, blank=True)
    s = models.FloatField(null=True, blank=True)
    l = models.FloatField(null=True, blank=True)
    r = models.FloatField(null=True, blank=True)

    objects = SensorDataManager()

    def __str__(self) -> str:
        return f"{self.sensor} at {self.timestamp}"


class SensorDataLegacy(SensorData):
    class Meta:
        proxy = True 
        verbose_name = "Legacy Sensor Data (t & h)"
    
    objects = SensorDataManager()

    def get_queryset(self):
        return super().get_queryset().only("timestamp", "sensor", "t", "h")


class DataPoint(models.Model):
    timestamp = models.DateTimeField(default=timezone.now)
    sensor = models.CharField(max_length=255)
    metric = models.CharField(max_length=1) # t, h, s, l
    value = models.FloatField()

    def __str__(self):
        return f"{self.sensor} at {self.timestamp}"