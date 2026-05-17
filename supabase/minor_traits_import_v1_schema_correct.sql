-- Minor Traits Import v1 SCHEMA CORRECT
-- Source: Railbound Trait Guide, Minor Traits section.
-- Matches current public.traits schema:
-- guild_id bigint, name, slug, tier text, cost integer, category, exclusive_group,
-- description, effects_json, requirements_json, is_active.
--
-- traits.tier check allows: origin, minor, reliable, keystone, negative.
-- Therefore all one-point minor traits use tier = 'minor' and cost = 1.

delete from public.traits
where guild_id = 1462489358908129354
and slug in (
  'magic_background',
  'beast_handler',
  'salesman',
  'lucky_spark',
  'actor',
  'charming',
  'threatening',
  'sixth_sense',
  'hustler',
  'conscientious',
  'natural_performer',
  'pack_mule',
  'perceptive',
  'light_foot',
  'dragons_insight',
  'leviathan_depth',
  'gorilla_strength',
  'cats_grace',
  'bears_fortitude'
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
  'Magic Background',
  'magic_background',
  'minor',
  1,
  'magic',
  null,
  'You have had schooling in magic, or come from a family with access to their circuits.',
  '{"minor_tier": 1, "point_value": 1, "mechanical_effects": ["With Mana Circuits: You may select one Magic School skill as a free skill.", "All others: You gain the ability to use force-enchanted tools as a free skill."], "incompatible_traits": [], "notes": "This trait can grant a free skill and may require staff override/approval when assigning that skill.", "source": "Railbound Trait Guide - Minor Traits", "grants_free_skill": true, "free_skill_options": ["With Mana Circuits: one Magic School skill", "Without Mana Circuits: force-enchanted tools access"], "may_require_staff_skill_override": true}'::jsonb,
  '{"staff_approval_required": true, "requirements": []}'::jsonb,
  true
),
(
  1462489358908129354,
  'Beast Handler',
  'beast_handler',
  'minor',
  1,
  'animal',
  null,
  'You are especially good at dealing with animals, friendly or not.',
  '{"minor_tier": 1, "point_value": 1, "mechanical_effects": ["+1 to all rolls dealing with animal handling."], "incompatible_traits": [], "notes": "Cleaned source wording: friendling -> friendly.", "source": "Railbound Trait Guide - Minor Traits"}'::jsonb,
  '{"staff_approval_required": true, "requirements": []}'::jsonb,
  true
),
(
  1462489358908129354,
  'Salesman',
  'salesman',
  'minor',
  1,
  'economy',
  null,
  'You are better than average at selling objects to NPCs.',
  '{"minor_tier": 1, "point_value": 1, "mechanical_effects": ["When selling objects to an NPC, you make 1.2x more than the average person would."], "incompatible_traits": [], "notes": "", "source": "Railbound Trait Guide - Minor Traits"}'::jsonb,
  '{"staff_approval_required": true, "requirements": []}'::jsonb,
  true
),
(
  1462489358908129354,
  'Lucky Spark',
  'lucky_spark',
  'minor',
  1,
  'stat',
  null,
  'You have a small natural spark of luck.',
  '{"minor_tier": 1, "point_value": 1, "mechanical_effects": ["+1 Luck."], "incompatible_traits": ["Unlucky"], "notes": "", "source": "Railbound Trait Guide - Minor Traits"}'::jsonb,
  '{"staff_approval_required": true, "requirements": []}'::jsonb,
  true
),
(
  1462489358908129354,
  'Actor',
  'actor',
  'minor',
  1,
  'social',
  null,
  'You are skilled at deception, lying, and performing under disguise.',
  '{"minor_tier": 1, "point_value": 1, "mechanical_effects": ["+1 to deception and lying.", "+2 when in disguise."], "incompatible_traits": [], "notes": "", "source": "Railbound Trait Guide - Minor Traits"}'::jsonb,
  '{"staff_approval_required": true, "requirements": []}'::jsonb,
  true
),
(
  1462489358908129354,
  'Charming',
  'charming',
  'minor',
  1,
  'social',
  null,
  'You are naturally persuasive and socially graceful.',
  '{"minor_tier": 1, "point_value": 1, "mechanical_effects": ["+1 on social persuasion, charm, and negotiation."], "incompatible_traits": ["Threatening"], "notes": "Cannot have Threatening.", "source": "Railbound Trait Guide - Minor Traits"}'::jsonb,
  '{"staff_approval_required": true, "requirements": []}'::jsonb,
  true
),
(
  1462489358908129354,
  'Threatening',
  'threatening',
  'minor',
  1,
  'social',
  null,
  'You carry an intimidating or dangerous presence.',
  '{"minor_tier": 1, "point_value": 1, "mechanical_effects": ["+1 on intimidation, bluffing, and extortion."], "incompatible_traits": ["Charming"], "notes": "Cannot have Charming.", "source": "Railbound Trait Guide - Minor Traits"}'::jsonb,
  '{"staff_approval_required": true, "requirements": []}'::jsonb,
  true
),
(
  1462489358908129354,
  'Sixth Sense',
  'sixth_sense',
  'minor',
  1,
  'perception',
  null,
  'You have a subtle instinct for danger and awareness beyond ordinary senses.',
  '{"minor_tier": 1, "point_value": 1, "mechanical_effects": ["+2% Reaction Score.", "+2% Dodge.", "+1 to perception rolls, even if you cannot see."], "incompatible_traits": [], "notes": "", "source": "Railbound Trait Guide - Minor Traits"}'::jsonb,
  '{"staff_approval_required": true, "requirements": []}'::jsonb,
  true
),
(
  1462489358908129354,
  'Hustler',
  'hustler',
  'minor',
  1,
  'economy',
  null,
  'You are good with money and can stretch a dollar or coin further than most.',
  '{"minor_tier": 1, "point_value": 1, "mechanical_effects": ["Permanent 1.2x boost to money earned from missions."], "incompatible_traits": [], "notes": "Events do not count.", "source": "Railbound Trait Guide - Minor Traits"}'::jsonb,
  '{"staff_approval_required": true, "requirements": []}'::jsonb,
  true
),
(
  1462489358908129354,
  'Conscientious',
  'conscientious',
  'minor',
  1,
  'equipment',
  null,
  'You take care of everything you own, and even when things break, you can still get them repaired.',
  '{"minor_tier": 1, "point_value": 1, "mechanical_effects": ["Items that reach 0 durability can still be repaired for you."], "incompatible_traits": [], "notes": "Normally items at 0 durability are broken and cannot be repaired.", "source": "Railbound Trait Guide - Minor Traits"}'::jsonb,
  '{"staff_approval_required": true, "requirements": []}'::jsonb,
  true
),
(
  1462489358908129354,
  'Natural Performer',
  'natural_performer',
  'minor',
  1,
  'performance',
  null,
  'You have a chosen performance specialty such as singing, musician, or dancer.',
  '{"minor_tier": 1, "point_value": 1, "mechanical_effects": ["Choose one performance specialty.", "When performing with the chosen specialty, GM may call for a roll to determine crowd response.", "1-9: Nothing happens.", "10-15: Pulls a couple of people.", "16-20: Pulls a full crowd."], "incompatible_traits": [], "notes": "Crowd result is up to GM discretion.", "source": "Railbound Trait Guide - Minor Traits"}'::jsonb,
  '{"staff_approval_required": true, "requirements": ["Performance specialty should be recorded on approval."]}'::jsonb,
  true
),
(
  1462489358908129354,
  'Pack Mule',
  'pack_mule',
  'minor',
  1,
  'inventory',
  null,
  'You can carry more than most.',
  '{"minor_tier": 1, "point_value": 1, "mechanical_effects": ["+1 Inventory Capacity."], "incompatible_traits": ["Bad Back"], "notes": "", "source": "Railbound Trait Guide - Minor Traits"}'::jsonb,
  '{"staff_approval_required": true, "requirements": []}'::jsonb,
  true
),
(
  1462489358908129354,
  'Perceptive',
  'perceptive',
  'minor',
  1,
  'perception',
  null,
  'You are naturally observant.',
  '{"minor_tier": 1, "point_value": 1, "mechanical_effects": ["+1 to all checks that deal with observing."], "incompatible_traits": [], "notes": "", "source": "Railbound Trait Guide - Minor Traits"}'::jsonb,
  '{"staff_approval_required": true, "requirements": []}'::jsonb,
  true
),
(
  1462489358908129354,
  'Light Foot',
  'light_foot',
  'minor',
  1,
  'stealth',
  null,
  'You move quietly and are comfortable acting from stealth.',
  '{"minor_tier": 1, "point_value": 1, "mechanical_effects": ["+1 on all stealth rolls and rolls while being in stealth."], "incompatible_traits": [], "notes": "Cleaned source wording.", "source": "Railbound Trait Guide - Minor Traits"}'::jsonb,
  '{"staff_approval_required": true, "requirements": []}'::jsonb,
  true
),
(
  1462489358908129354,
  'Dragon''s Insight',
  'dragons_insight',
  'minor',
  1,
  'stat',
  null,
  'A small boost to the Magic Affinity stat.',
  '{"minor_tier": 1, "point_value": 1, "mechanical_effects": ["+5% to Magic Affinity."], "incompatible_traits": ["Inflamed Mana Circuits"], "notes": "Stat boosting trait. Sheet should show final amount in parentheses, e.g. 50 (53).", "source": "Railbound Trait Guide - Minor Traits"}'::jsonb,
  '{"staff_approval_required": true, "requirements": []}'::jsonb,
  true
),
(
  1462489358908129354,
  'Leviathan Depth',
  'leviathan_depth',
  'minor',
  1,
  'stat',
  null,
  'A small boost to the Mana stat.',
  '{"minor_tier": 1, "point_value": 1, "mechanical_effects": ["+5% to Mana."], "incompatible_traits": ["Inflamed Mana Circuits"], "notes": "Stat boosting trait. Source title appears as Leviathan Depth.", "source": "Railbound Trait Guide - Minor Traits"}'::jsonb,
  '{"staff_approval_required": true, "requirements": []}'::jsonb,
  true
),
(
  1462489358908129354,
  'Gorilla Strength',
  'gorilla_strength',
  'minor',
  1,
  'stat',
  null,
  'A small boost to the Strength stat.',
  '{"minor_tier": 1, "point_value": 1, "mechanical_effects": ["+5% to Strength."], "incompatible_traits": ["Weak Body"], "notes": "Stat boosting trait.", "source": "Railbound Trait Guide - Minor Traits"}'::jsonb,
  '{"staff_approval_required": true, "requirements": []}'::jsonb,
  true
),
(
  1462489358908129354,
  'Cat''s Grace',
  'cats_grace',
  'minor',
  1,
  'stat',
  null,
  'A small boost to the Dexterity stat.',
  '{"minor_tier": 1, "point_value": 1, "mechanical_effects": ["+5% to Dexterity."], "incompatible_traits": ["Weak Body"], "notes": "Stat boosting trait.", "source": "Railbound Trait Guide - Minor Traits"}'::jsonb,
  '{"staff_approval_required": true, "requirements": []}'::jsonb,
  true
),
(
  1462489358908129354,
  'Bear''s Fortitude',
  'bears_fortitude',
  'minor',
  1,
  'stat',
  null,
  'A small boost to the Stamina stat.',
  '{"minor_tier": 1, "point_value": 1, "mechanical_effects": ["+5% to Stamina."], "incompatible_traits": ["Weak Body"], "notes": "Stat boosting trait. Source text says Bears Fortitude; imported display name uses Bear''s Fortitude for consistency with existing references.", "source": "Railbound Trait Guide - Minor Traits"}'::jsonb,
  '{"staff_approval_required": true, "requirements": []}'::jsonb,
  true
);

select
  slug,
  name,
  tier,
  cost,
  category,
  effects_json->>'minor_tier' as minor_tier,
  effects_json->>'point_value' as point_value,
  is_active
from public.traits
where guild_id = 1462489358908129354
  and tier = 'minor'
  and slug in (
    'magic_background',
    'beast_handler',
    'salesman',
    'lucky_spark',
    'actor',
    'charming',
    'threatening',
    'sixth_sense',
    'hustler',
    'conscientious',
    'natural_performer',
    'pack_mule',
    'perceptive',
    'light_foot',
    'dragons_insight',
    'leviathan_depth',
    'gorilla_strength',
    'cats_grace',
    'bears_fortitude'
  )
order by name;
