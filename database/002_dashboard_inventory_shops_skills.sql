-- Railbound Tools Dashboard v2 foundation
-- Adds the skill catalog + skill purchase request workflow used by the web dashboard.
-- Inventory and shop dashboard pages reuse Keystone's existing tables:
--   items, inventory_entries, inventory_logs, inventory_loadouts,
--   companies, company_members, shop_items, shop_orders.

create extension if not exists pgcrypto;

-- Ensure a simple skills ownership table exists for projects that have not created one yet.
-- If your existing oc_skills table already exists, this block will not replace it.
create table if not exists public.oc_skills (
  guild_id bigint not null,
  character_id uuid not null,
  skill_key text not null,
  created_at timestamptz not null default now()
);

create unique index if not exists uq_oc_skills_character_skill
on public.oc_skills (guild_id, character_id, skill_key);

create table if not exists public.skill_definitions (
  skill_id uuid primary key default gen_random_uuid(),
  guild_id bigint not null,
  skill_key text not null,
  name text not null,
  tree text not null default 'General',
  tier integer,
  cost integer not null default 0 check (cost >= 0),
  prerequisites jsonb not null default '[]'::jsonb,
  chain text,
  usage text,
  effects text,
  description text,
  source_label text,
  sort_order integer not null default 0,
  is_active boolean not null default true,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (guild_id, skill_key)
);

create index if not exists idx_skill_definitions_guild_tree
on public.skill_definitions (guild_id, tree, is_active, sort_order);

