-- =========================================================
-- Railbound Tools MVP
-- Stat Upgrade Requests + Cost Preview + Staff Approval RPCs
-- =========================================================
-- This patch intentionally reuses your existing:
--   public.stat_xp_cost_bands
--   public.buy_stat_point(...)
--   public.spend_xp(...)
--   public.oc_stats
--   public.oc_stat_changes
--   public.oc_xp_wallets
-- =========================================================

create extension if not exists pgcrypto;

-- =========================================================
-- updated_at helper
-- =========================================================

create or replace function public.set_updated_at()
returns trigger
language plpgsql
as $$
begin
  new.updated_at := now();
  return new;
end;
$$;

-- =========================================================
-- STAT UPGRADE REQUESTS
-- =========================================================

create table if not exists public.stat_upgrade_requests (
  request_id uuid primary key default gen_random_uuid(),

  guild_id bigint not null,
  character_id uuid not null,
  requested_by_discord_id bigint not null,

  status text not null default 'pending'
    check (status in ('pending', 'approved', 'denied', 'cancelled')),

  total_cost integer not null default 0
    check (total_cost >= 0),

  submitter_note text,
  staff_note text,

  reviewed_by_discord_id bigint,
  reviewed_at timestamptz,

  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists idx_stat_upgrade_requests_guild_status
on public.stat_upgrade_requests (guild_id, status, created_at desc);

create index if not exists idx_stat_upgrade_requests_character
on public.stat_upgrade_requests (guild_id, character_id, created_at desc);

drop trigger if exists trg_stat_upgrade_requests_updated_at on public.stat_upgrade_requests;
create trigger trg_stat_upgrade_requests_updated_at
before update on public.stat_upgrade_requests
for each row
execute function public.set_updated_at();

-- =========================================================
-- STAT UPGRADE REQUEST ITEMS
-- One request can contain multiple stat upgrades.
-- Core stats only. Derived stats are not buyable.
-- =========================================================

create table if not exists public.stat_upgrade_request_items (
  item_id uuid primary key default gen_random_uuid(),

  request_id uuid not null
    references public.stat_upgrade_requests(request_id)
    on delete cascade,

  stat_key text not null
    check (stat_key in (
      'strength',
      'dexterity',
      'stamina',
      'magic_affinity',
      'mana'
    )),

  current_value integer not null check (current_value >= 0),
  target_value integer not null check (target_value >= 0),
  points_added integer not null check (points_added > 0),
  cost integer not null check (cost >= 0),

  cost_breakdown jsonb not null default '[]'::jsonb,

  created_at timestamptz not null default now(),

  constraint stat_upgrade_request_items_values_check
    check (target_value > current_value),

  constraint stat_upgrade_request_items_points_check
    check (points_added = target_value - current_value)
);

create index if not exists idx_stat_upgrade_request_items_request
on public.stat_upgrade_request_items (request_id);

-- =========================================================
-- Core stat guard helper
-- =========================================================

create or replace function public.is_core_stat_key(p_stat_key text)
returns boolean
language sql
immutable
as $$
  select p_stat_key in (
    'strength',
    'dexterity',
    'stamina',
    'magic_affinity',
    'mana'
  );
$$;

-- =========================================================
-- Cost preview function
-- Mirrors existing public.buy_stat_point cost logic.
-- Uses public.stat_xp_cost_bands.
-- =========================================================

create or replace function public.calculate_stat_upgrade_cost(
  p_stat_key text,
  p_current_value integer,
  p_target_value integer
)
returns jsonb
language plpgsql
as $$
declare
  v_value integer;
  v_band_cost integer;

  v_total integer := 0;
  v_breakdown jsonb := '[]'::jsonb;

  v_seg_start integer := null;
  v_seg_end integer := null;
  v_seg_cost integer := null;
begin
  if p_stat_key is null or trim(p_stat_key) = '' then
    raise exception 'Stat key cannot be blank';
  end if;

  if not public.is_core_stat_key(p_stat_key) then
    raise exception 'Only core stats can be purchased: %', p_stat_key;
  end if;

  if p_current_value < 0 then
    raise exception 'Current value cannot be negative';
  end if;

  if p_target_value <= p_current_value then
    raise exception 'Target value must be greater than current value';
  end if;

  for v_value in (p_current_value + 1)..p_target_value loop
    select cost_per_point
    into v_band_cost
    from public.stat_xp_cost_bands
    where (stat_key is null or stat_key = p_stat_key)
      and v_value between min_value and max_value
    order by stat_key desc nulls last
    limit 1;

    if v_band_cost is null then
      raise exception 'No XP cost band found for stat value %', v_value;
    end if;

    v_total := v_total + v_band_cost;

    if v_seg_cost is null then
      v_seg_start := v_value;
      v_seg_end := v_value;
      v_seg_cost := v_band_cost;
    elsif v_seg_cost = v_band_cost and v_value = v_seg_end + 1 then
      v_seg_end := v_value;
    else
      v_breakdown := v_breakdown || jsonb_build_array(
        jsonb_build_object(
          'from_value', v_seg_start,
          'to_value', v_seg_end,
          'points', v_seg_end - v_seg_start + 1,
          'cost_per_point', v_seg_cost,
          'subtotal', (v_seg_end - v_seg_start + 1) * v_seg_cost
        )
      );

      v_seg_start := v_value;
      v_seg_end := v_value;
      v_seg_cost := v_band_cost;
    end if;
  end loop;

  if v_seg_cost is not null then
    v_breakdown := v_breakdown || jsonb_build_array(
      jsonb_build_object(
        'from_value', v_seg_start,
        'to_value', v_seg_end,
        'points', v_seg_end - v_seg_start + 1,
        'cost_per_point', v_seg_cost,
        'subtotal', (v_seg_end - v_seg_start + 1) * v_seg_cost
      )
    );
  end if;

  return jsonb_build_object(
    'stat_key', p_stat_key,
    'current_value', p_current_value,
    'target_value', p_target_value,
    'points_added', p_target_value - p_current_value,
    'total_cost', v_total,
    'breakdown', v_breakdown
  );
end;
$$;

-- =========================================================
-- Submit request RPC
-- p_target_stats format:
-- {
--   "strength": 100,
--   "dexterity": 150,
--   "stamina": 80
-- }
-- =========================================================

create or replace function public.submit_stat_upgrade_request(
  p_guild_id bigint,
  p_character_id uuid,
  p_requested_by_discord_id bigint,
  p_target_stats jsonb,
  p_submitter_note text default null
)
returns jsonb
language plpgsql
as $$
declare
  v_request_id uuid;
  v_stat_key text;
  v_target_text text;
  v_target_value integer;
  v_current_value integer;
  v_preview jsonb;
  v_cost integer;
  v_total_cost integer := 0;
  v_item_count integer := 0;
begin
  if p_target_stats is null or jsonb_typeof(p_target_stats) <> 'object' then
    raise exception 'Target stats must be a JSON object';
  end if;

  insert into public.stat_upgrade_requests (
    guild_id,
    character_id,
    requested_by_discord_id,
    status,
    total_cost,
    submitter_note
  )
  values (
    p_guild_id,
    p_character_id,
    p_requested_by_discord_id,
    'pending',
    0,
    nullif(trim(coalesce(p_submitter_note, '')), '')
  )
  returning request_id into v_request_id;

  for v_stat_key, v_target_text in
    select key, value #>> '{}'
    from jsonb_each(p_target_stats)
  loop
    if not public.is_core_stat_key(v_stat_key) then
      raise exception 'Only core stats can be purchased: %', v_stat_key;
    end if;

    if v_target_text is null or trim(v_target_text) = '' then
      raise exception 'Target value cannot be blank for %', v_stat_key;
    end if;

    v_target_value := v_target_text::integer;

    select stat_value
    into v_current_value
    from public.oc_stats
    where guild_id = p_guild_id
      and character_id = p_character_id
      and stat_key = v_stat_key;

    if v_current_value is null then
      v_current_value := 0;
    end if;

    if v_target_value <= v_current_value then
      -- Ignore unchanged/lower target stats instead of failing the whole request.
      continue;
    end if;

    v_preview := public.calculate_stat_upgrade_cost(
      v_stat_key,
      v_current_value,
      v_target_value
    );

    v_cost := (v_preview ->> 'total_cost')::integer;

    insert into public.stat_upgrade_request_items (
      request_id,
      stat_key,
      current_value,
      target_value,
      points_added,
      cost,
      cost_breakdown
    )
    values (
      v_request_id,
      v_stat_key,
      v_current_value,
      v_target_value,
      v_target_value - v_current_value,
      v_cost,
      v_preview -> 'breakdown'
    );

    v_total_cost := v_total_cost + v_cost;
    v_item_count := v_item_count + 1;
  end loop;

  if v_item_count = 0 then
    delete from public.stat_upgrade_requests
    where request_id = v_request_id;

    raise exception 'Request must include at least one stat increase';
  end if;

  update public.stat_upgrade_requests
  set total_cost = v_total_cost
  where request_id = v_request_id;

  return jsonb_build_object(
    'request_id', v_request_id,
    'status', 'pending',
    'total_cost', v_total_cost,
    'item_count', v_item_count
  );
end;
$$;

-- =========================================================
-- Staff approval RPC
-- Re-checks stale stats and stale costs, then calls existing buy_stat_point.
-- =========================================================

create or replace function public.approve_stat_upgrade_request(
  p_request_id uuid,
  p_staff_discord_id bigint,
  p_staff_note text default null
)
returns jsonb
language plpgsql
as $$
declare
  v_request record;
  v_item record;

  v_current integer;
  v_preview jsonb;
  v_recalculated_cost integer;
  v_actual_total integer := 0;
begin
  select *
  into v_request
  from public.stat_upgrade_requests
  where request_id = p_request_id
  for update;

  if not found then
    raise exception 'Stat upgrade request not found';
  end if;

  if v_request.status <> 'pending' then
    raise exception 'Request is not pending';
  end if;

  for v_item in
    select *
    from public.stat_upgrade_request_items
    where request_id = p_request_id
    order by created_at asc
  loop
    select stat_value
    into v_current
    from public.oc_stats
    where guild_id = v_request.guild_id
      and character_id = v_request.character_id
      and stat_key = v_item.stat_key
    for update;

    if v_current is null then
      v_current := 0;
    end if;

    if v_current <> v_item.current_value then
      raise exception
        'Request is stale for %. Expected current value %, found %',
        v_item.stat_key,
        v_item.current_value,
        v_current;
    end if;

    v_preview := public.calculate_stat_upgrade_cost(
      v_item.stat_key,
      v_item.current_value,
      v_item.target_value
    );

    v_recalculated_cost := (v_preview ->> 'total_cost')::integer;

    if v_recalculated_cost <> v_item.cost then
      raise exception
        'Request cost is stale for %. Expected cost %, recalculated cost %',
        v_item.stat_key,
        v_item.cost,
        v_recalculated_cost;
    end if;

    v_actual_total := v_actual_total + v_recalculated_cost;

    perform public.buy_stat_point(
      v_request.guild_id,
      v_request.character_id,
      v_item.stat_key,
      v_item.points_added,
      p_staff_discord_id
    );
  end loop;

  if v_actual_total <> v_request.total_cost then
    raise exception
      'Request total cost is stale. Expected %, recalculated %',
      v_request.total_cost,
      v_actual_total;
  end if;

  update public.stat_upgrade_requests
  set
    status = 'approved',
    staff_note = nullif(trim(coalesce(p_staff_note, '')), ''),
    reviewed_by_discord_id = p_staff_discord_id,
    reviewed_at = now(),
    updated_at = now()
  where request_id = p_request_id;

  return jsonb_build_object(
    'request_id', p_request_id,
    'status', 'approved',
    'total_cost', v_actual_total
  );
end;
$$;

-- =========================================================
-- Staff deny RPC
-- =========================================================

create or replace function public.deny_stat_upgrade_request(
  p_request_id uuid,
  p_staff_discord_id bigint,
  p_staff_note text default null
)
returns jsonb
language plpgsql
as $$
declare
  v_request record;
begin
  select *
  into v_request
  from public.stat_upgrade_requests
  where request_id = p_request_id
  for update;

  if not found then
    raise exception 'Stat upgrade request not found';
  end if;

  if v_request.status <> 'pending' then
    raise exception 'Request is not pending';
  end if;

  update public.stat_upgrade_requests
  set
    status = 'denied',
    staff_note = nullif(trim(coalesce(p_staff_note, '')), ''),
    reviewed_by_discord_id = p_staff_discord_id,
    reviewed_at = now(),
    updated_at = now()
  where request_id = p_request_id;

  return jsonb_build_object(
    'request_id', p_request_id,
    'status', 'denied'
  );
end;
$$;

-- =========================================================
-- Player cancel RPC
-- =========================================================

create or replace function public.cancel_stat_upgrade_request(
  p_request_id uuid,
  p_requested_by_discord_id bigint
)
returns jsonb
language plpgsql
as $$
declare
  v_request record;
begin
  select *
  into v_request
  from public.stat_upgrade_requests
  where request_id = p_request_id
  for update;

  if not found then
    raise exception 'Stat upgrade request not found';
  end if;

  if v_request.status <> 'pending' then
    raise exception 'Request is not pending';
  end if;

  if v_request.requested_by_discord_id <> p_requested_by_discord_id then
    raise exception 'Only the requester can cancel this request';
  end if;

  update public.stat_upgrade_requests
  set
    status = 'cancelled',
    updated_at = now()
  where request_id = p_request_id;

  return jsonb_build_object(
    'request_id', p_request_id,
    'status', 'cancelled'
  );
end;
$$;
