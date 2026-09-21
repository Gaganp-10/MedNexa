from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):

    ROLE_CHOICES = (
        ('doctor', 'Doctor'),
        ('patient', 'Patient'),
    )

    role = models.CharField(max_length=10, choices=ROLE_CHOICES)

class DoctorProfile(models.Model):

    user = models.OneToOneField(User, on_delete=models.CASCADE)

    specialization = models.CharField(max_length=200)


class PatientProfile(models.Model):

    user = models.OneToOneField(User, on_delete=models.CASCADE)

    surgery_type = models.CharField(max_length=200)

    surgery_date = models.DateField()

    doctor = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name="patients"
    )