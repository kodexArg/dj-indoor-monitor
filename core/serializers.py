# Django y DRF
from rest_framework import serializers
from django.utils.timezone import localtime

# Local
from .models import SensorData

class SensorDataSerializer(serializers.ModelSerializer):
    """
    Serializador para el modelo SensorData.
    """
    timestamp = serializers.SerializerMethodField()

    class Meta:
        model = SensorData
        fields = ['timestamp', 'sensor', 't', 'h']

    def get_timestamp(self, obj):
        return localtime(obj.timestamp).isoformat()
