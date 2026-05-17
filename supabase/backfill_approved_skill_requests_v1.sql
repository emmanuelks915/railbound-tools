-- Backfill Approved Skill Purchase Requests v1
-- Fixes approved skill requests that deducted XP but did not appear in Owned Skills.
-- Safe to run multiple times: it only inserts missing oc_skills rows.

insert into public.oc_skills (
  guild_id,
  character_id,
  skill_key,
  acquired_via,
  xp_cost_paid,
  actor_discord_id,
  notes
)
select
  spr.guild_id,
  spr.character_id,
  spr.skill_key,
  'skill_purchase',
  spr.cost,
  spr.reviewed_by_discord_id,
  coalesce(spr.staff_note, 'Backfilled from approved skill purchase request.')
from public.skill_purchase_requests spr
where spr.status = 'approved'
  and not exists (
    select 1
    from public.oc_skills os
    where os.guild_id = spr.guild_id
      and os.character_id = spr.character_id
      and os.skill_key = spr.skill_key
  );

-- Verify approved skill requests now have owned skill rows.
select
  spr.request_id,
  spr.character_id,
  c.name as character_name,
  spr.skill_key,
  spr.status,
  spr.cost,
  case when os.skill_key is not null then true else false end as now_owned
from public.skill_purchase_requests spr
left join public.characters c
  on c.guild_id = spr.guild_id
 and c.character_id = spr.character_id
left join public.oc_skills os
  on os.guild_id = spr.guild_id
 and os.character_id = spr.character_id
 and os.skill_key = spr.skill_key
where spr.status = 'approved'
order by spr.updated_at desc;
