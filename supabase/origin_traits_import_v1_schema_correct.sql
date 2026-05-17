-- Origin Traits Import v1 SCHEMA CORRECT
-- Source: Railbound Trait Guide, Origin Traits section.
-- Matches current public.traits schema:
-- guild_id bigint, name, slug, tier text, cost integer, category, exclusive_group,
-- description, effects_json, requirements_json, is_active.
--
-- Origin Traits:
-- Every character receives one free Origin Trait during character creation.
-- They do not count toward the standard 5 Trait Point limit.
-- They must align with character background and are creation-only.

delete from public.traits
where guild_id = 1462489358908129354
and slug in (
  'origin_imperial_citadel',
  'origin_industrialist_flywheel',
  'origin_zealot_morthand',
  'origin_resilient_cinder',
  'origin_enterprising_gearford',
  'origin_mystic_brassmere',
  'origin_indominable_high_sable',
  'origin_survivalist_thornwick',
  'origin_dauntless_ashgate',
  'origin_erudite_lumenhold',
  'origin_wayfarer',
  'origin_caravaneer',
  'origin_bound'
);

insert into public.traits (
  guild_id,
  name,
  slug,
  tier,
  cost,
  category,
  exclusive_group,
  description,
  effects_json,
  requirements_json,
  is_active
)
values
(
  1462489358908129354,
  'Imperial: Citadel',
  'origin_imperial_citadel',
  'origin',
  0,
  'origin_citystate',
  'origin_trait',
  'Raised amongst bureaucrats, you know order.',
  '{"origin_trait": true, "free_origin_trait": true, "counts_toward_trait_limit": false, "origin_type": "Imperial", "origin_location": "Citadel", "origin_category": "origin_citystate", "free_skill_choice": true, "free_skill_options": ["Local Study", "Historian", "Linguistics"], "knowledge_bonus": "+1", "mechanical_effects": ["Citizenship rights in this origin location.", "May take one of the listed Knowledge skills for free: Local Study, Historian, or Linguistics.", "+1 to all Knowledge checks relating to this origin, including city layout, laws, culture, and traditions.", "May request this origin-related information from GMs/staff to support RP, even if it is not documented."], "notes": "Social impact: citizenship rights.", "source": "Railbound Trait Guide - Origin Traits", "may_require_staff_skill_override": true}'::jsonb,
  '{"staff_approval_required": true, "creation_only": true, "narrative_requirement": true, "requirements": ["Must be selected during character creation.", "Must directly align with the character''s established background.", "Cannot be purchased later.", "Cannot be swapped out.", "Cannot be earned through events.", "Cannot be rewritten after approval."]}'::jsonb,
  true
),
(
  1462489358908129354,
  'Industrialist: Flywheel',
  'origin_industrialist_flywheel',
  'origin',
  0,
  'origin_citystate',
  'origin_trait',
  'You know the value of hard work.',
  '{"origin_trait": true, "free_origin_trait": true, "counts_toward_trait_limit": false, "origin_type": "Industrialist", "origin_location": "Flywheel", "origin_category": "origin_citystate", "free_skill_choice": true, "free_skill_options": ["Steam Engines", "Metallurgy", "Electricity"], "knowledge_bonus": "+1", "mechanical_effects": ["Citizenship rights in this origin location.", "May take one of the listed Knowledge skills for free: Steam Engines, Metallurgy, or Electricity.", "+1 to all Knowledge checks relating to this origin, including city layout, laws, culture, and traditions.", "May request this origin-related information from GMs/staff to support RP, even if it is not documented."], "notes": "Social impact: citizenship rights.", "source": "Railbound Trait Guide - Origin Traits", "may_require_staff_skill_override": true}'::jsonb,
  '{"staff_approval_required": true, "creation_only": true, "narrative_requirement": true, "requirements": ["Must be selected during character creation.", "Must directly align with the character''s established background.", "Cannot be purchased later.", "Cannot be swapped out.", "Cannot be earned through events.", "Cannot be rewritten after approval."]}'::jsonb,
  true
),
(
  1462489358908129354,
  'Zealot: Morthand',
  'origin_zealot_morthand',
  'origin',
  0,
  'origin_citystate',
  'origin_trait',
  'Surrounded by zealots, you were shaped by Morthand''s culture.',
  '{"origin_trait": true, "free_origin_trait": true, "counts_toward_trait_limit": false, "origin_type": "Zealot", "origin_location": "Morthand", "origin_category": "origin_citystate", "free_skill_choice": true, "free_skill_options": ["Catechumen", "Linguistics"], "knowledge_bonus": "+1", "mechanical_effects": ["Citizenship rights in this origin location.", "May take one of the listed Knowledge skills for free: Catechumen or Linguistics.", "+1 to all Knowledge checks relating to this origin, including city layout, laws, culture, and traditions.", "May request this origin-related information from GMs/staff to support RP, even if it is not documented."], "notes": "Social impact: citizenship rights.", "source": "Railbound Trait Guide - Origin Traits", "may_require_staff_skill_override": true}'::jsonb,
  '{"staff_approval_required": true, "creation_only": true, "narrative_requirement": true, "requirements": ["Must be selected during character creation.", "Must directly align with the character''s established background.", "Cannot be purchased later.", "Cannot be swapped out.", "Cannot be earned through events.", "Cannot be rewritten after approval."]}'::jsonb,
  true
),
(
  1462489358908129354,
  'Resilient: Cinder',
  'origin_resilient_cinder',
  'origin',
  0,
  'origin_citystate',
  'origin_trait',
  'Born to rise, you were shaped by Cinder.',
  '{"origin_trait": true, "free_origin_trait": true, "counts_toward_trait_limit": false, "origin_type": "Resilient", "origin_location": "Cinder", "origin_category": "origin_citystate", "free_skill_choice": true, "free_skill_options": ["Geology", "Biology", "Veterinary Studies"], "knowledge_bonus": "+1", "mechanical_effects": ["Citizenship rights in this origin location.", "May take one of the listed Knowledge skills for free: Geology, Biology, or Veterinary Studies.", "+1 to all Knowledge checks relating to this origin, including city layout, laws, culture, and traditions.", "May request this origin-related information from GMs/staff to support RP, even if it is not documented."], "notes": "Social impact: citizenship rights.", "source": "Railbound Trait Guide - Origin Traits", "may_require_staff_skill_override": true}'::jsonb,
  '{"staff_approval_required": true, "creation_only": true, "narrative_requirement": true, "requirements": ["Must be selected during character creation.", "Must directly align with the character''s established background.", "Cannot be purchased later.", "Cannot be swapped out.", "Cannot be earned through events.", "Cannot be rewritten after approval."]}'::jsonb,
  true
),
(
  1462489358908129354,
  'Enterprising: Gearford',
  'origin_enterprising_gearford',
  'origin',
  0,
  'origin_citystate',
  'origin_trait',
  'Growing up amongst silvertongued serpents, you learned how systems, secrets, and trade move.',
  '{"origin_trait": true, "free_origin_trait": true, "counts_toward_trait_limit": false, "origin_type": "Enterprising", "origin_location": "Gearford", "origin_category": "origin_citystate", "free_skill_choice": true, "free_skill_options": ["Codebreaking", "Print Forgery", "Cartography"], "knowledge_bonus": "+1", "mechanical_effects": ["Citizenship rights in this origin location.", "May take one of the listed Knowledge skills for free: Codebreaking, Print Forgery, or Cartography.", "+1 to all Knowledge checks relating to this origin, including city layout, laws, culture, and traditions.", "May request this origin-related information from GMs/staff to support RP, even if it is not documented."], "notes": "Social impact: citizenship rights.", "source": "Railbound Trait Guide - Origin Traits", "may_require_staff_skill_override": true}'::jsonb,
  '{"staff_approval_required": true, "creation_only": true, "narrative_requirement": true, "requirements": ["Must be selected during character creation.", "Must directly align with the character''s established background.", "Cannot be purchased later.", "Cannot be swapped out.", "Cannot be earned through events.", "Cannot be rewritten after approval."]}'::jsonb,
  true
),
(
  1462489358908129354,
  'Mystic: Brassmere',
  'origin_mystic_brassmere',
  'origin',
  0,
  'origin_citystate',
  'origin_trait',
  'A child of the fog, you were shaped by Brassmere''s mysteries.',
  '{"origin_trait": true, "free_origin_trait": true, "counts_toward_trait_limit": false, "origin_type": "Mystic", "origin_location": "Brassmere", "origin_category": "origin_citystate", "free_skill_choice": true, "free_skill_options": ["Chemistry", "Biology", "Catechumen"], "knowledge_bonus": "+1", "mechanical_effects": ["Citizenship rights in this origin location.", "May take one of the listed Knowledge skills for free: Chemistry, Biology, or Catechumen.", "+1 to all Knowledge checks relating to this origin, including city layout, laws, culture, and traditions.", "May request this origin-related information from GMs/staff to support RP, even if it is not documented."], "notes": "Social impact: citizenship rights.", "source": "Railbound Trait Guide - Origin Traits", "may_require_staff_skill_override": true}'::jsonb,
  '{"staff_approval_required": true, "creation_only": true, "narrative_requirement": true, "requirements": ["Must be selected during character creation.", "Must directly align with the character''s established background.", "Cannot be purchased later.", "Cannot be swapped out.", "Cannot be earned through events.", "Cannot be rewritten after approval."]}'::jsonb,
  true
),
(
  1462489358908129354,
  'Indominable: High Sable',
  'origin_indominable_high_sable',
  'origin',
  0,
  'origin_citystate',
  'origin_trait',
  'You were forged by militants and shaped by High Sable.',
  '{"origin_trait": true, "free_origin_trait": true, "counts_toward_trait_limit": false, "origin_type": "Indominable", "origin_location": "High Sable", "origin_category": "origin_citystate", "free_skill_choice": true, "free_skill_options": ["Martial Historian", "Metallurgy", "Doranswyr Historian"], "knowledge_bonus": "+1", "mechanical_effects": ["Citizenship rights in this origin location.", "May take one of the listed Knowledge skills for free: Martial Historian, Metallurgy, or Doranswyr Historian.", "+1 to all Knowledge checks relating to this origin, including city layout, laws, culture, and traditions.", "May request this origin-related information from GMs/staff to support RP, even if it is not documented."], "notes": "Source spelling is Indominable.", "source": "Railbound Trait Guide - Origin Traits", "may_require_staff_skill_override": true}'::jsonb,
  '{"staff_approval_required": true, "creation_only": true, "narrative_requirement": true, "requirements": ["Must be selected during character creation.", "Must directly align with the character''s established background.", "Cannot be purchased later.", "Cannot be swapped out.", "Cannot be earned through events.", "Cannot be rewritten after approval."]}'::jsonb,
  true
),
(
  1462489358908129354,
  'Survivalist: Thornwick',
  'origin_survivalist_thornwick',
  'origin',
  0,
  'origin_citystate',
  'origin_trait',
  'You know how to make do with little.',
  '{"origin_trait": true, "free_origin_trait": true, "counts_toward_trait_limit": false, "origin_type": "Survivalist", "origin_location": "Thornwick", "origin_category": "origin_citystate", "free_skill_choice": true, "free_skill_options": ["Geology", "Biology", "Catechumen"], "knowledge_bonus": "+1", "mechanical_effects": ["Citizenship rights in this origin location.", "May take one of the listed Knowledge skills for free: Geology, Biology, or Catechumen.", "+1 to all Knowledge checks relating to this origin, including city layout, laws, culture, and traditions.", "May request this origin-related information from GMs/staff to support RP, even if it is not documented."], "notes": "Social impact: citizenship rights.", "source": "Railbound Trait Guide - Origin Traits", "may_require_staff_skill_override": true}'::jsonb,
  '{"staff_approval_required": true, "creation_only": true, "narrative_requirement": true, "requirements": ["Must be selected during character creation.", "Must directly align with the character''s established background.", "Cannot be purchased later.", "Cannot be swapped out.", "Cannot be earned through events.", "Cannot be rewritten after approval."]}'::jsonb,
  true
),
(
  1462489358908129354,
  'Dauntless: Ashgate',
  'origin_dauntless_ashgate',
  'origin',
  0,
  'origin_citystate',
  'origin_trait',
  'You are fearless and shaped by Ashgate.',
  '{"origin_trait": true, "free_origin_trait": true, "counts_toward_trait_limit": false, "origin_type": "Dauntless", "origin_location": "Ashgate", "origin_category": "origin_citystate", "free_skill_choice": true, "free_skill_options": ["Physics", "Chemistry", "Martial Historian"], "knowledge_bonus": "+1", "mechanical_effects": ["Citizenship rights in this origin location.", "May take one of the listed Knowledge skills for free: Physics, Chemistry, or Martial Historian.", "+1 to all Knowledge checks relating to this origin, including city layout, laws, culture, and traditions.", "May request this origin-related information from GMs/staff to support RP, even if it is not documented."], "notes": "Social impact: citizenship rights.", "source": "Railbound Trait Guide - Origin Traits", "may_require_staff_skill_override": true}'::jsonb,
  '{"staff_approval_required": true, "creation_only": true, "narrative_requirement": true, "requirements": ["Must be selected during character creation.", "Must directly align with the character''s established background.", "Cannot be purchased later.", "Cannot be swapped out.", "Cannot be earned through events.", "Cannot be rewritten after approval."]}'::jsonb,
  true
),
(
  1462489358908129354,
  'Erudite: Lumenhold',
  'origin_erudite_lumenhold',
  'origin',
  0,
  'origin_citystate',
  'origin_trait',
  'You were educated and shaped by Lumenhold.',
  '{"origin_trait": true, "free_origin_trait": true, "counts_toward_trait_limit": false, "origin_type": "Erudite", "origin_location": "Lumenhold", "origin_category": "origin_citystate", "free_skill_choice": true, "free_skill_options": ["Mathematics", "Linguistics", "Doranswyr Historian"], "knowledge_bonus": "+1", "mechanical_effects": ["Citizenship rights in this origin location.", "May take one of the listed Knowledge skills for free: Mathematics, Linguistics, or Doranswyr Historian.", "+1 to all Knowledge checks relating to this origin, including city layout, laws, culture, and traditions.", "May request this origin-related information from GMs/staff to support RP, even if it is not documented."], "notes": "Social impact: citizenship rights.", "source": "Railbound Trait Guide - Origin Traits", "may_require_staff_skill_override": true}'::jsonb,
  '{"staff_approval_required": true, "creation_only": true, "narrative_requirement": true, "requirements": ["Must be selected during character creation.", "Must directly align with the character''s established background.", "Cannot be purchased later.", "Cannot be swapped out.", "Cannot be earned through events.", "Cannot be rewritten after approval."]}'::jsonb,
  true
),
(
  1462489358908129354,
  'Wayfarer',
  'origin_wayfarer',
  'origin',
  0,
  'origin_outsider',
  'origin_trait',
  'You grew up an outcast, bandit, or child of an exile, not tolerated within any city-state.',
  '{"origin_trait": true, "free_origin_trait": true, "counts_toward_trait_limit": false, "origin_type": "Wayfarer", "origin_location": null, "origin_category": "origin_outsider", "free_skill_choice": true, "free_skill_options": ["Local Study: City States", "Print Forgery", "Cartography"], "knowledge_bonus": "+1", "mechanical_effects": ["Recognition amongst thieves, poachers, and outlaws.", "May take one of the listed Knowledge skills for free: Local Study: City States, Print Forgery, or Cartography.", "You share kinship with outlaws and have a better chance to persuade or intimidate them.", "+1 to all Knowledge checks relating to this origin, including bandits, thieves'' codes, and poaching areas.", "May request this origin-related information from GMs/staff to support RP, even if it is not documented."], "notes": "No city-state citizenship; outsider origin.", "source": "Railbound Trait Guide - Origin Traits", "may_require_staff_skill_override": true}'::jsonb,
  '{"staff_approval_required": true, "creation_only": true, "narrative_requirement": true, "requirements": ["Must be selected during character creation.", "Must directly align with the character''s established background.", "Cannot be purchased later.", "Cannot be swapped out.", "Cannot be earned through events.", "Cannot be rewritten after approval."]}'::jsonb,
  true
),
(
  1462489358908129354,
  'Caravaneer',
  'origin_caravaneer',
  'origin',
  0,
  'origin_traveling',
  'origin_trait',
  'You grew up a child of a merchant or troupe, vaguely tolerated for short periods within city-states.',
  '{"origin_trait": true, "free_origin_trait": true, "counts_toward_trait_limit": false, "origin_type": "Caravaneer", "origin_location": null, "origin_category": "origin_traveling", "free_skill_choice": true, "free_skill_options": ["Local Study: City States", "Linguistics", "Cartography"], "knowledge_bonus": "+1", "mechanical_effects": ["Friendly disposition from caravaneers.", "May take one of the listed Knowledge skills for free: Local Study: City States, Linguistics, or Cartography.", "You find it easier to deal with traveling troubles and merchants, and can convince them to trust you more.", "+1 to all Knowledge checks relating to this origin, including routes, city laws, and trade preferences.", "May request this origin-related information from GMs/staff to support RP, even if it is not documented."], "notes": "Traveling origin.", "source": "Railbound Trait Guide - Origin Traits", "may_require_staff_skill_override": true}'::jsonb,
  '{"staff_approval_required": true, "creation_only": true, "narrative_requirement": true, "requirements": ["Must be selected during character creation.", "Must directly align with the character''s established background.", "Cannot be purchased later.", "Cannot be swapped out.", "Cannot be earned through events.", "Cannot be rewritten after approval."]}'::jsonb,
  true
),
(
  1462489358908129354,
  'Bound',
  'origin_bound',
  'origin',
  0,
  'origin_guild',
  'origin_trait',
  'You grew up a child born or raised within one of the mercenary companies, with no ties to anyone else.',
  '{"origin_trait": true, "free_origin_trait": true, "counts_toward_trait_limit": false, "origin_type": "Bound", "origin_location": null, "origin_category": "origin_guild", "free_skill_choice": true, "free_skill_options": ["Local Study: City States", "Doranswyr Historian", "Martial Historian"], "knowledge_bonus": "+1", "mechanical_effects": ["Recognized by Guild NPCs.", "May take one of the listed Knowledge skills for free: Local Study: City States, Doranswyr Historian, or Martial Historian.", "Your glory, merits, and infamy impact you more, as Guild elders know who raised you.", "+1 to all Knowledge checks relating to this origin, including traditions, history, politics, and important NPCs.", "May request this origin-related information from GMs/staff to support RP, even if it is not documented."], "notes": "Mercenary company / guild-raised origin.", "source": "Railbound Trait Guide - Origin Traits", "may_require_staff_skill_override": true}'::jsonb,
  '{"staff_approval_required": true, "creation_only": true, "narrative_requirement": true, "requirements": ["Must be selected during character creation.", "Must directly align with the character''s established background.", "Cannot be purchased later.", "Cannot be swapped out.", "Cannot be earned through events.", "Cannot be rewritten after approval."]}'::jsonb,
  true
);

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
  and slug in (
    'origin_imperial_citadel',
    'origin_industrialist_flywheel',
    'origin_zealot_morthand',
    'origin_resilient_cinder',
    'origin_enterprising_gearford',
    'origin_mystic_brassmere',
    'origin_indominable_high_sable',
    'origin_survivalist_thornwick',
    'origin_dauntless_ashgate',
    'origin_erudite_lumenhold',
    'origin_wayfarer',
    'origin_caravaneer',
    'origin_bound'
  )
order by name;
