from rest_framework import serializers
from django.utils.timezone import localtime
from .models import DataPoint

class DataPointSerializer(serializers.ModelSerializer):
    timestamp = serializers.SerializerMethodField()

    class Meta:
        model = DataPoint
        fields = ['timestamp', 'sensor', 'metric', 'value']

    def get_timestamp(self, obj: DataPoint) -> str:
        return localtime(obj.timestamp).isoformat()