# MedNexa — Post-Surgery Monitoring Backend

> ⚠️ **MEDICAL SAFETY NOTICE**: This is a prototype clinical decision-support tool, NOT a diagnostic system. Outputs such as risk indicators, vital threshold alerts, and wound analysis are prototype heuristics and are NOT clinically validated diagnostic findings. They are designed exclusively to prompt clinical review by the assigned healthcare team.

---

## Overview

MedNexa is a Django/Channels REST + WebSocket API backend for post-operative patient monitoring. It supports:

- Doctor-patient assignment and role-based access control
- Daily health logs with automated recovery scoring
- Wound image upload with prototype computer-vision analysis
- Medication scheduling, dose tracking, and reminder push notifications
- Real-time alert broadcasting to the assigned doctor
- Doctor-patient live chat via WebSocket
- Comprehensive OpenAPI documentation at `/api/docs/`

**Frontend**: Built separately in Lovable (React/Vite). See [`FRONTEND.md`](FRONTEND.md) for the full integration guide.

---

## Setup from a Fresh Clone

### 1. Clone and create virtual environment

```bash
git clone https://github.com/Gaganp-10/MedNexa.git
cd MedNexa
python -m venv venv
```

Activate:
- **Windows**: `venv\Scripts\activate`
- **Linux/macOS**: `source venv/bin/activate`

### 2. Install dependencies

```bash
pip install -r medic/requirements.txt
```

### 3. Configure environment variables

```bash
cp .env.example .env
```

Edit `.env` with your values. The project runs with **zero `.env` file** using safe dev defaults (SQLite, `DEBUG=True`, InMemory channel layer). You only need a `.env` for production or to override specific values.

Key variables (see `.env.example` for the full list):

| Variable | Dev default | Description |
|---|---|---|
| `SECRET_KEY` | Insecure dev key | Django secret key — **must** be changed in production |
| `DEBUG` | `True` | Set `False` in production |
| `ALLOWED_HOSTS` | `localhost,127.0.0.1` | Comma-separated allowed hosts |
| `DATABASE_URL` | SQLite | PostgreSQL connection string |
| `REDIS_URL` | InMemory | Redis URL for WebSocket channel layer |
| `CORS_ALLOWED_ORIGINS` | localhost:5173, 3000 | Comma-separated frontend origins |

> ⚠️ **Production**: Generate a new `SECRET_KEY` with:
> ```bash
> python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
> ```
> The hardcoded dev key has been retired as of Phase 8.

### 4. Run database migrations

```bash
cd medic
python manage.py migrate
```

### 5. Seed demo data (dev only)

```bash
python manage.py seed_demo
```

Creates demo accounts for local testing:

| Role | Username | Password |
|---|---|---|
| Doctor | `demo_doctor` | `DemoPass123!` |
| Patient | `demo_patient` | `DemoPass123!` |

> `seed_demo` refuses to run when `DEBUG=False`.

---

## Running the Development Server

### HTTP only (REST API, no WebSockets)

```bash
# From medic/
python manage.py runserver
```

The API is available at `http://localhost:8000/`.

### HTTP + WebSockets (full stack)

WebSockets require an **ASGI server**. Use Daphne:

```bash
# From medic/
daphne -b 0.0.0.0 -p 8000 medic.asgi:application
```

Or with auto-reload during development:

```bash
daphne -b 127.0.0.1 -p 8000 medic.asgi:application
```

> `python manage.py runserver` uses Django's built-in WSGI server which does NOT support WebSockets. Use Daphne or Uvicorn for all WebSocket functionality.

---

## Running the Reminder Scheduler

The medication reminder scheduler must be run separately (it is a long-running management command):

```bash
# From medic/
python manage.py run_reminders
```

This polls for upcoming doses every 60 seconds and fires reminder push notifications to patients via the WebSocket notification channel. Run it as a background process or system service in production.

---

## Running Tests

```bash
# From medic/
python manage.py test
```

All 70+ tests must pass. The test suite uses:
- In-Memory channel layer (no Redis required)
- MD5 password hasher (faster hashing in tests)
- SQLite test database (auto-created and destroyed)

To run a specific app's tests:

```bash
python manage.py test accounts
python manage.py test alerts
python manage.py test communication
python manage.py test medication
python manage.py test monitoring
python manage.py test medic
```

---

## API Documentation

| URL | Description |
|---|---|
| `http://localhost:8000/api/docs/` | Interactive Swagger UI |
| `http://localhost:8000/api/schema/` | Raw OpenAPI schema (YAML) |
| `http://localhost:8000/health/` | System health check (public) |

> ⚠️ **Production**: Restrict Swagger UI to admins by setting `SERVE_PERMISSIONS` in `SPECTACULAR_SETTINGS` to `['rest_framework.permissions.IsAdminUser']`.

For the full endpoint reference, WebSocket URLs, payload shapes, and Lovable integration instructions, see [`FRONTEND.md`](FRONTEND.md).

---

## Project Structure

```
MedNexa/
├── .env.example          ← Environment variable template
├── FRONTEND.md           ← Lovable frontend integration guide
├── README.md             ← This file
└── medic/                ← Django project root
    ├── requirements.txt
    ├── manage.py
    ├── medic/            ← Django settings package
    │   ├── settings.py   ← Env-var-driven settings (Phase 8)
    │   ├── urls.py
    │   └── asgi.py
    ├── accounts/         ← User, DoctorProfile, PatientProfile, auth
    ├── monitoring/       ← DailyHealthLog, WoundImage, recovery/risk
    ├── medication/       ← Medication, MedicationDose, reminders
    ├── alerts/           ← Alert model, threshold analysis, WebSocket dispatch
    ├── communication/    ← Conversation, Message, chat WebSocket
    └── tools/            ← Management commands (seed_demo, run_reminders)
```

---

## Architecture Notes

- **Auth**: JWT Bearer tokens via `djangorestframework-simplejwt`. Access token: 30 min. Refresh: 7 days (rotates on use).
- **Authorization**: All patient-scoped endpoints return 404 (not 403) for unauthorized access to prevent existence enumeration. Central helper: `accounts/access.py`.
- **WebSockets**: Three consumers — `ws/alerts/`, `ws/notifications/`, `ws/chat/<conv_id>/`. All authenticate via `?token=<jwt>`. Invalid/expired → 4401. Wrong role/non-participant → 4403.
- **CORS**: Configured via `django-cors-headers`. Origins from `CORS_ALLOWED_ORIGINS` env var. WebSocket origins validated by `AllowedHostsOriginValidator` — add the Lovable domain to `ALLOWED_HOSTS` in production.
- **Throttling**: Login endpoint (`/api/token/`) limited to 5 requests/minute to mitigate brute-force attacks.
- **Logging**: Structured to stdout (`[timestamp] [level] [logger] message`). Never logs tokens, passwords, or PHI.

---

## Medical Safety Disclaimer

This application is a **prototype decision-support tool** for clinical review workflows. It is NOT a diagnostic system. Outputs including recovery scores, risk indicators, vital threshold alerts, and wound analysis are heuristic indicators designed to prompt clinician attention — they are NOT clinically validated and must NOT be used as a substitute for professional medical judgment.