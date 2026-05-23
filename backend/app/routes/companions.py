from __future__ import annotations
from math import ceil
from typing import Any
from uuid import UUID
from fastapi import APIRouter, Body, Depends, HTTPException
from app.permissions import is_staff
from app.security import actor_from_header
from app.services import get_guild_id, sb_data
from app.supabase_client import get_supabase
router = APIRouter(prefix="/api/companions", tags=["companions"])
CORE_STATS=["strength","dexterity","stamina","magic_affinity","mana"]
RULES={"combat":{"combat":3,"mount":2,"utility":1,"own_type_skill_cap_per_tier":3,"non_type_skill_cap_per_tier":2},"mount":{"combat":1,"mount":3,"utility":2,"own_type_skill_cap_per_tier":3,"non_type_skill_cap_per_tier":2},"utility":{"combat":2,"mount":1,"utility":3,"own_type_skill_cap_per_tier":3,"non_type_skill_cap_per_tier":2}}
def _rows(x):
    r=sb_data(x) or []
    return r if isinstance(r,list) else []
def _safe(q):
    try: return _rows(q.execute())
    except Exception: return []
def _actor(x):
    if x is None: raise HTTPException(status_code=401, detail="Login with Discord required.")
    return int(x)
def _char(sb,cid):
    r=_safe(sb.table("characters").select("*").eq("character_id",cid).limit(1))
    if not r: raise HTTPException(status_code=404, detail="OC not found.")
    return r[0]
def _can(c,a):
    return is_staff(a) or any(str(c.get(k))==str(a) for k in ("user_id","discord_id","owner_discord_id","player_discord_id") if c.get(k) is not None)
def _traits(sb,cid,gid):
    owned=[]
    for t in ("oc_traits","character_traits"):
        owned += _safe(sb.table(t).select("*").eq("character_id",cid).limit(300))
    ids=[str(r.get("trait_id")) for r in owned if r.get("trait_id")]
    slugs=[str(r.get(k)) for r in owned for k in ("slug","trait_slug","trait_key") if r.get(k)]
    catalog=[]
    if ids: catalog += _safe(sb.table("traits").select("*").eq("guild_id",gid).in_("trait_id",ids).limit(300))
    if slugs: catalog += _safe(sb.table("traits").select("*").eq("guild_id",gid).in_("slug",slugs).limit(300))
    byid={str(r.get("trait_id")):r for r in catalog if r.get("trait_id")}
    byslug={str(r.get("slug")):r for r in catalog if r.get("slug")}
    out=[]; seen=set()
    for r in owned:
        s=byid.get(str(r.get("trait_id"))) if r.get("trait_id") else None
        if not s:
            for k in ("slug","trait_slug","trait_key"):
                if r.get(k) and str(r.get(k)) in byslug:
                    s=byslug[str(r.get(k))]; break
        s=s or r
        slug=str(s.get("slug") or r.get("slug") or r.get("trait_slug") or r.get("trait_key") or "")
        name=str(s.get("name") or r.get("name") or r.get("trait_name") or slug or "")
        marker=slug or name
        if marker in seen: continue
        seen.add(marker)
        out.append({**s,"slug":slug,"name":name})
    return out
def _eligible(traits):
    return any("loyal_companion" in str(t.get("slug") or "").lower().replace("-","_").replace(" ","_") or "loyal companion" in str(t.get("name") or "").lower() for t in traits)
def _stats(sb,cid,gid):
    r=_safe(sb.table("oc_stats").select("stat_key,stat_value,value").eq("guild_id",gid).eq("character_id",cid).limit(100))
    out={k:0 for k in CORE_STATS}
    for x in r:
        k=str(x.get("stat_key") or "")
        if k in out: out[k]=int((x.get("stat_value") if x.get("stat_value") is not None else x.get("value")) or 0)
    return out
def _default(cid,gid):
    return {"guild_id":gid,"character_id":cid,"beast_name":"","beast_type":"utility","description":"","image_url":"","xp":0,"base_strength":5,"base_dexterity":5,"base_stamina":5,"base_magic_affinity":5,"base_mana":5,"current_skills":"","notes":""}
def _computed(b,s):
    out={}
    for k in CORE_STATS:
        base=int(b.get(f"base_{k}") or 5); mod=ceil(int(s.get(k) or 0)*.10)
        out[k]={"base":base,"modifier":mod,"final":base+mod}
    return out
def _int(p,k,d=5):
    try: return max(0,int(p.get(k,d)))
    except Exception: return d
@router.get("/{character_id}")
def get_companion(character_id: UUID, actor_discord_id:int|None=Depends(actor_from_header)):
    a=_actor(actor_discord_id); sb=get_supabase(); cid=str(character_id); c=_char(sb,cid)
    if not _can(c,a): raise HTTPException(status_code=403, detail="You can only view your own companion.")
    gid=int(c.get("guild_id") or get_guild_id()); traits=_traits(sb,cid,gid); elig=_eligible(traits)
    rows=_safe(sb.table("source_beasts").select("*").eq("character_id",cid).limit(1))
    beast=rows[0] if rows else _default(cid,gid); stats=_stats(sb,cid,gid); typ=str(beast.get("beast_type") or "utility")
    return {"eligible":elig,"character":{"character_id":cid,"name":c.get("name")},"loyal_companion_trait":next((t for t in traits if _eligible([t])),None),"beast":beast,"oc_stats":stats,"computed_stats":_computed(beast,stats),"type_rules":RULES.get(typ,RULES["utility"]),"allowed_types":["combat","mount","utility"]}
@router.put("/{character_id}")
def save_companion(character_id:UUID,payload:dict[str,Any]=Body(default={}),actor_discord_id:int|None=Depends(actor_from_header)):
    a=_actor(actor_discord_id); sb=get_supabase(); cid=str(character_id); c=_char(sb,cid)
    if not _can(c,a): raise HTTPException(status_code=403, detail="You can only edit your own companion.")
    gid=int(c.get("guild_id") or get_guild_id())
    if not _eligible(_traits(sb,cid,gid)): raise HTTPException(status_code=403, detail="This OC does not have the Loyal Companion trait.")
    typ=str(payload.get("beast_type") or "utility").lower().strip()
    if typ=="support": typ="utility"
    if typ not in RULES: raise HTTPException(status_code=400, detail="Beast type must be combat, mount, or utility.")
    row={"guild_id":gid,"character_id":cid,"beast_name":str(payload.get("beast_name") or "")[:160],"beast_type":typ,"description":str(payload.get("description") or "")[:4000],"image_url":str(payload.get("image_url") or "")[:1000],"xp":_int(payload,"xp",0),"base_strength":_int(payload,"base_strength"),"base_dexterity":_int(payload,"base_dexterity"),"base_stamina":_int(payload,"base_stamina"),"base_magic_affinity":_int(payload,"base_magic_affinity"),"base_mana":_int(payload,"base_mana"),"current_skills":str(payload.get("current_skills") or "")[:4000],"notes":str(payload.get("notes") or "")[:4000]}
    try: rows=_rows(sb.table("source_beasts").upsert(row,on_conflict="character_id").execute())
    except Exception:
        exists=_safe(sb.table("source_beasts").select("character_id").eq("character_id",cid).limit(1))
        rows=_rows((sb.table("source_beasts").update(row).eq("character_id",cid) if exists else sb.table("source_beasts").insert(row)).execute())
    saved=rows[0] if rows else row; stats=_stats(sb,cid,gid)
    return {"message":"Source Beast saved.","beast":saved,"computed_stats":_computed(saved,stats),"type_rules":RULES.get(typ,RULES["utility"])}
