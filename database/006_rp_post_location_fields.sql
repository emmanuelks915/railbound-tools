-- 006_rp_post_location_fields.sql
-- Adds durable RP location fields so Citizen Registry can show where RP happened
-- without guessing from old messages.

alter table if exists public.rp_posts
  add column if not exists channel_name text,
  add column if not exists thread_id text,
  add column if not exists thread_name text,
  add column if not exists parent_channel_id text,
  add column if not exists parent_channel_name text,
  add column if not exists location_name text;

alter table if exists public.rp_messages
  add column if not exists channel_name text,
  add column if not exists thread_id text,
  add column if not exists thread_name text,
  add column if not exists parent_channel_id text,
  add column if not exists parent_channel_name text,
  add column if not exists location_name text;

alter table if exists public.rp_activity
  add column if not exists channel_name text,
  add column if not exists thread_id text,
  add column if not exists thread_name text,
  add column if not exists parent_channel_id text,
  add column if not exists parent_channel_name text,
  add column if not exists location_name text;

alter table if exists public.rp_logs
  add column if not exists channel_name text,
  add column if not exists thread_id text,
  add column if not exists thread_name text,
  add column if not exists parent_channel_id text,
  add column if not exists parent_channel_name text,
  add column if not exists location_name text;

create index if not exists idx_rp_posts_channel_id on public.rp_posts(channel_id);
create index if not exists idx_rp_posts_thread_id on public.rp_posts(thread_id);
create index if not exists idx_rp_messages_channel_id on public.rp_messages(channel_id);
create index if not exists idx_rp_activity_channel_id on public.rp_activity(channel_id);
create index if not exists idx_rp_logs_channel_id on public.rp_logs(channel_id);
