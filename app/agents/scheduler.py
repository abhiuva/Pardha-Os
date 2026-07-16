from __future__ import annotations

import logging
import os
import inspect
from datetime import datetime, timezone
from typing import Callable
from uuid import uuid4

from apscheduler.schedulers.background import BackgroundScheduler

from app.agents.ceo import generate_daily_brief
from app.agents.cto import generate_cto_brief
from app.agents.executions import complete_execution, start_execution
from app.agents.pm import generate_pm_brief


logger = logging.getLogger(__name__)
EXECUTION_INTERVAL_MINUTES = 5
AGENT_WORKFLOW: tuple[tuple[str, Callable], ...] = (
    ("ceo", generate_daily_brief),
    ("cto", generate_cto_brief),
    ("pm", generate_pm_brief),
)

scheduler: BackgroundScheduler | None = None


def _serialize_output(output) -> dict:
    if hasattr(output, "model_dump"):
        return output.model_dump(mode="json")
    return output.dict()


def run_agent_cycle() -> None:
    from app.business.service import get_active_business

    business = get_active_business()
    cycle_id = str(uuid4())
    for agent_name, generate_output in AGENT_WORKFLOW:
        execution_id = start_execution(agent_name, cycle_id, business_id=business.business_id)
        try:
            if "business_id" in inspect.signature(generate_output).parameters:
                output = generate_output(business_id=business.business_id)
            else:
                output = generate_output()
            complete_execution(
                execution_id,
                status="succeeded",
                output=_serialize_output(output),
            )
        except Exception as exc:
            logger.exception("%s agent execution failed for %s", agent_name.upper(), business.business_name)
            complete_execution(execution_id, status="failed", error=str(exc))


def start_scheduler() -> None:
    global scheduler
    enabled = os.getenv("PARDHA_SCHEDULER_ENABLED", "true").lower() not in {"0", "false", "no"}
    if not enabled or (scheduler is not None and scheduler.running):
        return

    scheduler = BackgroundScheduler(timezone="UTC")
    scheduler.add_job(
        run_agent_cycle,
        trigger="interval",
        minutes=EXECUTION_INTERVAL_MINUTES,
        id="pardha-agent-cycle",
        replace_existing=True,
        coalesce=True,
        max_instances=1,
        next_run_time=datetime.now(timezone.utc),
    )
    scheduler.start()


def stop_scheduler() -> None:
    global scheduler
    if scheduler is not None and scheduler.running:
        scheduler.shutdown(wait=False)
    scheduler = None


def scheduler_status() -> str:
    if scheduler is None:
        return "stopped"
    return "running" if scheduler.running else "stopped"
