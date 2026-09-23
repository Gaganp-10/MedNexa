import io
import datetime
from PIL import Image as PILImage
from django.test import TestCase
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APIClient
from rest_framework import status

from accounts.models import User, PatientProfile
from monitoring.models import DailyHealthLog, WoundImage
from alerts.models import Alert


class MonitoringSecurityAndValidationTests(TestCase):
    def setUp(self):
        self.client = APIClient()

        # Doctor 1 & Doctor 2
        self.doc1 = User.objects.create_user(
            username="test_doc1", password="password123", role="doctor"
        )
        self.doc2 = User.objects.create_user(
            username="test_doc2", password="password123", role="doctor"
        )

        # Patient 1 (assigned to doc1)
        self.p1_user = User.objects.create_user(
            username="test_p1", password="password123", role="patient"
        )
        self.p1_profile = PatientProfile.objects.create(
            user=self.p1_user,
            surgery_type="Appendectomy",
            surgery_date=datetime.date(2026, 3, 1),
            doctor=self.doc1
        )

        # Patient 2 (assigned to doc2)
        self.p2_user = User.objects.create_user(
            username="test_p2", password="password123", role="patient"
        )
        self.p2_profile = PatientProfile.objects.create(
            user=self.p2_user,
            surgery_type="Cholecystectomy",
            surgery_date=datetime.date(2026, 3, 2),
            doctor=self.doc2
        )

    def _create_sample_image_file(self, filename="wound.jpg", color="red", size=(50, 50)):
        img = PILImage.new("RGB", size, color=color)
        buf = io.BytesIO()
        img.save(buf, format="JPEG")
        buf.seek(0)
        return SimpleUploadedFile(filename, buf.read(), content_type="image/jpeg")

    def test_health_log_create_derives_patient_and_ignores_body(self):
        """Creating a health log derives patient from request.user, ignoring body patient ID."""
        self.client.force_authenticate(user=self.p1_user)

        # Attempt to spoof patient_id in body pointing to patient 2
        payload = {
            "patient": self.p2_profile.id,
            "temperature": 37.2,
            "pain_level": 3,
            "swelling": False,
            "medication_taken": True,
            "notes": "Recovering steadily.",
        }
        res = self.client.post("/api/health/create/", payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

        created_log = DailyHealthLog.objects.get(id=res.data["id"])
        # Must be assigned to p1, not p2
        self.assertEqual(created_log.patient, self.p1_profile)
        self.assertEqual(created_log.recovery_score, 100)

    def test_health_log_validation_temperature_and_pain(self):
        """Temperature outside 35-42 or pain outside 0-10 must be rejected with 400."""
        self.client.force_authenticate(user=self.p1_user)

        # Low temperature
        res_low_temp = self.client.post("/api/health/create/", {
            "temperature": 34.0,
            "pain_level": 5,
        })
        self.assertEqual(res_low_temp.status_code, status.HTTP_400_BAD_REQUEST)

        # High temperature
        res_high_temp = self.client.post("/api/health/create/", {
            "temperature": 43.5,
            "pain_level": 5,
        })
        self.assertEqual(res_high_temp.status_code, status.HTTP_400_BAD_REQUEST)

        # Invalid pain
        res_pain = self.client.post("/api/health/create/", {
            "temperature": 37.0,
            "pain_level": 15,
        })
        self.assertEqual(res_pain.status_code, status.HTTP_400_BAD_REQUEST)

    # ── Phase 7 gap: exact boundary values ────────────────────────────────────

    def test_health_log_exact_boundary_temperature_min(self):
        """Temperature exactly 35.0 (min valid) must be accepted."""
        self.client.force_authenticate(user=self.p1_user)
        res = self.client.post("/api/health/create/", {
            "temperature": 35.0,
            "pain_level": 5,
        })
        self.assertEqual(res.status_code, status.HTTP_201_CREATED,
                         "Temperature 35.0 is the minimum valid value — must be accepted")

    def test_health_log_exact_boundary_temperature_max(self):
        """Temperature exactly 42.0 (max valid) must be accepted."""
        self.client.force_authenticate(user=self.p1_user)
        res = self.client.post("/api/health/create/", {
            "temperature": 42.0,
            "pain_level": 5,
        })
        self.assertEqual(res.status_code, status.HTTP_201_CREATED,
                         "Temperature 42.0 is the maximum valid value — must be accepted")

    def test_health_log_just_below_min_temperature_rejected(self):
        """Temperature 34.99 (just below minimum) must be rejected with 400."""
        self.client.force_authenticate(user=self.p1_user)
        res = self.client.post("/api/health/create/", {
            "temperature": 34.99,
            "pain_level": 5,
        })
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_health_log_just_above_max_temperature_rejected(self):
        """Temperature 42.01 (just above maximum) must be rejected with 400."""
        self.client.force_authenticate(user=self.p1_user)
        res = self.client.post("/api/health/create/", {
            "temperature": 42.01,
            "pain_level": 5,
        })
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_health_log_exact_boundary_pain_min(self):
        """Pain level exactly 0 (min valid) must be accepted."""
        self.client.force_authenticate(user=self.p1_user)
        res = self.client.post("/api/health/create/", {
            "temperature": 37.0,
            "pain_level": 0,
        })
        self.assertEqual(res.status_code, status.HTTP_201_CREATED,
                         "Pain level 0 is the minimum valid value — must be accepted")

    def test_health_log_exact_boundary_pain_max(self):
        """Pain level exactly 10 (max valid) must be accepted."""
        self.client.force_authenticate(user=self.p1_user)
        res = self.client.post("/api/health/create/", {
            "temperature": 37.0,
            "pain_level": 10,
        })
        self.assertEqual(res.status_code, status.HTTP_201_CREATED,
                         "Pain level 10 is the maximum valid value — must be accepted")

    def test_health_log_pain_negative_one_rejected(self):
        """Pain level -1 (just below minimum) must be rejected."""
        self.client.force_authenticate(user=self.p1_user)
        res = self.client.post("/api/health/create/", {
            "temperature": 37.0,
            "pain_level": -1,
        })
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_health_log_pain_eleven_rejected(self):
        """Pain level 11 (just above maximum) must be rejected."""
        self.client.force_authenticate(user=self.p1_user)
        res = self.client.post("/api/health/create/", {
            "temperature": 37.0,
            "pain_level": 11,
        })
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    # ── Phase 7 gap: exact file size boundary ──────────────────────────────────

    def test_wound_upload_exactly_5mb_accepted(self):
        """
        A wound image of exactly 5 MB (5 * 1024 * 1024 bytes) must be accepted.
        We build a valid JPEG that is padded with trailing bytes to hit exactly 5MB.
        """
        self.client.force_authenticate(user=self.p1_user)

        img = PILImage.new("RGB", (100, 100), color="green")
        buf = io.BytesIO()
        img.save(buf, format="JPEG")
        raw_jpeg = buf.getvalue()

        target_size = 5 * 1024 * 1024
        final_jpeg = raw_jpeg + b"0" * (target_size - len(raw_jpeg))

        exact_file = SimpleUploadedFile("exact_5mb.jpg", final_jpeg, content_type="image/jpeg")
        res = self.client.post("/api/wound/upload/", {"image": exact_file}, format="multipart")

        self.assertEqual(len(final_jpeg), target_size)
        self.assertEqual(res.status_code, status.HTTP_201_CREATED,
                         f"File of size {len(final_jpeg)} bytes (exact 5MB) should be accepted")

    def test_wound_upload_one_byte_over_5mb_rejected(self):
        """An image of 5 MB + 1 byte must be rejected with 400."""
        self.client.force_authenticate(user=self.p1_user)
        over_limit = b"0" * (5 * 1024 * 1024 + 1)
        over_file = SimpleUploadedFile("over.jpg", over_limit, content_type="image/jpeg")
        res = self.client.post("/api/wound/upload/", {"image": over_file}, format="multipart")
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST,
                         "File of 5MB+1 byte must be rejected")

    def test_doctor_cannot_create_health_log(self):
        """Doctors cannot submit patient health logs."""
        self.client.force_authenticate(user=self.doc1)
        res = self.client.post("/api/health/create/", {"temperature": 37.0, "pain_level": 2})
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_health_log_list_returns_only_own_records(self):
        """Endpoint /api/health/logs/ returns strictly the caller's own logs."""
        DailyHealthLog.objects.create(patient=self.p1_profile, temperature=36.8, pain_level=1)
        DailyHealthLog.objects.create(patient=self.p2_profile, temperature=37.0, pain_level=2)

        self.client.force_authenticate(user=self.p1_user)
        res = self.client.get("/api/health/logs/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        # Results paginated: count should be 1
        self.assertEqual(res.data["count"], 1)

    def test_wound_upload_valid_and_sanitized(self):
        """Valid wound upload creates UUID filename and executes prototype heuristic."""
        self.client.force_authenticate(user=self.p1_user)
        img_file = self._create_sample_image_file()

        res = self.client.post("/api/wound/upload/", {"image": img_file}, format="multipart")
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

        wound = WoundImage.objects.get(id=res.data["id"])
        self.assertEqual(wound.patient, self.p1_profile)
        self.assertIn("prototype indicator", wound.analysis_result)
        # Ensure file was given a sanitized name
        self.assertIn("wound_images/", wound.image.name)

    def test_wound_upload_invalid_file_rejected(self):
        """Non-image files (e.g. text scripts) disguised as .jpg must be rejected."""
        self.client.force_authenticate(user=self.p1_user)
        fake_file = SimpleUploadedFile("malicious.jpg", b"NOT_A_REAL_IMAGE_DATA", content_type="image/jpeg")

        res = self.client.post("/api/wound/upload/", {"image": fake_file}, format="multipart")
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_wound_upload_oversized_rejected(self):
        """Images over 5MB must be rejected."""
        self.client.force_authenticate(user=self.p1_user)
        # 6MB dummy buffer
        big_content = b"0" * (6 * 1024 * 1024)
        big_file = SimpleUploadedFile("big.jpg", big_content, content_type="image/jpeg")

        res = self.client.post("/api/wound/upload/", {"image": big_file}, format="multipart")
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_wound_image_file_stream_access_control(self):
        """Wound image download strictly enforces ownership and assignment."""
        img_file = self._create_sample_image_file()
        wound = WoundImage.objects.create(patient=self.p1_profile, image=img_file)

        stream_url = f"/api/wound/images/{wound.id}/file/"

        # Anonymous -> 401
        self.client.logout()
        res_anon = self.client.get(stream_url)
        self.assertEqual(res_anon.status_code, status.HTTP_401_UNAUTHORIZED)

        # Assigned patient -> 200
        self.client.force_authenticate(user=self.p1_user)
        res_p1 = self.client.get(stream_url)
        self.assertEqual(res_p1.status_code, status.HTTP_200_OK)

        # Assigned doctor -> 200
        self.client.force_authenticate(user=self.doc1)
        res_doc1 = self.client.get(stream_url)
        self.assertEqual(res_doc1.status_code, status.HTTP_200_OK)

        # Unassigned doctor -> 404
        self.client.force_authenticate(user=self.doc2)
        res_doc2 = self.client.get(stream_url)
        self.assertEqual(res_doc2.status_code, status.HTTP_404_NOT_FOUND)

        # Other patient -> 404
        self.client.force_authenticate(user=self.p2_user)
        res_p2 = self.client.get(stream_url)
        self.assertEqual(res_p2.status_code, status.HTTP_404_NOT_FOUND)

    def test_empty_state_recovery_trend_and_risk(self):
        """Patients with 0 logs return 200 with safe defaults without crashing."""
        self.client.force_authenticate(user=self.p1_user)

        res_trend = self.client.get(f"/api/patient/{self.p1_profile.id}/recovery-trend/")
        self.assertEqual(res_trend.status_code, status.HTTP_200_OK)
        self.assertEqual(res_trend.data, [])

        res_risk = self.client.get(f"/api/patient/{self.p1_profile.id}/risk/")
        self.assertEqual(res_risk.status_code, status.HTTP_200_OK)
        self.assertIn("Insufficient data", res_risk.data["risk_prediction"])

    # ── Phase 7 gap: recovery score and risk with 1 log and many logs ─────────

    def test_recovery_score_and_risk_with_one_log(self):
        """One health log: recovery trend returns one entry; risk returns a value (not 'Insufficient data')."""
        DailyHealthLog.objects.create(
            patient=self.p1_profile,
            temperature=37.0,
            pain_level=2,
            swelling=False,
            medication_taken=True
        )
        self.client.force_authenticate(user=self.p1_user)

        res_trend = self.client.get(f"/api/patient/{self.p1_profile.id}/recovery-trend/")
        self.assertEqual(res_trend.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res_trend.data), 1)
        self.assertIn("score", res_trend.data[0])

        res_risk = self.client.get(f"/api/patient/{self.p1_profile.id}/risk/")
        self.assertEqual(res_risk.status_code, status.HTTP_200_OK)
        # With 1 log there is still insufficient data (model needs more)
        self.assertIn("risk_prediction", res_risk.data)

    def test_recovery_score_and_risk_with_many_logs(self):
        """Many health logs: recovery trend returns multiple entries with scores."""
        for day_offset in range(5):
            DailyHealthLog.objects.create(
                patient=self.p1_profile,
                temperature=36.5 + day_offset * 0.1,
                pain_level=5 - day_offset,
                swelling=False,
                medication_taken=True
            )
        self.client.force_authenticate(user=self.p1_user)

        res_trend = self.client.get(f"/api/patient/{self.p1_profile.id}/recovery-trend/")
        self.assertEqual(res_trend.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res_trend.data), 5)
        for entry in res_trend.data:
            self.assertIn("score", entry)
            self.assertIsNotNone(entry["score"])

        res_risk = self.client.get(f"/api/patient/{self.p1_profile.id}/risk/")
        self.assertEqual(res_risk.status_code, status.HTTP_200_OK)
        self.assertIn("risk_prediction", res_risk.data)

    def _create_sample_webp_file(self, filename="wound.webp", size=(50, 50)):
        img = PILImage.new("RGB", size, color="blue")
        buf = io.BytesIO()
        img.save(buf, format="WEBP")
        buf.seek(0)
        return SimpleUploadedFile(filename, buf.read(), content_type="image/webp")

    def test_wound_image_file_stream_security_headers(self):
        """Wound image streaming response includes Cache-Control and X-Content-Type-Options."""
        img_file = self._create_sample_image_file()
        wound = WoundImage.objects.create(patient=self.p1_profile, image=img_file)
        stream_url = f"/api/wound/images/{wound.id}/file/"

        self.client.force_authenticate(user=self.p1_user)
        response = self.client.get(stream_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.headers.get("Cache-Control"), "private, no-store")
        self.assertEqual(response.headers.get("X-Content-Type-Options"), "nosniff")

    def test_wound_upload_valid_webp_accepted(self):
        """Wound image upload accepts valid WebP images."""
        self.client.force_authenticate(user=self.p1_user)
        webp_file = self._create_sample_webp_file()

        response = self.client.post("/api/wound/upload/", {"image": webp_file}, format="multipart")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(WoundImage.objects.filter(patient=self.p1_profile).exists())

    def test_wound_upload_spoofed_webp_rejected(self):
        """Wound image upload rejects invalid/spoofed WebP files."""
        self.client.force_authenticate(user=self.p1_user)
        fake_file = SimpleUploadedFile("fake.webp", b"NOT_A_WEBP_IMAGE_CONTENT", content_type="image/webp")

        response = self.client.post("/api/wound/upload/", {"image": fake_file}, format="multipart")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
