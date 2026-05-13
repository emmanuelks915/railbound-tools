-- 003_stat_request_hotfixes.sql
-- Final working stat request RPCs discovered during local Railbound Tools testing.

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

  if p_stat_key not in ('strength', 'dexterity', 'stamina', 'magic_affinity', 'mana') then
    raise exception 'Derived/non-core stat cannot be purchased: %', p_stat_key;
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
  v_item jsonb;
  v_stat_key text;
  v_target_value integer;
  v_current_value integer;
  v_preview jsonb;
  v_cost integer;
  v_total integer := 0;
  v_items_created integer := 0;
begin
  if p_target_stats is null then
    raise exception 'No stat upgrades provided';
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
    p_submitter_note
  )
  returning request_id into v_request_id;

  if jsonb_typeof(p_target_stats) = 'object' then
    for v_stat_key, v_target_value in
      select key, trim(both '"' from value::text)::integer
      from jsonb_each(p_target_stats)
    loop
      select stat_value
      into v_current_value
      from public.oc_stats
      where guild_id = p_guild_id
        and character_id = p_character_id
        and stat_key = v_stat_key
      limit 1;

      v_current_value := coalesce(v_current_value, 0);

      if v_target_value < v_current_value then
        delete from public.stat_upgrade_requests where request_id = v_request_id;
        raise exception 'Target value for % cannot be lower than current value %', v_stat_key, v_current_value;
      end if;

      if v_target_value = v_current_value then
        continue;
      end if;

      v_preview := public.calculate_stat_upgrade_cost(
        v_stat_key,
        v_current_value,
        v_target_value
      );

      v_cost := (v_preview ->> 'total_cost')::integer;
      v_total := v_total + v_cost;
      v_items_created := v_items_created + 1;

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
    end loop;

  elsif jsonb_typeof(p_target_stats) = 'array' then
    for v_item in select * from jsonb_array_elements(p_target_stats)
    loop
      v_stat_key := v_item ->> 'stat_key';
      v_target_value := (v_item ->> 'target_value')::integer;

      select stat_value
      into v_current_value
      from public.oc_stats
      where guild_id = p_guild_id
        and character_id = p_character_id
        and stat_key = v_stat_key
      limit 1;

      v_current_value := coalesce(v_current_value, 0);

      if v_target_value < v_current_value then
        delete from public.stat_upgrade_requests where request_id = v_request_id;
        raise exception 'Target value for % cannot be lower than current value %', v_stat_key, v_current_value;
      end if;

      if v_target_value = v_current_value then
        continue;
      end if;

      v_preview := public.calculate_stat_upgrade_cost(
        v_stat_key,
        v_current_value,
        v_target_value
      );

      v_cost := (v_preview ->> 'total_cost')::integer;
      v_total := v_total + v_cost;
      v_items_created := v_items_created + 1;

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
    end loop;

  else
    delete from public.stat_upgrade_requests where request_id = v_request_id;
    raise exception 'Invalid stat upgrade payload';
  end if;

  if v_items_created = 0 then
    delete from public.stat_upgrade_requests where request_id = v_request_id;
    raise exception 'No changed stats submitted';
  end if;

  update public.stat_upgrade_requests
  set
    total_cost = v_total,
    updated_at = now()
  where request_id = v_request_id;

  return jsonb_build_object(
    'request_id', v_request_id,
    'status', 'pending',
    'total_cost', v_total,
    'items_created', v_items_created
  );
end;
$$;


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

    v_current := coalesce(v_current, 0);

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
    staff_note = p_staff_note,
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
    staff_note = p_staff_note,
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


notify pgrst, 'reload schema';