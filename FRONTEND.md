# MEDIC API — Lovable Frontend Integration Guide

> **Status**: Backend Phases 1–6 complete. CORS (Phase 8) not yet configured —
> see the CORS section below before attempting cross-origin requests.

---

## 1. Base API URL

```
http://<backend-host>:8000/api/
```

Replace `<backend-host>` with the IP or hostname where the Django server is running.
In local development this is typically `http://localhost:8000/api/` or `http://127.0.0.1:8000/api/`.

---

## 2. Authentication

All protected endpoints require a **Bearer JWT** in the `Authorization` header.

### Obtain Tokens

```http
POST http://localhost:8000/api/token/
Content-Type: application/json

{
  "username": "your_username",
  "password": "your_password"
}
```

Response:
```json
{
  "access":  "<short-lived JWT access token>",
  "refresh": "<long-lived JWT refresh token>"
}
```

### Refresh Access Token

```http
POST http://localhost:8000/api/token/refresh/
Content-Type: application/json

{
  "refresh": "<refresh token>"
}
```

### Using the Token

Add to every subsequent request:
```
Authorization: Bearer <access_token>
```

---

## 3. Default Request Headers

| Header | Value |
|---|---|
| `Authorization` | `Bearer <access_token>` |
| `Content-Type` | `application/json` |

**Exception**: wound image uploads must use `Content-Type: multipart/form-data` with the file field named **`image`**.

---

## 4. REST Endpoint Reference

| Method | Endpoint | Role | Description |
|---|---|---|---|
| `GET` | `/api/auth/me/` | Any | Caller identity + role metadata |
| `GET` | `/api/patient/profile/` | Patient | Patient's own profile + assigned doctor |
| `GET` | `/api/doctor/overview/` | Doctor | Dashboard overview for all assigned patients |
| `GET` | `/api/doctor/patients/` | Doctor | Paginated list of assigned patients |
| `GET` | `/api/patient/<patient_id>/logs/` | Patient/Doctor | Patient health logs |
| `POST` | `/api/health/create/` | Patient | Submit a new daily health log |
| `GET` | `/api/health/logs/` | Patient | List own health logs |
| `GET` | `/api/patient/<patient_id>/wounds/` | Patient/Doctor | Patient wound images metadata |
| `POST` | `/api/wound/upload/` | Patient | Upload wound image (multipart/form-data, field: `image`) |
| `GET` | `/api/wound/images/` | Patient | List own wound images |
| `GET` | `/api/wound/images/<id>/file/` | Patient/Doctor | Stream raw wound image file |
| `GET` | `/api/patient/<patient_id>/alerts/` | Patient/Doctor | List decision-support alerts |
| `PATCH` | `/api/alerts/<alert_id>/read/` | Doctor | Mark alert as read |
| `GET` | `/api/patient/<patient_id>/recovery-trend/` | Patient/Doctor | Recovery score history |
| `GET` | `/api/patient/<patient_id>/risk/` | Patient/Doctor | Prototype risk indicator |
| `POST` | `/api/medication/create/` | Doctor | Prescribe medication |
| `GET` | `/api/medication/<patient_id>/` | Patient/Doctor | List patient medications |
| `PATCH` | `/api/medication/<medication_id>/update/` | Patient | Legacy: mark medication taken |
| `GET` | `/api/medication/doses/today/` | Patient | Today's scheduled doses |
| `GET` | `/api/medication/doses/upcoming/?days=7` | Patient | Upcoming doses |
| `PATCH` | `/api/medication/doses/<dose_id>/take/` | Patient | Mark a dose as taken |
| `GET` | `/api/patient/<patient_id>/medication-adherence/?days=7` | Patient/Doctor | Adherence summary |
| `GET` | `/api/communication/conversations/` | Any | List caller's conversations |
| `POST` | `/api/communication/conversations/` | Any | Create conversation (body: `patient_id`, optional `content`) |
| `GET` | `/api/communication/conversations/<id>/messages/` | Any | Message history (oldest-first) |
| `POST` | `/api/communication/conversations/<id>/messages/` | Any | Send message — see note below |
| `PATCH` | `/api/communication/messages/<id>/read/` | Recipient only | Mark message as read |

