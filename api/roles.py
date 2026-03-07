"""
Moonjar PMS — Role-based access control.
"""

from functools import wraps
from fastapi import Depends, HTTPException, status

from api.auth import get_current_user


def require_role(*allowed_roles: str):
    """FastAPI dependency: restrict endpoint to specific roles."""
    async def dependency(current_user=Depends(get_current_user)):
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{current_user.role}' not allowed. Required: {', '.join(allowed_roles)}",
            )
        return current_user
    return dependency


# Convenience shortcuts
require_owner = require_role("owner")
require_admin = require_role("owner", "administrator")
require_management = require_role("owner", "administrator", "ceo", "production_manager")
require_quality = require_role("owner", "administrator", "quality_manager")
require_warehouse = require_role("owner", "administrator", "warehouse")
require_sorting = require_role("owner", "administrator", "production_manager", "sorter_packer")
require_any = require_role(
    "owner", "administrator", "ceo", "production_manager",
    "quality_manager", "warehouse", "sorter_packer", "purchaser",
)
