"""
Batch optimization — maximize kiln utilization.
TOC principle: the constraint (kiln) must never be idle.
"""
from uuid import UUID

from sqlalchemy.orm import Session


def optimize_batch_fill(db: Session, batch_id: UUID) -> dict:
    """
    Find additional positions that can fill remaining batch capacity.
    Considers: size compatibility, co-firing rules, priority.
    """
    # TODO: implement
    raise NotImplementedError


def calculate_kiln_utilization(db: Session, factory_id: UUID, period_days: int = 30) -> dict:
    """
    Calculate kiln utilization metrics for analytics.
    Returns: {kiln_id: {firings, avg_fill_pct, idle_days}}
    """
    # TODO: implement
    raise NotImplementedError
