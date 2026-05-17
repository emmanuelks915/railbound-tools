-- Cleanup Duplicate Origin Traits
-- Removes old/legacy origin trait rows that do not use the new origin_* slug format.
-- Keeps the clean imported rows from origin_traits_import_v1_schema_correct.sql.

delete from public.traits
where guild_id = 1462489358908129354
  and tier = 'origin'
  and slug not like 'origin_%';

-- Verify: should return exactly 13 rows, no duplicates.
select
  slug,
  name,
  tier,
  cost,
  category,
  exclusive_group,
  effects_json->>'origin_type' as origin_type,
  effects_json->>'origin_location' as origin_location,
  effects_json->>'counts_toward_trait_limit' as counts_toward_trait_limit,
  is_active
from public.traits
where guild_id = 1462489358908129354
  and tier = 'origin'
order by name;
