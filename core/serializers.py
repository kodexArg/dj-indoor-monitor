from rest_framework import serializers
from django.utils.timezone import localtime
from .models import SensorData, SensorDataLegacy

class SensorDataSerializer(serializers.ModelSerializer):
    timestamp = serializers.SerializerMethodField()

    class Meta:
        model = SensorData
        fields = ['timestamp', 'sensor', 't', 'h', 's', 'l', 'r']

    def get_timestamp(self, obj: SensorData) -> str:
        return localtime(obj.timestamp).isoformat()

class SensorDataLegacySerializer(serializers.ModelSerializer):
    timestamp = serializers.SerializerMethodField()

    class Meta:
        model = SensorDataLegacy
        fields = ['timestamp', 'sensor', 't', 'h']

    def get_timestamp(self, obj: SensorDataLegacy) -> str:
        return localtime(obj.timestamp).isoformat()
