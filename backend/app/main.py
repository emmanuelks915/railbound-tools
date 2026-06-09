from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.routes import (
    loadouts,
    characters,
    combat,
    dashboard,
    inventory,
    skills,
    staff,
    xp,
    rp,
    activity,
    auth,
    registry,
    oc_registration,
    oc_balances,
    oc_management,
    activity_log,
    permissions,
    request_workflow,
    market,
    shop_owner,
    character_self,
    companions,
    discord_roles,
    staff_maintenance,
    missions,
    source_beast_skills,
    weather,
)

settings = get_settings()

app = FastAPI(
    title="Railbound Tools API",
    version="0.1.0",
    description="Railbound XP planner, stat requests, staff approvals, and calculator tools.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(characters.router)
app.include_router(dashboard.router)
app.include_router(xp.router)
app.include_router(staff.router)
app.include_router(combat.router)
app.include_router(inventory.router)
# shops.router removed — legacy /api/shops replaced by /api/market + /api/shop-owner
app.include_router(skills.router)
app.include_router(rp.router)
app.include_router(activity.router)
app.include_router(auth.router)
app.include_router(registry.router)
app.include_router(oc_registration.router)
app.include_router(oc_balances.router)
app.include_router(oc_management.router)
app.include_router(activity_log.router)
app.include_router(permissions.router)
app.include_router(request_workflow.router)
app.include_router(market.router)
app.include_router(loadouts.router)
app.include_router(shop_owner.router)
app.include_router(character_self.router)
app.include_router(discord_roles.router)
app.include_router(staff_maintenance.router)
app.include_router(missions.router)
app.include_router(companions.router)
app.include_router(source_beast_skills.router)
app.include_router(weather.router)


@app.get("/health")
def health():
    return {"ok": True}
