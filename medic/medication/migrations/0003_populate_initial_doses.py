import datetime
from django.db import migrations
from django.utils import timezone


def populate_initial_doses(apps, schema_editor):
    Medication = apps.get_model("medication", "Medication")
    MedicationDose = apps.get_model("medication", "MedicationDose")

    now = timezone.now()
    today = timezone.localdate(now)
    tz = timezone.get_current_timezone()

    for med in Medication.objects.all():
        for offset in range(-2, 6):
            target_date = today + datetime.timedelta(days=offset)
            dt = datetime.datetime.combine(target_date, med.time)
            scheduled_for = timezone.make_aware(dt, tz)

            if scheduled_for < now:
                if med.taken_status:
                    dose_status = "taken"
                    taken_at = scheduled_for
                else:
                    dose_status = "missed"
                    taken_at = None
            else:
                dose_status = "pending"
                taken_at = None

            MedicationDose.objects.get_or_create(
                medication=med,
                scheduled_for=scheduled_for,
                defaults={
                    "status": dose_status,
                    "taken_at": taken_at,
                }
            )


def reverse_initial_doses(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('medication', '0002_alter_medication_taken_status_medicationdose'),
    ]

    operations = [
        migrations.RunPython(populate_initial_doses, reverse_initial_doses),
    ]