create table if not exists public.skill_purchase_requests (
  request_id uuid primary key default gen_random_uuid(),
  guild_id bigint not null,
  character_id uuid not null,
  skill_key text not null,
  requested_by_discord_id bigint not null,
  status text not null default 'pending'
    check (status in ('pending', 'approved', 'denied', 'cancelled')),
  cost integer not null default 0 check (cost >= 0),
  submitter_note text,
  staff_note text,
  reviewed_by_discord_id bigint,
  reviewed_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists idx_skill_purchase_requests_guild_status
on public.skill_purchase_requests (guild_id, status, created_at desc);

create index if not exists idx_skill_purchase_requests_character
on public.skill_purchase_requests (guild_id, character_id, created_at desc);

-- Starter seed. You can edit/add the full catalog later from the dashboard/admin tools.
insert into public.skill_definitions
  (guild_id, skill_key, name, tree, tier, cost, prerequisites, chain, usage, effects, description, source_label, sort_order)
values
  (1462489358908129354, 'pilfer', 'Pilfer', 'Mercenary', 0, 50, '[]'::jsonb, 'Pilfer → Stealth → Misdirection', 'Non-combat utility', 'Redirect attention, sleight of hand, pickpocketing, and planting.', 'Tier 0 stealth skill.', 'Skill Guide', 10),
  (1462489358908129354, 'stealth', 'Stealth', 'Mercenary', 1, 265, '["pilfer"]'::jsonb, 'Pilfer → Stealth → Misdirection', 'Non-combat stealth', 'Hide, sneak, and set ambushes. Broken if detected or if attacking/defending once combat has begun.', 'Tier 1 stealth skill.', 'Skill Guide', 20),
  (1462489358908129354, 'misdirection', 'Misdirection', 'Mercenary', 2, 1200, '["stealth"]'::jsonb, 'Pilfer → Stealth → Misdirection', 'Combat stealth', 'Allows stealth actions in combat with AP costs and restrictions.', 'Tier 2 stealth skill.', 'Skill Guide', 30),
  (1462489358908129354, 'riding_harness_driving', 'Riding & Harness Driving', 'Mercenary / Character', 0, 50, '[]'::jsonb, null, 'Passive access', 'Use mounts, carts, carriages, and harness/yoke tools.', 'General travel/vehicle skill.', 'Skill Guide', 40),
  (1462489358908129354, 'pilot', 'Pilot', 'Mercenary / Character', 0, 100, '[]'::jsonb, null, 'Passive access', 'Pilot basic vehicles including unpowered boats, motorbikes, and simple vehicles.', 'General vehicle skill.', 'Skill Guide', 50),
  (1462489358908129354, 'pacing', 'Pacing', 'Mercenary / Character', 0, 300, '[]'::jsonb, null, 'Passive', 'Permanent +1 AP in all scenes.', 'Character improvement skill.', 'Skill Guide', 60),
  (1462489358908129354, 'quartermastery', 'Quartermastery', 'Mercenary / Character', 0, 300, '[]'::jsonb, null, 'Passive', 'Permanent +2 CC in all scenes.', 'Inventory/carry capacity skill.', 'Skill Guide', 70),
  (1462489358908129354, 'heavy_armaments', 'Heavy Armaments', 'Martial / Heavy', 1, 50, '[]'::jsonb, 'Heavy Armaments → Taunt/Dominion, Berserker/Sweeping Strike, Honed Strike/Mastered Strike', 'Passive combat style', '+2% damage output when using heavy arms.', 'Heavy weapon discipline.', 'Skill Guide', 100),
  (1462489358908129354, 'light_armaments', 'Light Armaments', 'Martial / Light', 1, 50, '[]'::jsonb, 'Light Armaments → Crowd Feint/Swashbuckler, Unbound/Disarm, Duelist/Parry', 'Passive combat style', '+2% damage output when using light arms.', 'Light weapon discipline.', 'Skill Guide', 110),
  (1462489358908129354, 'martial_arts', 'Martial Arts', 'Martial / Unarmed', 1, 50, '[]'::jsonb, 'Martial Arts → Offensive Defense/Furious Technique, Trance/Disarm, Brawler/Grappler', 'Passive combat style', '+4% damage output when fighting unarmed.', 'Unarmed combat discipline.', 'Skill Guide', 120)
on conflict (guild_id, skill_key) do update set
  name = excluded.name,
  tree = excluded.tree,
  tier = excluded.tier,
  cost = excluded.cost,
  prerequisites = excluded.prerequisites,
  chain = excluded.chain,
  usage = excluded.usage,
  effects = excluded.effects,
  description = excluded.description,
  source_label = excluded.source_label,
  sort_order = excluded.sort_order,
  is_active = true,
  updated_at = now();

create or replace function public.submit_skill_purchase_request(
  p_guild_id bigint,
  p_character_id uuid,
  p_skill_key text,
  p_requested_by_discord_id bigint,
  p_submitter_note text default null
)
returns jsonb
language plpgsql
as $$
declare
  v_skill record;
  v_existing integer;
  v_request_id uuid;
begin
  select *
  into v_skill
  from public.skill_definitions
  where guild_id = p_guild_id
    and skill_key = p_skill_key
    and is_active = true
  limit 1;

  if not found then
    raise exception 'Skill not found or inactive';
  end if;

  select count(*) into v_existing
  from public.oc_skills
  where guild_id = p_guild_id
    and character_id = p_character_id
    and skill_key = p_skill_key;

  if v_existing > 0 then
    raise exception 'Character already has this skill';
  end if;

  select count(*) into v_existing
  from public.skill_purchase_requests
  where guild_id = p_guild_id
    and character_id = p_character_id
    and skill_key = p_skill_key
    and status = 'pending';

  if v_existing > 0 then
    raise exception 'A pending request already exists for this skill';
  end if;

  insert into public.skill_purchase_requests (
    guild_id,
    character_id,
    skill_key,
    requested_by_discord_id,
    cost,
    submitter_note
  ) values (
    p_guild_id,
    p_character_id,
    p_skill_key,
    p_requested_by_discord_id,
    v_skill.cost,
    p_submitter_note
  ) returning request_id into v_request_id;

  return jsonb_build_object(
    'request_id', v_request_id,
    'status', 'pending',
    'skill_key', p_skill_key,
    'cost', v_skill.cost
  );
end;
$$;

create or replace function public.approve_skill_purchase_request(
  p_request_id uuid,
  p_staff_discord_id bigint,
  p_staff_note text default null
)
returns jsonb
language plpgsql
as $$
declare
  v_req record;
  v_skill record;
  v_tx_id uuid;
begin
  select *
  into v_req
  from public.skill_purchase_requests
  where request_id = p_request_id
  for update;

  if not found then
    raise exception 'Skill purchase request not found';
  end if;

  if v_req.status <> 'pending' then
    raise exception 'Request is not pending';
  end if;

  select *
  into v_skill
  from public.skill_definitions
  where guild_id = v_req.guild_id
    and skill_key = v_req.skill_key
    and is_active = true
  limit 1;

  if not found then
    raise exception 'Skill is no longer active';
  end if;

  if v_skill.cost <> v_req.cost then
    raise exception 'Skill cost is stale. Expected %, current %', v_req.cost, v_skill.cost;
  end if;

  if exists (
    select 1 from public.oc_skills
    where guild_id = v_req.guild_id
      and character_id = v_req.character_id
      and skill_key = v_req.skill_key
  ) then
    raise exception 'Character already has this skill';
  end if;

  if v_req.cost > 0 then
    v_tx_id := public.spend_xp(
      v_req.guild_id,
      v_req.character_id,
      v_req.cost,
      'skill_purchase',
      'skill',
      v_req.skill_key,
      'Skill purchase approved',
      p_staff_discord_id
    );
  end if;

  insert into public.oc_skills (guild_id, character_id, skill_key)
  values (v_req.guild_id, v_req.character_id, v_req.skill_key)
  on conflict do nothing;

  update public.skill_purchase_requests
  set
    status = 'approved',
    staff_note = p_staff_note,
    reviewed_by_discord_id = p_staff_discord_id,
    reviewed_at = now(),
    updated_at = now()
  where request_id = p_request_id;

  return jsonb_build_object(
    'request_id', p_request_id,
    'status', 'approved',
    'skill_key', v_req.skill_key,
    'cost', v_req.cost,
    'xp_tx_id', v_tx_id
  );
end;
$$;

create or replace function public.deny_skill_purchase_request(
  p_request_id uuid,
  p_staff_discord_id bigint,
  p_staff_note text default null
)
returns jsonb
language plpgsql
as $$
declare
  v_req record;
begin
  select *
  into v_req
  from public.skill_purchase_requests
  where request_id = p_request_id
  for update;

  if not found then
    raise exception 'Skill purchase request not found';
  end if;

  if v_req.status <> 'pending' then
    raise exception 'Request is not pending';
  end if;

  update public.skill_purchase_requests
  set
    status = 'denied',
    staff_note = p_staff_note,
    reviewed_by_discord_id = p_staff_discord_id,
    reviewed_at = now(),
    updated_at = now()
  where request_id = p_request_id;

  return jsonb_build_object('request_id', p_request_id, 'status', 'denied');
end;
$$;
