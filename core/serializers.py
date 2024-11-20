from rest_framework import serializers
from .models import SensorData
from django.utils.timezone import localtime

class SensorDataSerializer(serializers.ModelSerializer):
    timestamp = serializers.SerializerMethodField() # timestamp = serializers.DateTimeField(format='%Y-%m-%dT%H:%M:%S%z')

    class Meta:
        model = SensorData
        fields = ['timestamp', 'rpi', 't', 'h']

    def get_timestamp(self, obj):
        return localtime(obj.timestamp).isoformat()
