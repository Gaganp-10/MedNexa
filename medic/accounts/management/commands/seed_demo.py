import datetime
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from accounts.models import User, DoctorProfile, PatientProfile
from monitoring.models import DailyHealthLog
from medication.models import Medication
from alerts.services import analyze_health_log
from monitoring.recovery_score import calculate_recovery_score


class Command(BaseCommand):
    help = "Seeds demo doctors, assigned patients, health logs, and medications (dev only)."

    def handle(self, *args, **options):
        if not settings.DEBUG:
            raise CommandError("seed_demo can only be run when DEBUG is True.")

        self.stdout.write(self.style.NOTICE("Seeding MEDIC demo dataset..."))

        # 1. Doctors
        doc1, _ = User.objects.get_or_create(
            username="dr_smith",
            defaults={
                "email": "dr.smith@medic-demo.local",
                "first_name": "Alice",
                "last_name": "Smith",
                "role": "doctor",
                "is_staff": True,
            }
        )
        doc1.set_password("DoctorPass123!")
        doc1.save()
        DoctorProfile.objects.update_or_create(
            user=doc1,
            defaults={"specialization": "Cardiothoracic Surgery"}
        )

        doc2, _ = User.objects.get_or_create(
            username="dr_patel",
            defaults={
                "email": "dr.patel@medic-demo.local",
                "first_name": "Rajesh",
                "last_name": "Patel",
                "role": "doctor",
                "is_staff": True,
            }
        )
        doc2.set_password("DoctorPass123!")
        doc2.save()
        DoctorProfile.objects.update_or_create(
            user=doc2,
            defaults={"specialization": "Orthopedic Surgery"}
        )

        # 2. Patients
        # Patient 1: Alice Johnson -> assigned to dr_smith
        p1_user, _ = User.objects.get_or_create(
            username="patient_alice",
            defaults={
                "email": "alice.johnson@patient.local",
                "first_name": "Alice",
                "last_name": "Johnson",
                "role": "patient",
            }
        )
        p1_user.set_password("PatientPass123!")
        p1_user.save()
        p1_profile, _ = PatientProfile.objects.update_or_create(
            user=p1_user,
            defaults={
                "surgery_type": "Appendectomy",
                "surgery_date": datetime.date(2026, 3, 1),
                "doctor": doc1,
            }
        )

        # Patient 2: Bob Williams -> assigned to dr_patel
        p2_user, _ = User.objects.get_or_create(
            username="patient_bob",
            defaults={
                "email": "bob.williams@patient.local",
                "first_name": "Bob",
                "last_name": "Williams",
                "role": "patient",
            }
        )
        p2_user.set_password("PatientPass123!")
        p2_user.save()
        p2_profile, _ = PatientProfile.objects.update_or_create(
            user=p2_user,
            defaults={
                "surgery_type": "Knee Arthroplasty",
                "surgery_date": datetime.date(2026, 3, 5),
                "doctor": doc2,
            }
        )

        # Patient 3: Charlie Davis -> assigned to dr_smith (Empty-state test patient with 0 logs initially)
        p3_user, _ = User.objects.get_or_create(
            username="patient_charlie",
            defaults={
                "email": "charlie.davis@patient.local",
                "first_name": "Charlie",
                "last_name": "Davis",
                "role": "patient",
            }
        )
        p3_user.set_password("PatientPass123!")
        p3_user.save()
        p3_profile, _ = PatientProfile.objects.update_or_create(
            user=p3_user,
            defaults={
                "surgery_type": "Laparoscopic Cholecystectomy",
                "surgery_date": datetime.date(2026, 3, 10),
                "doctor": doc1,
            }
        )

        # 3. Medications
        from medication.services import generate_upcoming_doses

        m1, _ = Medication.objects.update_or_create(
            patient=p1_profile,
            medicine_name="Amoxicillin",
            defaults={"dosage": "500mg", "time": datetime.time(8, 0), "taken_status": True}
        )
        generate_upcoming_doses(m1, days=7)

        m2, _ = Medication.objects.update_or_create(
            patient=p1_profile,
            medicine_name="Paracetamol",
            defaults={"dosage": "1000mg", "time": datetime.time(14, 0), "taken_status": False}
        )
        generate_upcoming_doses(m2, days=7)

        m3, _ = Medication.objects.update_or_create(
            patient=p2_profile,
            medicine_name="Ibuprofen",
            defaults={"dosage": "400mg", "time": datetime.time(9, 0), "taken_status": True}
        )
        generate_upcoming_doses(m3, days=7)

        # 4. Sample Health Logs for Patient Alice
        if not DailyHealthLog.objects.filter(patient=p1_profile).exists():
            log1 = DailyHealthLog(
                patient=p1_profile,
                temperature=37.8,
                pain_level=6,
                swelling=True,
                medication_taken=True,
                notes="Mild discomfort around incision."
            )
            log1.recovery_score = calculate_recovery_score(log1, "Normal visual variation; routine observation recommended (prototype indicator)")
            log1.save()
            analyze_health_log(log1)

            log2 = DailyHealthLog(
                patient=p1_profile,
                temperature=36.8,
                pain_level=2,
                swelling=False,
                medication_taken=True,
                notes="Feeling significantly better today."
            )
            log2.recovery_score = calculate_recovery_score(log2, "Normal visual variation; routine observation recommended (prototype indicator)")
            log2.save()

        # Sample Health Log for Patient Bob (Triggers decision-support alerts)
        if not DailyHealthLog.objects.filter(patient=p2_profile).exists():
            log_bob = DailyHealthLog(
                patient=p2_profile,
                temperature=38.4,
                pain_level=9,
                swelling=True,
                medication_taken=False,
                notes="Severe knee throbbing and warmth."
            )
            log_bob.recovery_score = calculate_recovery_score(log_bob, "")
            log_bob.save()
            analyze_health_log(log_bob)

        self.stdout.write(self.style.SUCCESS("Demo database successfully seeded!\n"))
        self.stdout.write(self.style.WARNING("================ DEMO CREDENTIALS ================"))
        self.stdout.write("DOCTOR 1 (dr_smith):     dr_smith / DoctorPass123!   [Cardiothoracic, Assigned: Alice, Charlie]")
        self.stdout.write("DOCTOR 2 (dr_patel):     dr_patel / DoctorPass123!   [Orthopedics,    Assigned: Bob]")
        self.stdout.write("PATIENT 1 (Alice):       patient_alice / PatientPass123! [Assigned to dr_smith - Has logs]")
        self.stdout.write("PATIENT 2 (Bob):         patient_bob / PatientPass123!   [Assigned to dr_patel - High fever/pain]")
        self.stdout.write("PATIENT 3 (Charlie):     patient_charlie / PatientPass123! [Assigned to dr_smith - Empty state]")
        self.stdout.write(self.style.WARNING("=================================================="))
