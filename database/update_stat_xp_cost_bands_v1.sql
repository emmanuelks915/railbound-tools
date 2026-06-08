-- Update Stat XP Cost Bands v1
-- New Railbound stat-buying costs:
-- 0-50: 1 XP
-- 51-150: 2 XP
-- 151-250: 4 XP
-- 251-350: 6 XP
-- 351-450: 8 XP
-- 451-550: 10 XP
-- 551-650: 12 XP
-- 651-750: 14 XP
--
-- Run this in Supabase SQL Editor.
-- It updates the table used by:
-- public.calculate_stat_upgrade_cost(...)
-- public.submit_stat_upgrade_request(...)
-- public.approve_stat_upgrade_request(...)

begin;

delete from public.stat_xp_cost_bands
where (stat_key is null or stat_key in ('strength', 'dexterity', 'stamina', 'magic_affinity', 'mana'))
  and min_value >= 0
  and max_value <= 750;

insert into public.stat_xp_cost_bands
  (stat_key, min_value, max_value, cost_per_point)
values
  (null, 0,   50,  1),
  (null, 51,  150, 2),
  (null, 151, 250, 4),
  (null, 251, 350, 6),
  (null, 351, 450, 8),
  (null, 451, 550, 10),
  (null, 551, 650, 12),
  (null, 651, 750, 14);

notify pgrst, 'reload schema';

commit;

-- Optional sanity checks:
-- 10 -> 50 should cost 40
select public.calculate_stat_upgrade_cost('strength', 10, 50) as cost_10_to_50;

-- 45 -> 55 should cost 15
select public.calculate_stat_upgrade_cost('strength', 45, 55) as cost_45_to_55;

-- 10 -> 150 should cost 240
select public.calculate_stat_upgrade_cost('strength', 10, 150) as cost_10_to_150;
