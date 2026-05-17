-- Repair Approved Skill Requests Missing Owned Skill v3
-- Uses acquired_via = 'xp' because oc_skills_acquired_via_check does not allow 'skill_purchase'.
-- Safe to run multiple times.

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
  'xp',
  0,
  spr.reviewed_by_discord_id,
  'Repaired from approved skill request; XP was already handled during approval.'
from public.skill_purchase_requests spr
where spr.status = 'approved'
  and not exists (
    select 1
    from public.oc_skills os
    where os.guild_id = spr.guild_id
      and os.character_id = spr.character_id
      and os.skill_key = spr.skill_key
  );

select
  spr.request_id,
  c.name as character_name,
  spr.skill_key,
  spr.status,
  spr.cost,
  w.available_xp,
  os.acquired_via,
  case when os.skill_key is not null then true else false end as now_owned
from public.skill_purchase_requests spr
left join public.characters c
  on c.guild_id = spr.guild_id
 and c.character_id = spr.character_id
left join public.oc_xp_wallets w
  on w.guild_id = spr.guild_id
 and w.character_id = spr.character_id
left join public.oc_skills os
  on os.guild_id = spr.guild_id
 and os.character_id = spr.character_id
 and os.skill_key = spr.skill_key
where spr.status = 'approved'
order by spr.reviewed_at desc nulls last, spr.created_at desc;
