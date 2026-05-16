-- 007_character_public_profile_fields.sql
-- Player-facing Citizen Registry profile fields.
-- Run this in Supabase SQL Editor before testing the profile editor.

alter table if exists public.characters
  add column if not exists occupation text,
  add column if not exists affiliation text,
  add column if not exists sheet_url text,
  add column if not exists portrait_url text,
  add column if not exists blurb text;

create index if not exists idx_characters_occupation on public.characters(occupation);
create index if not exists idx_characters_affiliation on public.characters(affiliation);
