"""Onboarding content registry — maps role to content module."""

from typing import Any

_ROLE_MODULES: dict[str, Any] = {}


def _load_modules():
    if _ROLE_MODULES:
        return
    from api.onboarding_content import pm_content, ceo_content, qm_content
    from api.onboarding_content import wh_content, sp_content, purch_content
    from api.onboarding_content import admin_content, owner_content

    _ROLE_MODULES.update({
        "production_manager": pm_content,
        "ceo": ceo_content,
        "quality_manager": qm_content,
        "warehouse": wh_content,
        "sorter_packer": sp_content,
        "purchaser": purch_content,
        "administrator": admin_content,
        "owner": owner_content,
    })


def get_role_content(role: str) -> dict:
    """Return {SECTIONS, QUIZ_ANSWERS, ONBOARDING_CONTENT} for a given role."""
    _load_modules()
    mod = _ROLE_MODULES.get(role)
    if mod is None:
        return None
    return {
        "SECTIONS": mod.SECTIONS,
        "QUIZ_ANSWERS": mod.QUIZ_ANSWERS,
        "ONBOARDING_CONTENT": mod.ONBOARDING_CONTENT,
    }


def get_all_roles() -> list[str]:
    """Return list of all roles with onboarding content."""
    _load_modules()
    return list(_ROLE_MODULES.keys())
