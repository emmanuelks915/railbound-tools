-- Activity Log Hardening v2
-- Dedicated audit/activity trail for Railbound Tools.

create table if not exists public.activity_log (
  activity_id uuid primary key default gen_random_uuid(),
  guild_id bigint not null,
  event_type text not null,
  label text not null,
  status text default 'info',
  actor_discord_id bigint,
  character_id uuid,
  character_name text,
  amount numeric,
  note text,
  source text,
  details jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);

create index if not exists idx_activity_log_guild_created
  on public.activity_log (guild_id, created_at desc);

create index if not exists idx_activity_log_guild_event_type
  on public.activity_log (guild_id, event_type);

create index if not exists idx_activity_log_guild_status
  on public.activity_log (guild_id, status);

create index if not exists idx_activity_log_character_id
  on public.activity_log (character_id);

create index if not exists idx_activity_log_actor_discord_id
  on public.activity_log (actor_discord_id);
