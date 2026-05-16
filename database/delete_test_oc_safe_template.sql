-- Safe Test OC Cleanup Template
-- 1. First find the test OC you want to delete:

select
  character_id,
  guild_id,
  user_id,
  name,
  created_at
from public.characters
where name ilike '%test%'
order by created_at desc;

-- 2. Copy the character_id you want to delete.
-- 3. Paste it below, replacing PASTE_CHARACTER_UUID_HERE.
-- 4. Run the DO block.

do $$
declare
  v_character_id uuid := 'PASTE_CHARACTER_UUID_HERE';
begin
  if to_regclass('public.character_traits') is not null then
    delete from public.character_traits where character_id = v_character_id;
  end if;

  if to_regclass('public.oc_traits') is not null then
    delete from public.oc_traits where character_id = v_character_id;
  end if;

  if to_regclass('public.character_skills') is not null then
    delete from public.character_skills where character_id = v_character_id;
  end if;

  if to_regclass('public.oc_skills') is not null then
    delete from public.oc_skills where character_id = v_character_id;
  end if;

  if to_regclass('public.character_inventory') is not null then
    delete from public.character_inventory where character_id = v_character_id;
  end if;

  if to_regclass('public.oc_inventory') is not null then
    delete from public.oc_inventory where character_id = v_character_id;
  end if;

  if to_regclass('public.wallets') is not null then
    delete from public.wallets where character_id = v_character_id;
  end if;

  if to_regclass('public.transactions') is not null then
    delete from public.transactions where character_id = v_character_id;
  end if;

  if to_regclass('public.oc_xp_transactions') is not null then
    delete from public.oc_xp_transactions where character_id = v_character_id;
  end if;

  if to_regclass('public.stat_requests') is not null then
    delete from public.stat_requests where character_id = v_character_id;
  end if;

  if to_regclass('public.skill_requests') is not null then
    delete from public.skill_requests where character_id = v_character_id;
  end if;

  if to_regclass('public.rp_posts') is not null then
    delete from public.rp_posts where character_id = v_character_id;
  end if;

  delete from public.characters where character_id = v_character_id;
end $$;

-- 5. Confirm it is gone:

select character_id, name
from public.characters
where character_id = 'PASTE_CHARACTER_UUID_HERE';
