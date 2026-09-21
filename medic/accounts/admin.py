from django.contrib import admin
from .models import User, DoctorProfile, PatientProfile

admin.site.register(User)
admin.site.register(DoctorProfile)
admin.site.register(PatientProfile)