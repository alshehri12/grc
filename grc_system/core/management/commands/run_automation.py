"""
Run the GRC automation jobs without Celery.

    python manage.py run_automation              # run every job once
    python manage.py run_automation --list       # show available jobs
    python manage.py run_automation --job expire_evidence --job snapshot_kpis

Schedule it from cron (e.g. every 15 minutes) when a Celery worker/beat is
not available; the jobs are idempotent so overlapping runs are harmless.
"""
import json

from django.core.management.base import BaseCommand, CommandError

from core.automation import JOBS, run_all


class Command(BaseCommand):
    help = 'Run GRC automation jobs (reminders, escalations, expiries, recalculations, delivery).'

    def add_arguments(self, parser):
        parser.add_argument('--job', action='append', dest='jobs', help='Run only this job (repeatable).')
        parser.add_argument('--list', action='store_true', help='List available jobs and exit.')
        parser.add_argument('--json', action='store_true', help='Print results as JSON.')

    def handle(self, *args, **opts):
        if opts['list']:
            for name, fn in JOBS.items():
                self.stdout.write(f'{name:<32} {(fn.__doc__ or "").strip().splitlines()[0] if fn.__doc__ else ""}')
            return
        unknown = [j for j in (opts['jobs'] or []) if j not in JOBS]
        if unknown:
            raise CommandError(f'Unknown job(s): {", ".join(unknown)}. Use --list to see available jobs.')

        results = run_all(only=opts['jobs'])
        if opts['json']:
            self.stdout.write(json.dumps(results, indent=2, default=str))
            return
        for r in results:
            if r['ok']:
                self.stdout.write(self.style.SUCCESS(f"✓ {r['job']:<30} {r['result']}  ({r['seconds']}s)"))
            else:
                self.stdout.write(self.style.ERROR(f"✗ {r['job']:<30} {r['error']}"))
        if any(not r['ok'] for r in results):
            raise CommandError('One or more automation jobs failed.')
