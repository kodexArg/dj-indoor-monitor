from django.contrib import admin
from .models import SiteConfigurations, Room, Sensor

admin.site.register(SiteConfigurations)
admin.site.register(Room)
admin.site.register(Sensor)

