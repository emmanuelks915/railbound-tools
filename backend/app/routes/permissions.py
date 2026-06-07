from __future__ import annotations

from fastapi import APIRouter, Depends

from app.permissions import is_staff
from app.security import actor_from_header

router = APIRouter(prefix="/api/auth", tags=["permissions"])


STAFF_TABS = {"staff", "qa", "beast_skills"}
STAFF_RECOMMENDED_TABS = {"activity"}

PLAYER_TABS = [
    "dashboard",
    "planner",
    "oc",
    "inventory",
    "manage_oc",
    "register",
    "registry",
    "skills",
    "shops",
    "rp",
    "missions",
    "companion",
]


def _is_admin(actor_discord_id: int | None) -> bool:
    if actor_discord_id is None:
        return False
    return is_staff(int(actor_discord_id))


@router.get("/permissions")
def get_permissions(actor_discord_id: int | None = Depends(actor_from_header)):
    if actor_discord_id is None:
        return {
            "discord_id": None,
            "is_logged_in": False,
            "is_staff": False,
            "is_admin": False,
            "allowed_tabs": [],
            "staff_tabs": sorted(STAFF_TABS),
            "staff_recommended_tabs": sorted(STAFF_RECOMMENDED_TABS),
        }

    staff = is_staff(int(actor_discord_id))
    admin = _is_admin(actor_discord_id)

    allowed_tabs = list(PLAYER_TABS)
    if staff:
        allowed_tabs.extend(sorted(STAFF_TABS))
        allowed_tabs.extend(sorted(STAFF_RECOMMENDED_TABS))

    # Check if this player owns any shops
    from app.supabase_client import get_supabase
    from app.services import get_guild_id, sb_data
    try:
        sb = get_supabase()
        shop_rows = (sb_data(sb.table("shops").select("shop_id").eq("owner_discord_id", str(actor_discord_id)).eq("guild_id", get_guild_id()).limit(1).execute()) or [])
        if not shop_rows:
            shop_rows = (sb_data(sb.table("shops").select("shop_id").eq("owner_discord_id", str(actor_discord_id)).limit(1).execute()) or [])
        is_shop_owner = len(shop_rows) > 0
    except Exception:
        is_shop_owner = False

    if is_shop_owner or staff:
        allowed_tabs.append("shop_owner")

    return {
        "discord_id": str(actor_discord_id),
        "is_logged_in": True,
        "is_staff": staff,
        "is_admin": admin,
        "is_shop_owner": is_shop_owner,
        "allowed_tabs": allowed_tabs,
        "staff_tabs": sorted(STAFF_TABS),
        "staff_recommended_tabs": sorted(STAFF_RECOMMENDED_TABS),
    }
