-- Optional Staff Trait Grant Log v1
create table if not exists public.staff_trait_grant_log (
  log_id uuid primary key default gen_random_uuid(),
  guild_id bigint not null,
  character_id uuid not null,
  trait_id uuid not null,
  action text not null check (action in ('grant', 'remove')),
  staff_discord_id bigint,
  reason text not null,
  created_at timestamptz not null default now()
);

create index if not exists staff_trait_grant_log_character_idx
  on public.staff_trait_grant_log (guild_id, character_id, created_at desc);
