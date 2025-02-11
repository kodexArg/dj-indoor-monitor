from rest_framework import serializers
from django.utils.timezone import localtime
from .models import DataPoint

class DataPointSerializer(serializers.ModelSerializer):
    timestamp = serializers.SerializerMethodField()
    room = serializers.SerializerMethodField()

    class Meta:
        model = DataPoint
        fields = ['timestamp', 'sensor', 'metric', 'value', 'room']

    def get_timestamp(self, obj: DataPoint) -> str:
        return localtime(obj.timestamp).isoformat()

    def get_room(self, obj: DataPoint) -> str:
        """
        Returns the room name if include_room is True in the context, otherwise returns None.
        """
        if self.context.get('include_room'):

            sensor_room_map = self.context.get('sensor_room_map', {})
            return sensor_room_map.get(obj.sensor, '')
        return None