from django.contrib import admin

from .models import GeoPoint


@admin.register(GeoPoint)
class GeoPointAdmin(admin.ModelAdmin):
    list_display = ['address', 'lon', 'lat', 'last_updated']
    search_fields = ['address']
    readonly_fields = ['last_updated']
