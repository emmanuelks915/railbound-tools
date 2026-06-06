-- Website Shops Consolidation v1
-- Makes public.shops the single storefront system going forward.
-- Safe to run more than once.

alter table public.shops
  add column if not exists owner_discord_id bigint,
  add column if not exists owner_character_id uuid;

create index if not exists shops_owner_discord_idx
  on public.shops (guild_id, owner_discord_id);

create index if not exists shops_owner_character_idx
  on public.shops (guild_id, owner_character_id);

update public.shops
set enabled = true
where enabled is null;
