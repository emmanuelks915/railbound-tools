from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, File, UploadFile
from pydantic import BaseModel

from app.models import ShopItemPatchRequest, ShopPatchRequest
from app.permissions import company_member_rank, is_staff, require_actor, require_company_manager
from app.security import actor_from_header
from app.services import get_guild_id, sb_data
from app.supabase_client import get_supabase
from app.discord_webhook import notify_shop_listing_submitted
from uuid import uuid4
import httpx
from app.config import get_settings

router = APIRouter(prefix="/api/shops", tags=["shops"])

_ALLOWED_SHOP_IMAGE_TYPES = {
    "image/png": "png",
    "image/jpeg": "jpg",
    "image/webp": "webp",
    "image/gif": "gif",
}

_MAX_SHOP_IMAGE_BYTES = 8 * 1024 * 1024


def _storage_public_url(bucket: str, object_path: str) -> str:
    settings = get_settings()
    base_url = settings.supabase_url.rstrip("/")
    return f"{base_url}/storage/v1/object/public/{bucket}/{object_path}"


def _storage_upload_url(bucket: str, object_path: str) -> str:
    settings = get_settings()
    base_url = settings.supabase_url.rstrip("/")
    return f"{base_url}/storage/v1/object/{bucket}/{object_path}"



class ShopItemCreateRequest(BaseModel):
    name: str
    description: str = ""
    image_url: str | None = None
    price: int
    stock: int | None = None
    item_type: str | None = None
    item_class: str | None = None
    recipe_link: str | None = None
    unique_owner: str | None = None
    cc: int | None = None
    stat_limits: str | None = None
    special_effects: str | None = None
    usage_information: str | None = None
    requires_approval: bool = True
    purchasable: bool = True
    max_per_order: int | None = None
    max_per_day: int | None = None
    max_per_week: int | None = None
    max_per_user: int | None = None
    weight: int | None = None
    weight_unit: str | None = None


def _shop_select() -> str:
    return (
        "company_id,guild_id,name,owner_character_id,shop_description,"
        "shop_banner_url,shop_logo_url,shop_status,shop_category_id,"
        "shop_forum_channel_id,shop_storefront_thread_id"
    )


def _clean_text(value: str | None) -> str | None:
    if value is None:
        return None

    cleaned = str(value).strip()
    return cleaned or None


def _get_primary_currency_id(sb, guild_id: int) -> str:
    res = (
        sb.table("currencies")
        .select("currency_id")
        .eq("guild_id", guild_id)
        .eq("is_primary", True)
        .eq("is_enabled", True)
        .limit(1)
        .execute()
    )

    rows = sb_data(res) or []

    if rows:
        return str(rows[0]["currency_id"])

    fallback = (
        sb.table("currencies")
        .select("currency_id")
        .eq("guild_id", guild_id)
        .eq("is_enabled", True)
        .limit(1)
        .execute()
    )

    fallback_rows = sb_data(fallback) or []

    if fallback_rows:
        return str(fallback_rows[0]["currency_id"])

    raise HTTPException(status_code=400, detail="No enabled currency found for this server.")


def _get_primary_shop_id(sb, guild_id: int) -> str:
    """
    shop_items.shop_id points to the global marketplace shop in public.shops.
    shop_items.vendor_company_id points to the player/company shop in public.companies.
    """

    primary_shop_res = (
        sb.table("shops")
        .select("shop_id")
        .eq("guild_id", guild_id)
        .eq("enabled", True)
        .order("created_at", desc=False)
        .limit(1)
        .execute()
    )

    primary_shop_rows = sb_data(primary_shop_res) or []

    if not primary_shop_rows:
        raise HTTPException(
            status_code=400,
            detail="No enabled global shop exists. Create or enable a shop in public.shops first.",
        )

    return str(primary_shop_rows[0]["shop_id"])


@router.get("/mine")
def my_shops(actor_discord_id: int | None = Depends(actor_from_header)):
    actor = require_actor(actor_discord_id)
    sb = get_supabase()
    gid = get_guild_id()

    if is_staff(actor):
        res = (
            sb.table("companies")
            .select(_shop_select())
            .eq("guild_id", gid)
            .order("name", desc=False)
            .limit(500)
            .execute()
        )

        return {
            "shops": sb_data(res) or [],
            "staff_view": True,
        }

    memberships = (
        sb.table("company_members")
        .select("company_id,role")
        .eq("discord_id", actor)
        .execute()
    )

    member_rows = sb_data(memberships) or []

    company_ids = [
        str(r["company_id"])
        for r in member_rows
        if company_member_rank(sb, str(r["company_id"]), actor) >= 1
    ]

    if not company_ids:
        return {
            "shops": [],
            "staff_view": False,
        }

    shops = (
        sb.table("companies")
        .select(_shop_select())
        .eq("guild_id", gid)
        .in_("company_id", company_ids)
        .order("name", desc=False)
        .execute()
    )

    role_by_company = {
        str(r["company_id"]): str(r.get("role") or "MEMBER")
        for r in member_rows
    }

    out = []

    for shop in sb_data(shops) or []:
        out.append(
            {
                **shop,
                "member_role": role_by_company.get(str(shop["company_id"])),
            }
        )

    return {
        "shops": out,
        "staff_view": False,
    }


