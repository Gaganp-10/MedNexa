"""
Celery Task Definitions for Medication Reminders (Production Path).

Configured for production scheduling with Celery Beat.
Celery is optional and not required for local development or the test suite.
"""
import logging
from django.utils import timezone
from .reminders import check_and_send_reminders, check_and_mark_missed_doses

logger = logging.getLogger(__name__)

try:
    from celery import shared_task
except ImportError:
    # Fallback dummy decorator when Celery is not installed in development
    def shared_task(func):
        return func


@shared_task
def send_medication_reminders_task():
    """
    Periodic task to check and dispatch medication reminders for upcoming doses.
    Typically scheduled to run every 1 to 5 minutes via Celery Beat.
    """
    count = check_and_send_reminders(reference_time=timezone.now())
    logger.info("Celery task dispatched %d medication reminder(s)", count)
    return count


@shared_task
def mark_missed_doses_task():
    """
    Periodic task to evaluate pending doses past their grace period and record them as missed.
    Typically scheduled to run every 10 to 15 minutes via Celery Beat.
    """
    count = check_and_mark_missed_doses(reference_time=timezone.now(), grace_period_hours=2)
    logger.info("Celery task marked %d dose(s) as missed", count)
    return count
