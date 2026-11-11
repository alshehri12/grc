"""
Celery tasks: thin wrappers around core.automation jobs.

The schedule lives in settings.CELERY_BEAT_SCHEDULE (django-celery-beat's
DatabaseScheduler imports it on start-up). Without Celery, run the same jobs
with `python manage.py run_automation`.
"""
from celery import shared_task

from core.automation import JOBS, run_all, run_job


def _make_task(job_name):
    @shared_task(name=f'grc.automation.{job_name}', bind=True, max_retries=2)
    def _task(self):
        result = run_job(job_name)
        if not result['ok']:
            raise self.retry(countdown=300)
        return result
    _task.__doc__ = JOBS[job_name].__doc__
    return _task


# One Celery task per automation job, e.g. grc.automation.expire_evidence
TASKS = {name: _make_task(name) for name in JOBS}
globals().update({f'task_{name}': task for name, task in TASKS.items()})


@shared_task(name='grc.automation.run_all')
def run_all_automation():
    """Run every automation job in sequence (useful for a single nightly schedule)."""
    return run_all()


# Backwards-compatible names used by older code / docs
check_overdue_approvals = TASKS['escalate_overdue_approvals']
send_reminder_notifications = TASKS['remind_upcoming_approvals']
process_escalations = TASKS['process_escalations']
update_overdue_task_status = TASKS['mark_overdue_items']
