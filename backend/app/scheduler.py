"""
APScheduler wiring (spec Section 10) -- periodically runs the Escalation
Agent's check across every business. In-process scheduler for Phase 1;
replace with Celery + Redis at Phase 2 multi-tenant scale (per spec note).
"""
from apscheduler.schedulers.background import BackgroundScheduler

from app.agents.ledger_agent import list_all_business_ids
from app.agents.escal_agent import run_escalation_check

_scheduler = BackgroundScheduler()


def _run_escalation_for_all_businesses():
    for business_id in list_all_business_ids.invoke({}):
        run_escalation_check(business_id)


def start_scheduler():
    # Every hour is reasonable for real use. For the demo, you may want to
    # temporarily drop interval_minutes to 1-2 so you can actually see it
    # fire without waiting around -- just set it back before submitting.
    _scheduler.add_job(_run_escalation_for_all_businesses, "interval", minutes=60, id="escalation_check")
    _scheduler.start()