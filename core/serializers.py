from rest_framework import serializers
from .models import SensorData
from django.utils.timezone import make_aware
from datetime import datetime

class SensorDataSerializer(serializers.ModelSerializer):
    timestamp = serializers.DateTimeField(
        format='%Y-%m-%dT%H:%M:%SZ',
        input_formats=[
            '%Y-%m-%dT%H:%M:%SZ',         # Formato esperado por la API, con Z (UTC)
            '%Y-%m-%dT%H:%M:%S.%fZ',      # Con microsegundos y Z (UTC)
            '%Y-%m-%dT%H:%M:%S',          # Sin Z y sin microsegundos (hora local)
            '%Y-%m-%d %H:%M:%S',          # Con espacio en lugar de 'T'
            'iso-8601'                    # Formato ISO-8601 general (lo más flexible)
        ]
    )

    def validate_timestamp(self, value):
        if value.tzinfo is None:
            value = make_aware(value)
        return value

    class Meta:
        model = SensorData
        fields = ['timestamp', 'rpi', 't', 'h']
