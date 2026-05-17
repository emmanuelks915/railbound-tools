-- Reliable Traits Import v1 SCHEMA CORRECT
-- Source: Railbound Trait Guide, Reliable Traits section.
-- Matches current public.traits schema:
-- guild_id bigint, name, slug, tier text, cost integer, category, exclusive_group,
-- description, effects_json, requirements_json, is_active.
--
-- traits.tier check allows: origin, minor, reliable, keystone, negative.
-- Therefore all two-point reliable traits use tier = 'reliable' and cost = 2.

delete from public.traits
where guild_id = 1462489358908129354
and slug in (
  'field_medic',
  'tactician',
  'smuggler',
  'politician',
  'adrenaline_junky',
  'knowledgeable',
  'natural_leader',
  'well_known_family',
  'crowd_sense',
  'hardy_constitution',
  'inner_light',
  'amateur_historian',
  'artist',
  'animal_lover',
  'chef',
  'botanist',
  'logistics_mind',
  'silver_ear',
  'enhanced_physique',
  'merlins_skill'
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
  'Special Subclass || Field Medic',
  'field_medic',
  'reliable',
  2,
  'subclass',
  null,
  'You possess practical medical training focused on treating injuries without the use of magic.',
  '{"reliable_tier": 2, "point_value": 2, "mechanical_effects": ["Can heal and stabilize injured allies without magic.", "Improved effectiveness when treating physical wounds.", "Access to non-magical medical supplies and techniques.", "Can reduce recovery time through proper care."], "incompatible_traits": [], "notes": "Reliable special subclass.", "source": "Railbound Trait Guide - Reliable Traits", "special_subclass": true}'::jsonb,
  '{"staff_approval_required": true, "requirements": []}'::jsonb,
  true
),
(
  1462489358908129354,
  'Special Subclass || Tactician',
  'tactician',
  'reliable',
  2,
  'subclass',
  null,
  'You specialize in battlefield control, coordination, and strategic awareness, guiding allies to perform at their highest potential.',
  '{"reliable_tier": 2, "point_value": 2, "mechanical_effects": ["Can issue tactical commands that improve ally coordination and effectiveness.", "Enhanced awareness of battlefield positioning, threats, and enemy movement.", "Access to tracking, mapping, and strategic planning skills.", "Can influence combat flow through positioning, callouts, and decision-making."], "incompatible_traits": [], "notes": "Reliable special subclass.", "source": "Railbound Trait Guide - Reliable Traits", "special_subclass": true}'::jsonb,
  '{"staff_approval_required": true, "requirements": []}'::jsonb,
  true
),
(
  1462489358908129354,
  'Special Subclass || Smuggler',
  'smuggler',
  'reliable',
  2,
  'subclass',
  null,
  'You operate outside of systems, specializing in moving goods, information, and people through restricted or dangerous spaces.',
  '{"reliable_tier": 2, "point_value": 2, "mechanical_effects": ["Can conceal and transport items without detection.", "Access to hidden routes, black market dealings, and underground networks.", "Improved success in high-risk, high-reward trade and delivery situations.", "Can bypass restrictions, avoid authority, and operate in secrecy."], "incompatible_traits": [], "notes": "Reliable special subclass.", "source": "Railbound Trait Guide - Reliable Traits", "special_subclass": true}'::jsonb,
  '{"staff_approval_required": true, "requirements": []}'::jsonb,
  true
),
(
  1462489358908129354,
  'Special Subclass || Politician',
  'politician',
  'reliable',
  2,
  'subclass',
  null,
  'You specialize in influence, negotiation, and manipulating outcomes through financial and social influence.',
  '{"reliable_tier": 2, "point_value": 2, "mechanical_effects": ["Can persuade, negotiate, and influence NPCs more effectively.", "Access to networks, connections, and reputation-based advantages.", "Passive income opportunities through deals, influence, and investments.", "Can control or shift outcomes in social and economic situations."], "incompatible_traits": [], "notes": "Reliable special subclass.", "source": "Railbound Trait Guide - Reliable Traits", "special_subclass": true}'::jsonb,
  '{"staff_approval_required": true, "requirements": []}'::jsonb,
  true
),
(
  1462489358908129354,
  'Adrenaline Junky',
  'adrenaline_junky',
  'reliable',
  2,
  'injury',
  null,
  'You seek out the thrill of danger and doing things that could get you hurt.',
  '{"reliable_tier": 2, "point_value": 2, "mechanical_effects": ["Based on injuries listed, gain an output boost, but only for a singular injury.", "Tier 1 injury: +1% output.", "Tier 2 injury: +1.5% output.", "Tier 3 injury: +2% output.", "Tier 4 injury: +2.5% output."], "incompatible_traits": [], "notes": "Source spelling is ''Junky''; imported as written.", "source": "Railbound Trait Guide - Reliable Traits"}'::jsonb,
  '{"staff_approval_required": true, "requirements": []}'::jsonb,
  true
),
(
  1462489358908129354,
  'Knowledgeable',
  'knowledgeable',
  'reliable',
  2,
  'knowledge',
  null,
  'You are broadly knowledgeable and trained across knowledge skills.',
  '{"reliable_tier": 2, "point_value": 2, "mechanical_effects": ["+3 to all Knowledge Skills. Stacks even with tiered skills."], "incompatible_traits": [], "notes": "", "source": "Railbound Trait Guide - Reliable Traits"}'::jsonb,
  '{"staff_approval_required": true, "requirements": []}'::jsonb,
  true
),
(
  1462489358908129354,
  'Natural Leader',
  'natural_leader',
  'reliable',
  2,
  'social',
  null,
  'You have a dependable social presence and can lead others effectively.',
  '{"reliable_tier": 2, "point_value": 2, "mechanical_effects": ["+3 to all social skills. Stacks even with tiered skills."], "incompatible_traits": [], "notes": "", "source": "Railbound Trait Guide - Reliable Traits"}'::jsonb,
  '{"staff_approval_required": true, "requirements": ["Requires either Charming or Threatening."]}'::jsonb,
  true
),
(
  1462489358908129354,
  'Well-Known Family',
  'well_known_family',
  'reliable',
  2,
  'social',
  null,
  'While still middle class, you come from a decent family or family business, bringing certain perks.',
  '{"reliable_tier": 2, "point_value": 2, "mechanical_effects": ["+3 on rolls dealing with your family''s business or what it deals with.", "Start with +150 crowns or start with a small-scale business based on your family."], "incompatible_traits": [], "notes": "", "source": "Railbound Trait Guide - Reliable Traits"}'::jsonb,
  '{"staff_approval_required": true, "requirements": ["Family business/details should be recorded on approval."]}'::jsonb,
  true
),
(
  1462489358908129354,
  'Crowd Sense',
  'crowd_sense',
  'reliable',
  2,
  'perception',
  null,
  'An upgraded form of Perceptive, specialized for groups.',
  '{"reliable_tier": 2, "point_value": 2, "mechanical_effects": ["+3 to all perception rolls with groups."], "incompatible_traits": [], "notes": "", "source": "Railbound Trait Guide - Reliable Traits"}'::jsonb,
  '{"staff_approval_required": true, "requirements": ["Requires Perceptive."]}'::jsonb,
  true
),
(
  1462489358908129354,
  'Hardy Constitution',
  'hardy_constitution',
  'reliable',
  2,
  'injury',
  null,
  'You recover unusually well from serious permanent injuries.',
  '{"reliable_tier": 2, "point_value": 2, "mechanical_effects": ["Roll 1d20 on any permanent Tier 3+ injury.", "1-9: No change.", "10-15: Permanent effects self-heal 1 month after the injury does.", "16+: Injury self-heals in the normal time without permanent scarring.", "Does not regrow parts that are actually missing, but eliminates secondary penalties."], "incompatible_traits": [], "notes": "", "source": "Railbound Trait Guide - Reliable Traits"}'::jsonb,
  '{"staff_approval_required": true, "requirements": ["Requires Bear''s Fortitude."]}'::jsonb,
  true
),
(
  1462489358908129354,
  'Inner Light',
  'inner_light',
  'reliable',
  2,
  'support',
  null,
  'You seem to have an energy about you that lights a room up.',
  '{"reliable_tier": 2, "point_value": 2, "mechanical_effects": ["You can give an ally your modifiers on skill or knowledge rolls."], "incompatible_traits": [], "notes": "Source says requires the Lucky Trait; mapped to Lucky Spark based on current minor trait name.", "source": "Railbound Trait Guide - Reliable Traits"}'::jsonb,
  '{"staff_approval_required": true, "requirements": ["Requires Lucky Spark."]}'::jsonb,
  true
),
(
  1462489358908129354,
  'Amateur Historian',
  'amateur_historian',
  'reliable',
  2,
  'knowledge',
  null,
  'You have strong knowledge of history, politics, and current events.',
  '{"reliable_tier": 2, "point_value": 2, "mechanical_effects": ["+3 to all history, political, and current event checks. Stacks with related skills."], "incompatible_traits": [], "notes": "", "source": "Railbound Trait Guide - Reliable Traits"}'::jsonb,
  '{"staff_approval_required": true, "requirements": []}'::jsonb,
  true
),
(
  1462489358908129354,
  'Artist',
  'artist',
  'reliable',
  2,
  'art',
  null,
  'You are skilled in art and theatre-based work.',
  '{"reliable_tier": 2, "point_value": 2, "mechanical_effects": ["+3 to all art and theatre-based checks. Stacks with related skills."], "incompatible_traits": [], "notes": "", "source": "Railbound Trait Guide - Reliable Traits"}'::jsonb,
  '{"staff_approval_required": true, "requirements": []}'::jsonb,
  true
),
(
  1462489358908129354,
  'Animal Lover',
  'animal_lover',
  'reliable',
  2,
  'animal',
  null,
  'You have broad knowledge and familiarity with animals.',
  '{"reliable_tier": 2, "point_value": 2, "mechanical_effects": ["+3 to all animal type and species checks. Stacks with related skills."], "incompatible_traits": [], "notes": "", "source": "Railbound Trait Guide - Reliable Traits"}'::jsonb,
  '{"staff_approval_required": true, "requirements": []}'::jsonb,
  true
),
(
  1462489358908129354,
  'Chef',
  'chef',
  'reliable',
  2,
  'craft',
  null,
  'You are skilled in cooking, baking, and etiquette-based work.',
  '{"reliable_tier": 2, "point_value": 2, "mechanical_effects": ["+3 to all baking, cooking, and etiquette-based checks. Stacks with related skills."], "incompatible_traits": [], "notes": "", "source": "Railbound Trait Guide - Reliable Traits"}'::jsonb,
  '{"staff_approval_required": true, "requirements": []}'::jsonb,
  true
),
(
  1462489358908129354,
  'Botanist',
  'botanist',
  'reliable',
  2,
  'nature',
  null,
  'You are skilled in gathering, cultivating, and understanding plants.',
  '{"reliable_tier": 2, "point_value": 2, "mechanical_effects": ["+3 to all gathering, cultivating, and plant-based knowledge checks. Stacks with related skills."], "incompatible_traits": [], "notes": "", "source": "Railbound Trait Guide - Reliable Traits"}'::jsonb,
  '{"staff_approval_required": true, "requirements": []}'::jsonb,
  true
),
(
  1462489358908129354,
  'Logistics Mind',
  'logistics_mind',
  'reliable',
  2,
  'economy',
  null,
  'You are efficient with purchases, logistics, and value.',
  '{"reliable_tier": 2, "point_value": 2, "mechanical_effects": ["5% discount on items and services bought from NPC stores."], "incompatible_traits": ["Big Spender"], "notes": "Incompatible with Big Spender based on negative trait rules.", "source": "Railbound Trait Guide - Reliable Traits"}'::jsonb,
  '{"staff_approval_required": true, "requirements": []}'::jsonb,
  true
),
(
  1462489358908129354,
  'Silver Ear',
  'silver_ear',
  'reliable',
  2,
  'perception',
  null,
  'An upgraded form of Perceptive, specialized in seeking lies and deception.',
  '{"reliable_tier": 2, "point_value": 2, "mechanical_effects": ["+3 Perception to detect lies, half-truths, or evasion, or may request GM hints."], "incompatible_traits": [], "notes": "", "source": "Railbound Trait Guide - Reliable Traits"}'::jsonb,
  '{"staff_approval_required": true, "requirements": ["Requires Perceptive."]}'::jsonb,
  true
),
(
  1462489358908129354,
  'Enhanced Physique',
  'enhanced_physique',
  'reliable',
  2,
  'stat',
  null,
  'You refine an existing physical stat-boosting trait into stronger practical performance.',
  '{"reliable_tier": 2, "point_value": 2, "mechanical_effects": ["+3 for all rolls involving Strength or Dexterity respectively."], "incompatible_traits": [], "notes": "Source says access comes from Gorilla Strength or Cat''s Grace.", "source": "Railbound Trait Guide - Reliable Traits"}'::jsonb,
  '{"staff_approval_required": true, "requirements": ["Requires either Gorilla Strength or Cat''s Grace."]}'::jsonb,
  true
),
(
  1462489358908129354,
  'Merlin''s Skill',
  'merlins_skill',
  'reliable',
  2,
  'stat',
  null,
  'You refine an existing magical stat-boosting trait into a stronger boost.',
  '{"reliable_tier": 2, "point_value": 2, "mechanical_effects": ["Depending on whether you have Dragon''s Insight or Leviathan Depth, the matching stat is raised.", "The 5% boost becomes 10% for either Magic Affinity or Mana.", "The boost affects the total; the final amount should be written in parentheses, e.g. 100 (110)."], "incompatible_traits": [], "notes": "Source references Leviathans Depth; mapped to Leviathan Depth.", "source": "Railbound Trait Guide - Reliable Traits"}'::jsonb,
  '{"staff_approval_required": true, "requirements": ["Requires either Dragon''s Insight or Leviathan Depth."]}'::jsonb,
  true
);

select
  slug,
  name,
  tier,
  cost,
  category,
  effects_json->>'reliable_tier' as reliable_tier,
  effects_json->>'point_value' as point_value,
  is_active
from public.traits
where guild_id = 1462489358908129354
  and tier = 'reliable'
  and slug in (
    'field_medic',
    'tactician',
    'smuggler',
    'politician',
    'adrenaline_junky',
    'knowledgeable',
    'natural_leader',
    'well_known_family',
    'crowd_sense',
    'hardy_constitution',
    'inner_light',
    'amateur_historian',
    'artist',
    'animal_lover',
    'chef',
    'botanist',
    'logistics_mind',
    'silver_ear',
    'enhanced_physique',
    'merlins_skill'
  )
order by name;