@router.get("/{company_id}")
def shop_detail(
    company_id: str,
    actor_discord_id: int | None = Depends(actor_from_header),
):
    actor = require_actor(actor_discord_id)
    sb = get_supabase()

    if not is_staff(actor) and company_member_rank(sb, company_id, actor) < 1:
        raise HTTPException(status_code=403, detail="You can only view shops you belong to.")

    shop_res = (
        sb.table("companies")
        .select("*")
        .eq("guild_id", get_guild_id())
        .eq("company_id", str(company_id))
        .limit(1)
        .execute()
    )

    rows = sb_data(shop_res) or []

    if not rows:
        raise HTTPException(status_code=404, detail="Shop not found.")

    return {"shop": rows[0]}


@router.patch("/{company_id}")
def update_shop(
    company_id: str,
    payload: ShopPatchRequest,
    actor_discord_id: int | None = Depends(actor_from_header),
):
    sb = get_supabase()
    require_company_manager(sb, company_id, actor_discord_id, min_rank=2)

    patch = {}

    if payload.name is not None:
        patch["name"] = payload.name.strip()

    if payload.description is not None:
        patch["shop_description"] = payload.description.strip() or None

    if payload.banner_url is not None:
        patch["shop_banner_url"] = payload.banner_url.strip() or None

    if payload.logo_url is not None:
        patch["shop_logo_url"] = payload.logo_url.strip() or None

    if not patch:
        raise HTTPException(status_code=400, detail="No shop changes provided.")

    (
        sb.table("companies")
        .update(patch)
        .eq("guild_id", get_guild_id())
        .eq("company_id", str(company_id))
        .execute()
    )

    return {
        "ok": True,
        "updated_fields": sorted(patch.keys()),
    }


@router.get("/{company_id}/items")
def shop_items(
    company_id: str,
    actor_discord_id: int | None = Depends(actor_from_header),
):
    actor = require_actor(actor_discord_id)
    sb = get_supabase()

    if not is_staff(actor) and company_member_rank(sb, company_id, actor) < 1:
        raise HTTPException(status_code=403, detail="You can only view shops you belong to.")

    res = (
        sb.table("shop_items")
        .select("*")
        .eq("guild_id", get_guild_id())
        .eq("vendor_company_id", str(company_id))
        .order("created_at", desc=True)
        .limit(500)
        .execute()
    )

    return {"items": sb_data(res) or []}



@router.post("/{company_id}/images")
def upload_shop_image(
    company_id: str,
    file: UploadFile = File(...),
    actor_discord_id: int | None = Depends(actor_from_header),
):
    actor = require_actor(actor_discord_id)
    sb = get_supabase()
    gid = get_guild_id()

    require_company_manager(sb, company_id, actor, min_rank=2)

    content_type = (file.content_type or "").split(";")[0].strip().lower()

    if content_type not in _ALLOWED_SHOP_IMAGE_TYPES:
        raise HTTPException(
            status_code=400,
            detail="Unsupported image type. Use PNG, JPG, WEBP, or GIF.",
        )

    data = file.file.read()

    if not data:
        raise HTTPException(status_code=400, detail="Image file is empty.")

    if len(data) > _MAX_SHOP_IMAGE_BYTES:
        raise HTTPException(status_code=400, detail="Image must be 8 MB or smaller.")

    settings = get_settings()
    bucket = settings.supabase_storage_bucket
    ext = _ALLOWED_SHOP_IMAGE_TYPES[content_type]
    object_path = f"shop-listings/{gid}/{company_id}/{uuid4()}.{ext}"

    headers = {
        "apikey": settings.supabase_admin_key,
        "Content-Type": content_type,
        "Cache-Control": "3600",
        "x-upsert": "false",
    }

    upload_url = _storage_upload_url(bucket, object_path)

    try:
        response = httpx.post(
            upload_url,
            content=data,
            headers=headers,
            timeout=30.0,
        )
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Image upload failed: {exc}") from exc

    if response.status_code >= 400:
        detail = response.text or "Image upload failed."
        raise HTTPException(status_code=400, detail=detail)

    public_url = _storage_public_url(bucket, object_path)

    return {
        "ok": True,
        "bucket": bucket,
        "path": object_path,
        "url": public_url,
        "content_type": content_type,
        "size_bytes": len(data),
    }


