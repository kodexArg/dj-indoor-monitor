from rest_framework import serializers
from .models import SensorData
from django.utils.timezone import localtime

class SensorDataSerializer(serializers.ModelSerializer):
    """
    Serializer for SensorData model.
    """
    timestamp = serializers.SerializerMethodField()

    class Meta:
        model = SensorData
        fields = ['timestamp', 'rpi', 't', 'h']

    def get_timestamp(self, obj):
        return localtime(obj.timestamp).isoformat()
