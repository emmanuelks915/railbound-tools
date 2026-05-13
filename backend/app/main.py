from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.routes import characters, combat, dashboard, inventory, shops, skills, staff, xp, rp

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
app.include_router(shops.router)
app.include_router(skills.router)
app.include_router(rp.router)


@app.get("/health")
def health():
    return {"ok": True}
