"""
Per-kiln loading rules (JSONB-based).
See BUSINESS_LOGIC.md §30 for per-kiln rules.
"""
from uuid import UUID
from typing import Optional

from sqlalchemy.orm import Session


def get_loading_rules(db: Session, kiln_id: UUID) -> dict:
    """Load per-kiln JSONB rules from kiln_loading_rules table."""
    # TODO: implement — see BUSINESS_LOGIC.md §30
    raise NotImplementedError


def validate_cofiring(db: Session, positions: list, kiln_id: UUID) -> dict:
    """
    Validate co-firing compatibility.
    Check temperature restrictions from glaze recipes.
    See BUSINESS_LOGIC.md §31.
    """
    # TODO: implement — see BUSINESS_LOGIC.md §31
    raise NotImplementedError


def get_rotation_rules(db: Session, factory_id: UUID) -> dict:
    """
    Get configurable rotation rules per factory.
    See BUSINESS_LOGIC.md §37.
    """
    # TODO: implement — see BUSINESS_LOGIC.md §37
    raise NotImplementedError
