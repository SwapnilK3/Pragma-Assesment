from django.contrib import admin
from core.models import Address, MediaFile

# Register core models (concrete only)
admin.site.register([Address, MediaFile])
