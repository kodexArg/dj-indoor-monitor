from rest_framework import serializers
from django.utils.timezone import localtime
from .models import DataPoint

# Removed BaseDataPointSerializer; each serializer now implements its own timestamp field.

class DataPointSerializer(serializers.ModelSerializer):
    timestamp = serializers.SerializerMethodField()
    
    def get_timestamp(self, obj):
        return localtime(obj.timestamp).isoformat()
    
    class Meta:
        model = DataPoint
        fields = ['timestamp', 'sensor', 'metric', 'value']

class DataPointRoomSerializer(serializers.ModelSerializer):
    timestamp = serializers.SerializerMethodField()
    room = serializers.SerializerMethodField()
    
    def get_timestamp(self, obj):
        return localtime(obj.timestamp).isoformat()
    
    def get_room(self, obj):
        sensor_room_map = self.context.get('sensor_room_map', {})
        return sensor_room_map.get(obj.sensor, '')
    
    class Meta:
        model = DataPoint
        fields = ['timestamp', 'room', 'metric', 'value']

class DataPointRoomSensorSerializer(serializers.ModelSerializer):
    timestamp = serializers.SerializerMethodField()
    room = serializers.SerializerMethodField()
    
    def get_timestamp(self, obj):
        return localtime(obj.timestamp).isoformat()
    
    def get_room(self, obj):
        sensor_room_map = self.context.get('sensor_room_map', {})
        return sensor_room_map.get(obj.sensor, '')
    
    class Meta:
        model = DataPoint
        fields = ['timestamp', 'room', 'sensor', 'metric', 'value']