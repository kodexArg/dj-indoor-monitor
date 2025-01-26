from django.contrib import admin
from .models import SiteConfiguration, Room

@admin.register(SiteConfiguration)
class SiteConfigurationAdmin(admin.ModelAdmin):
    list_display = ('key', 'value')
    search_fields = ('key', 'value')

@admin.register(Room)
class RoomAdmin(admin.ModelAdmin):
    list_display = ('name', 'sensors')
    search_fields = ('name', 'sensors')
