from django.db import models
from django.utils import timezone
from django.conf import settings


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
    timestamp = models.DateTimeField(default=timezone.now)
    sensor = models.CharField(max_length=255) # not related to Sensor model
    metric = models.CharField(max_length=1) # t, h, s, l
    value = models.FloatField()

    def __str__(self):
        return f"{self.sensor} at {self.timestamp}"