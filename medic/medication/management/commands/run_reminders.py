import time
from django.core.management.base import BaseCommand
from django.utils import timezone
from medication.reminders import check_and_send_reminders, check_and_mark_missed_doses


class Command(BaseCommand):
    help = (
        "PROTOTYPE SCHEDULER (Dev / Demonstration only): "
        "Periodically runs medication reminder notifications and missed-dose detection. "
        "Note: Not intended for high-concurrency production (use Celery/Celery Beat in production)."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--interval",
            type=int,
            default=30,
            help="Polling interval in seconds (default: 30)."
        )
        parser.add_argument(
            "--once",
            action="store_true",
            help="Run a single pass and exit (useful for cron jobs and testing)."
        )

    def handle(self, *args, **options):
        interval = options["interval"]
        once = options["once"]

        self.stdout.write(
            self.style.SUCCESS(
                f"Starting prototype medication reminder scheduler (interval: {interval}s)..."
            )
        )

        while True:
            now = timezone.now()
            self.stdout.write(f"[{timezone.localtime(now).strftime('%Y-%m-%d %H:%M:%S')}] Checking reminders & missed doses...")

            reminders_sent = check_and_send_reminders(reference_time=now)
            missed_marked = check_and_mark_missed_doses(reference_time=now)

            if reminders_sent or missed_marked:
                self.stdout.write(
                    self.style.NOTICE(
                        f"  -> Reminders dispatched: {reminders_sent}, Doses marked missed: {missed_marked}"
                    )
                )

            if once:
                self.stdout.write(self.style.SUCCESS("Single pass completed."))
                break

            time.sleep(interval)
