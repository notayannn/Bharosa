from apscheduler.schedulers.background import BackgroundScheduler
from app.agents.ledger_agent import list_all_business_ids
from app.agents.escal_agent import run_escalation_check

_scheduler = BackgroundScheduler()

def _run_escalation_for_all_businesses():
    for business_id in list_all_business_ids.invoke({}):
        run_escalation_check(business_id)


def start_scheduler():

    _scheduler.add_job(_run_escalation_for_all_businesses, "interval", minutes=60, id="escalation_check")
    _scheduler.start()