> **Note on POST /communication/conversations/\<id\>/messages/**: The `<id>` path parameter is dual-purpose:
> - **First message** (no conversation exists yet): pass the **`PatientProfile.id`** — the conversation is auto-created server-side.
> - **Subsequent messages**: pass the **`Conversation.id`** from the conversations list.
>
> To avoid ambiguity, the recommended flow is:
> 1. `GET /api/communication/conversations/` — check if a conversation exists.
> 2. If yes: `POST /api/communication/conversations/<conversation_id>/messages/`
> 3. If no: `POST /api/communication/conversations/<patient_profile_id>/messages/` (auto-creates on first send)

---

## 5. `<patient_id>` Path Parameter

Wherever `<patient_id>` appears in a URL, it refers to **`PatientProfile.id`** (the primary key of the PatientProfile record), **not** `User.id`. Retrieve this from:
- `GET /api/auth/me/` → `patient_profile_id` (for patients)
- `GET /api/doctor/patients/` → `id` field on each patient record (for doctors)

---

## 6. Real-Time WebSocket Channels

WebSockets authenticate via a JWT passed as a **query string parameter**.

> ⚠️ Never hardcode relative WebSocket paths. Always use absolute URLs.

### Doctor Alert Channel
```
ws://<backend-host>:8000/ws/alerts/?token=<access_token>
```
- Connect as: authenticated doctor with an active DoctorProfile
- Closed with 4403 if caller is not a doctor
- Receives: vital threshold alerts, missed-dose alerts, and new patient chat messages

**Incoming payload shape:**
```json
{
  "id": 12,
  "patient_id": 3,
  "patient_display_name": "Jane Doe",
  "severity": "high",
  "message": "High fever detected: 39.5 C",
  "created_at": "2026-03-24T10:00:00+05:30"
}
```

### Patient Notification Channel
```
ws://<backend-host>:8000/ws/notifications/?token=<access_token>
```
- Connect as: authenticated patient with an active PatientProfile
- Closed with 4403 if caller is not a patient
- Receives: medication dose reminders and new doctor chat message alerts

**Incoming payload shape (medication reminder):**
```json
{
  "type": "medication_reminder",
  "dose_id": 45,
  "medicine_name": "Amoxicillin",
  "dosage": "500mg",
  "scheduled_time": "08:00 PM",
  "message": "Time for Amoxicillin (500mg) at 08:00 PM.",
  "created_at": "2026-03-24T19:55:00+05:30"
}
```

**Incoming payload shape (new chat message alert):**
```json
{
  "type": "chat_message",
  "conversation_id": 1,
  "message_id": 101,
  "sender_name": "Dr. John Smith",
  "preview": "Remember to take your antibiotic at 8 PM.",
  "created_at": "2026-03-24T20:00:00+05:30"
}
```

### Doctor-Patient Chat Channel
```
ws://<backend-host>:8000/ws/chat/<conversation_id>/?token=<access_token>
```
- Connect as: the doctor or patient in that specific conversation
- Closed with 4401 if token is missing/invalid
- Closed with 4403 if caller is not an active participant, or if doctor is no longer assigned

**Send message (client → server):**
```json
{"content": "How are you feeling today?"}
```

**Receive message (server → client broadcast):**
```json
{
  "id": 101,
  "conversation_id": 1,
  "sender_id": 2,
  "sender_name": "Dr. John Smith",
  "sender_role": "doctor",
  "content": "How are you feeling today?",
  "is_read": false,
  "created_at": "2026-03-24T10:15:00+05:30"
}
```

---

## 7. CORS Status ⚠️

**CORS headers are NOT currently configured (Phase 8).** This means cross-origin HTTP requests from a Lovable-hosted frontend will be blocked by browsers with a CORS error when connecting to this backend.

**Options for local development before Phase 8:**
- Run the frontend on the same origin as the backend (same host:port).
- Use a reverse proxy (e.g., Vite's `server.proxy`) to proxy `/api/` to the backend.
- Temporarily enable CORS in settings using `django-cors-headers` pointing at the Lovable dev origin.

**Phase 8 will configure:** `CORS_ALLOWED_ORIGINS` including the Lovable production domain, credentials support, and any required WebSocket origin headers.

---

## 8. API Documentation

- **Interactive Swagger UI**: `http://localhost:8000/api/docs/`
- **Raw OpenAPI schema (YAML/JSON)**: `http://localhost:8000/api/schema/`

> ⚠️ **Production Note**: Swagger UI is publicly accessible in development.
> Before production deployment, restrict it by setting `SERVE_PERMISSIONS` to
> `['rest_framework.permissions.IsAdminUser']` in `SPECTACULAR_SETTINGS`.

---

## 9. Timestamps

All timestamps are **timezone-aware** and localized to **Asia/Kolkata (IST, UTC+5:30)**.
Store and display accordingly in the frontend.