@router.post("/{company_id}/items")
def create_shop_item(
    company_id: str,
    payload: ShopItemCreateRequest,
    actor_discord_id: int | None = Depends(actor_from_header),
):
    actor = require_actor(actor_discord_id)
    sb = get_supabase()
    gid = get_guild_id()

    require_company_manager(sb, company_id, actor, min_rank=2)

    name = _clean_text(payload.name)

    if not name:
        raise HTTPException(status_code=400, detail="Item name is required.")

    if int(payload.price) < 0:
        raise HTTPException(status_code=400, detail="Price cannot be negative.")

    if payload.stock is not None and int(payload.stock) < 0:
        raise HTTPException(status_code=400, detail="Stock cannot be negative.")

    currency_id = _get_primary_currency_id(sb, gid)
    primary_shop_id = _get_primary_shop_id(sb, gid)

    row = {
        "guild_id": gid,

        # This must point to public.shops.shop_id, usually your global Railbound Shop.
        "shop_id": primary_shop_id,

        # This points to the player/company shop.
        "vendor_company_id": str(company_id),

        "currency_id": currency_id,
        "name": name,
        "description": _clean_text(payload.description),
        "image_url": _clean_text(payload.image_url),
        "price": int(payload.price),
        "stock": None if payload.stock is None else int(payload.stock),
        "purchasable": bool(payload.purchasable),
        "requires_approval": True,
        "is_active": False,
        "review_status": "pending_staff_review",
        "item_type": _clean_text(payload.item_type) or "item",
        "item_class": _clean_text(payload.item_class),
        "recipe_link": _clean_text(payload.recipe_link),
        "unique_owner": _clean_text(payload.unique_owner),
        "cc": None if payload.cc is None else int(payload.cc),
        "stat_limits": _clean_text(payload.stat_limits),
        "special_effects": _clean_text(payload.special_effects),
        "usage_information": _clean_text(payload.usage_information),
        "submitted_by_discord_id": actor,
        "max_per_order": payload.max_per_order,
        "max_per_day": payload.max_per_day,
        "max_per_week": payload.max_per_week,
        "max_per_user": payload.max_per_user,
        "weight": payload.weight,
        "weight_unit": _clean_text(payload.weight_unit),
    }

    ins = sb.table("shop_items").insert(row).execute()
    rows = sb_data(ins) or []
    created = rows[0] if rows else row

    if isinstance(created, dict):
        notify_shop_listing_submitted(created)

    return {
        "ok": True,
        "item": created,
        "message": "Listing submitted for staff review.",
    }


@router.patch("/items/{item_id}")
def update_shop_item(
    item_id: str,
    payload: ShopItemPatchRequest,
    actor_discord_id: int | None = Depends(actor_from_header),
):
    actor = require_actor(actor_discord_id)
    sb = get_supabase()
    gid = get_guild_id()

    item_res = (
        sb.table("shop_items")
        .select("*")
        .eq("guild_id", gid)
        .eq("item_id", str(item_id))
        .limit(1)
        .execute()
    )

    rows = sb_data(item_res) or []

    if not rows:
        raise HTTPException(status_code=404, detail="Shop item not found.")

    item = rows[0]
    company_id = str(item.get("vendor_company_id") or "")

    if not is_staff(actor):
        if not company_id or company_member_rank(sb, company_id, actor) < 2:
            raise HTTPException(
                status_code=403,
                detail="You must be this shop's owner or manager to edit listings.",
            )

    patch = {}

    if payload.name is not None:
        patch["name"] = payload.name.strip()

    if payload.description is not None:
        patch["description"] = payload.description.strip()

    if payload.price is not None:
        patch["price"] = int(payload.price)

    if payload.stock is not None:
        patch["stock"] = int(payload.stock)

    if payload.is_active is not None:
        # Non-staff can unpublish their own items, but staff approval should still control publishing.
        if payload.is_active and not is_staff(actor):
            raise HTTPException(status_code=403, detail="Staff approval is required to publish listings.")

        patch["is_active"] = bool(payload.is_active)

    if payload.review_status is not None:
        if not is_staff(actor):
            raise HTTPException(status_code=403, detail="Staff only can set review status directly.")

        patch["review_status"] = payload.review_status.strip()

    if not patch:
        raise HTTPException(status_code=400, detail="No item changes provided.")

    (
        sb.table("shop_items")
        .update(patch)
        .eq("guild_id", gid)
        .eq("item_id", str(item_id))
        .execute()
    )

    return {
        "ok": True,
        "updated_fields": sorted(patch.keys()),
    }