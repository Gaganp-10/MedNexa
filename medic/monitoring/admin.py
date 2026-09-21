from django.contrib import admin
from .models import DailyHealthLog, WoundImage

admin.site.register(DailyHealthLog)
admin.site.register(WoundImage)