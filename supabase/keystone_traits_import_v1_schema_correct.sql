-- Keystone Traits Import v1 SCHEMA CORRECT
-- Source: Railbound Trait Guide, Keystone Traits section.
-- Matches current public.traits schema:
-- guild_id bigint, name, slug, tier text, cost integer, category, exclusive_group,
-- description, effects_json, requirements_json, is_active.
--
-- traits.tier check allows: origin, minor, reliable, keystone, negative.
-- Therefore all three-point keystone/class-path traits use tier = 'keystone' and cost = 3.

delete from public.traits
where guild_id = 1462489358908129354
and slug in (
  'quiet_benefactor',
  'selective_fortune',
  'self_made_survivor',
  'greater_knowledge',
  'mana_circuits_mage',
  'forgeborn',
  'loyal_companion',
  'gunslinger'
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
  'Quiet Benefactor',
  'quiet_benefactor',
  'keystone',
  3,
  'reward_path',
  'keystone_reward_path',
  'Boosts rewards and effectiveness for others, not yourself.',
  '{"keystone_tier": 3, "point_value": 3, "mechanical_effects": ["Boost is 1.2x for others.", "Works only for missions.", "Grants two extra trait points, raising maximum trait points to 7."], "incompatible_traits": ["Mana Circuits (Mage)", "Forgeborn", "Gunslinger", "Loyal Companion", "Selective Fortune", "Self-Made Survivor"], "notes": "Reward-focused Keystone trait. Boost applies to others, not self.", "source": "Railbound Trait Guide - Keystone Traits", "reward_scaling_trait": true, "reward_target": "others", "mission_only": true, "reward_multiplier": 1.2, "max_trait_points": 7, "extra_trait_points": 2, "class_path_restricted": true}'::jsonb,
  '{"staff_approval_required": true, "requirements": ["Cannot have Mana Circuits (Mage), Forgeborn, Gunslinger, or Loyal Companion.", "Does not work with Selective Fortune or Self-Made Survivor."]}'::jsonb,
  true
),
(
  1462489358908129354,
  'Selective Fortune',
  'selective_fortune',
  'keystone',
  3,
  'reward_path',
  'keystone_reward_path',
  'Allows the user to decide whether to give a small boost to one person or to themself.',
  '{"keystone_tier": 3, "point_value": 3, "mechanical_effects": ["Chosen person boost is 1.15x.", "Self boost is 1.15x.", "Works only for missions.", "Grants one extra trait point, raising maximum trait points to 6."], "incompatible_traits": ["Mana Circuits (Mage)", "Forgeborn", "Gunslinger", "Loyal Companion", "Quiet Benefactor", "Self-Made Survivor"], "notes": "Reward-focused Keystone trait. Can target self or one chosen person.", "source": "Railbound Trait Guide - Keystone Traits", "reward_scaling_trait": true, "reward_target": "self_or_other", "mission_only": true, "reward_multiplier": 1.15, "max_trait_points": 6, "extra_trait_points": 1, "class_path_restricted": true}'::jsonb,
  '{"staff_approval_required": true, "requirements": ["Cannot have Mana Circuits (Mage), Forgeborn, Gunslinger, or Loyal Companion.", "Does not work with Quiet Benefactor or Self-Made Survivor."]}'::jsonb,
  true
),
(
  1462489358908129354,
  'Self-Made Survivor',
  'self_made_survivor',
  'keystone',
  3,
  'reward_path',
  'keystone_reward_path',
  'Boosted EXP gain for the user.',
  '{"keystone_tier": 3, "point_value": 3, "mechanical_effects": ["Boost is 1.3x for yourself.", "Works only for missions.", "User cannot go over 5 total trait points."], "incompatible_traits": ["Mana Circuits (Mage)", "Forgeborn", "Gunslinger", "Loyal Companion", "Selective Fortune", "Quiet Benefactor"], "notes": "Reward-focused Keystone trait. Self-only XP/reward gain.", "source": "Railbound Trait Guide - Keystone Traits", "reward_scaling_trait": true, "reward_target": "self", "mission_only": true, "reward_multiplier": 1.3, "max_trait_points": 5, "extra_trait_points": 0, "class_path_restricted": true}'::jsonb,
  '{"staff_approval_required": true, "requirements": ["Maximum trait points remain 5.", "Cannot have Mana Circuits (Mage), Forgeborn, Gunslinger, or Loyal Companion.", "Does not work with Selective Fortune or Quiet Benefactor."]}'::jsonb,
  true
),
(
  1462489358908129354,
  'Greater Knowledge',
  'greater_knowledge',
  'keystone',
  3,
  'knowledge',
  null,
  'For some reason, you have always been more attuned to the world and know things you were not supposed to know.',
  '{"keystone_tier": 3, "point_value": 3, "mechanical_effects": ["You may ask a GM for information your character would not normally know during a mission or event.", "Accuracy and usefulness depends on your roll.", "Can be used once per week during either a mission or an event.", "If you participate in both a mission and an event within the same week, you may use it once in each.", "1d20 roll: 1 = Nothing.", "1d20 roll: 2-6 = Minor info.", "1d20 roll: 7-11 = Moderate info.", "1d20 roll: 12-16 = Great info.", "1d20 roll: 17-19 = Amazing info.", "1d20 roll: 20 = Perfect info."], "incompatible_traits": [], "notes": "Exception to the class path restriction per source. Requires Source Sensitivity.", "source": "Railbound Trait Guide - Keystone Traits", "information_request_trait": true, "weekly_uses_mission": 1, "weekly_uses_event": 1, "requires_negative_trait": "Source Sensitivity", "class_path_restriction_exception": true}'::jsonb,
  '{"staff_approval_required": true, "requirements": ["Must be approved by staff.", "Required to take the negative trait Source Sensitivity."]}'::jsonb,
  true
),
(
  1462489358908129354,
  'Mana Circuits (Mage)',
  'mana_circuits_mage',
  'keystone',
  3,
  'class_path',
  'primary_class_path',
  'You cultivated internal pathways known as Mana Circuits, refined channels within your body that allow mana to flow with precision and intent.',
  '{"keystone_tier": 3, "point_value": 3, "mechanical_effects": ["Ability to consciously cast spells.", "Controlled mana manipulation.", "Access to spell-based progression systems.", "Gain one free Tier 0 Force to choose.", "The Force bought at character creation is a quarter of the price.", "Receive Magic Tool Use for free."], "incompatible_traits": ["Quiet Benefactor", "Selective Fortune", "Self-Made Survivor", "Forgeborn", "Gunslinger", "Loyal Companion"], "notes": "Primary class-defining path. May grant free skills and discounted force options.", "source": "Railbound Trait Guide - Keystone Traits", "class_path_trait": true, "primary_class_path": true, "grants_free_skill": true, "may_require_staff_skill_override": true, "free_skill_options": ["Magic Tool Use", "One free Tier 0 Force"], "discounts": [{"item": "Character creation Force", "multiplier": 0.25}]}'::jsonb,
  '{"staff_approval_required": true, "requirements": []}'::jsonb,
  true
),
(
  1462489358908129354,
  'Forgeborn',
  'forgeborn',
  'keystone',
  3,
  'class_path',
  'primary_class_path',
  'You were raised around machinery or developed an intense passion for industrial craft. Steam engines, pressure valves, reinforced plating, and mechanical systems are second nature to you.',
  '{"keystone_tier": 3, "point_value": 3, "mechanical_effects": ["Advanced knowledge of steam and mechanical systems.", "Repair-focused skills.", "Ability to tinker, modify, and enhance equipment.", "Increased effectiveness when working with tools or industrial devices."], "incompatible_traits": ["Quiet Benefactor", "Selective Fortune", "Self-Made Survivor", "Mana Circuits (Mage)", "Gunslinger", "Loyal Companion"], "notes": "Primary class-defining path.", "source": "Railbound Trait Guide - Keystone Traits", "class_path_trait": true, "primary_class_path": true}'::jsonb,
  '{"staff_approval_required": true, "requirements": []}'::jsonb,
  true
),
(
  1462489358908129354,
  'Loyal Companion',
  'loyal_companion',
  'keystone',
  3,
  'class_path',
  'primary_class_path',
  'Through training, upbringing, or deep personal bonding, you begin your journey with a loyal animal companion.',
  '{"keystone_tier": 3, "point_value": 3, "mechanical_effects": ["Companion may assist in roleplay interactions.", "Companion may assist in combat situations.", "Companion may assist in travel and mobility.", "Choose one companion build: Combat Focused, Mount Focused, or Support Focused.", "Combat Focused: specialized in offense, protection, and battlefield presence.", "Mount Focused: built for speed, endurance, and travel efficiency.", "Support Focused: assists with tracking, scouting, communication, or utility."], "incompatible_traits": ["Quiet Benefactor", "Selective Fortune", "Self-Made Survivor", "Mana Circuits (Mage)", "Forgeborn", "Gunslinger"], "notes": "Primary class-defining path.", "source": "Railbound Trait Guide - Keystone Traits", "class_path_trait": true, "primary_class_path": true, "requires_choice": true, "choice_field": "companion_build", "choice_options": ["Combat Focused", "Mount Focused", "Support Focused"]}'::jsonb,
  '{"staff_approval_required": true, "requirements": ["Companion build must be selected and recorded on approval."]}'::jsonb,
  true
),
(
  1462489358908129354,
  'Gunslinger',
  'gunslinger',
  'keystone',
  3,
  'class_path',
  'primary_class_path',
  'You are formally trained in the use, maintenance, and tactical application of firearms.',
  '{"keystone_tier": 3, "point_value": 3, "mechanical_effects": ["Proficiency with firearms.", "Knowledge of weapon maintenance and repair.", "Access to gun-based combat techniques.", "Starting firearm appropriate to your character''s stats and background."], "incompatible_traits": ["Quiet Benefactor", "Selective Fortune", "Self-Made Survivor", "Mana Circuits (Mage)", "Forgeborn", "Loyal Companion"], "notes": "Primary class-defining path. Source heading says Gunslinger; earlier docs may call this Gunslinger Training.", "source": "Railbound Trait Guide - Keystone Traits", "class_path_trait": true, "primary_class_path": true, "starting_equipment": ["firearm"]}'::jsonb,
  '{"staff_approval_required": true, "requirements": []}'::jsonb,
  true
);

select
  slug,
  name,
  tier,
  cost,
  category,
  exclusive_group,
  effects_json->>'keystone_tier' as keystone_tier,
  effects_json->>'point_value' as point_value,
  is_active
from public.traits
where guild_id = 1462489358908129354
  and tier = 'keystone'
  and slug in (
    'quiet_benefactor',
    'selective_fortune',
    'self_made_survivor',
    'greater_knowledge',
    'mana_circuits_mage',
    'forgeborn',
    'loyal_companion',
    'gunslinger'
  )
order by category, name;
