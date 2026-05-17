-- Negative Traits Import v1
-- Source: Railbound Trait Guide, Negative Traits section.
-- Imports/updates 24 negative traits.
-- Safe to run more than once.

create extension if not exists pgcrypto;

create table if not exists public.traits (
  trait_id uuid primary key default gen_random_uuid(),
  trait_key text unique,
  name text,
  trait_type text,
  trait_group text,
  category text,
  tier integer,
  point_value integer,
  refund_points integer,
  cost integer,
  description text,
  effects_json jsonb default '{}'::jsonb,
  requires_staff_approval boolean default true,
  is_active boolean default true,
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);

alter table public.traits add column if not exists trait_key text;
alter table public.traits add column if not exists name text;
alter table public.traits add column if not exists trait_type text;
alter table public.traits add column if not exists trait_group text;
alter table public.traits add column if not exists category text;
alter table public.traits add column if not exists tier integer;
alter table public.traits add column if not exists point_value integer;
alter table public.traits add column if not exists refund_points integer;
alter table public.traits add column if not exists cost integer;
alter table public.traits add column if not exists description text;
alter table public.traits add column if not exists effects_json jsonb default '{}'::jsonb;
alter table public.traits add column if not exists requires_staff_approval boolean default true;
alter table public.traits add column if not exists is_active boolean default true;
alter table public.traits add column if not exists updated_at timestamptz default now();

-- Negative Traits Import v3 no-conflict cleanup
delete from public.traits
where trait_key in (
  'negative_knucklehead',
  'negative_unlucky',
  'negative_illiterate',
  'negative_non_swimmer',
  'negative_monotoned',
  'negative_bad_back',
  'negative_hearing_impaired',
  'negative_big_spender',
  'negative_clumsy',
  'negative_in_debt',
  'negative_deaf',
  'negative_weak_body',
  'negative_inflamed_mana_circuits',
  'negative_hot_natured',
  'negative_cold_natured',
  'negative_visually_impaired',
  'negative_easily_hurt',
  'negative_got_a_prosthetic',
  'negative_pyrophobia',
  'negative_claustrophobia',
  'negative_acrophobia',
  'negative_source_sensitivity',
  'negative_mana_less',
  'negative_panic_attacks'
);

insert into public.traits (
  trait_key,
  name,
  trait_type,
  trait_group,
  category,
  tier,
  point_value,
  refund_points,
  cost,
  description,
  effects_json,
  requires_staff_approval,
  is_active
)
values
(
        'negative_knucklehead',
        'Knucklehead',
        'negative',
        'negative',
        'negative',
        1,
        -1,
        1,
        -1,
        'Skills cost 5% more XP.',
        '{"mechanical_effects": ["Skills cost 5% more XP."], "restrictions": [], "incompatible_traits": [], "notes": "Cleaned from source wording: ''Cost more 5% more exp for skills.''", "source": "Railbound Trait Guide - Negative Traits", "requires_staff_approval": true, "trait_type": "negative", "tier": 1, "refund_points": 1}'::jsonb,
        true,
        true
    ),
(
        'negative_unlucky',
        'Unlucky',
        'negative',
        'negative',
        'negative',
        1,
        -1,
        1,
        -1,
        'You suffer the opposite effect of the Luck trait.',
        '{"mechanical_effects": ["-1 to all rolls."], "restrictions": [], "incompatible_traits": ["Lucky", "Luck"], "notes": "Source says opposite effect of the Luck trait.", "source": "Railbound Trait Guide - Negative Traits", "requires_staff_approval": true, "trait_type": "negative", "tier": 1, "refund_points": 1}'::jsonb,
        true,
        true
    ),
(
        'negative_illiterate',
        'Illiterate',
        'negative',
        'negative',
        'negative',
        1,
        -1,
        1,
        -1,
        'You never learned how to read and are now at an age or maturity where learning is no longer practical.',
        '{"mechanical_effects": ["Automatically fail any check dealing with reading."], "restrictions": ["Cannot read without extraordinary staff-approved circumstances."], "incompatible_traits": [], "notes": "", "source": "Railbound Trait Guide - Negative Traits", "requires_staff_approval": true, "trait_type": "negative", "tier": 1, "refund_points": 1}'::jsonb,
        true,
        true
    ),
(
        'negative_non_swimmer',
        'Non-swimmer',
        'negative',
        'negative',
        'negative',
        1,
        -1,
        1,
        -1,
        'You cannot swim, tread water, or float, and cannot learn how to do so.',
        '{"mechanical_effects": ["Cannot swim, tread water, or float."], "restrictions": ["Cannot learn swimming normally."], "incompatible_traits": [], "notes": "", "source": "Railbound Trait Guide - Negative Traits", "requires_staff_approval": true, "trait_type": "negative", "tier": 1, "refund_points": 1}'::jsonb,
        true,
        true
    ),
(
        'negative_monotoned',
        'Monotoned',
        'negative',
        'negative',
        'negative',
        1,
        -1,
        1,
        -1,
        'You always sound disinterested, bored, or generally off-putting.',
        '{"mechanical_effects": ["-1 to all social rolls."], "restrictions": [], "incompatible_traits": [], "notes": "Cleaned typo from source: ''disinterred'' -> ''disinterested''.", "source": "Railbound Trait Guide - Negative Traits", "requires_staff_approval": true, "trait_type": "negative", "tier": 1, "refund_points": 1}'::jsonb,
        true,
        true
    ),
(
        'negative_bad_back',
        'Bad Back',
        'negative',
        'negative',
        'negative',
        1,
        -1,
        1,
        -1,
        'You have never been good at carrying too many items.',
        '{"mechanical_effects": ["-1 to inventory capacity."], "restrictions": [], "incompatible_traits": [], "notes": "", "source": "Railbound Trait Guide - Negative Traits", "requires_staff_approval": true, "trait_type": "negative", "tier": 1, "refund_points": 1}'::jsonb,
        true,
        true
    ),
(
        'negative_hearing_impaired',
        'Hearing Impaired',
        'negative',
        'negative',
        'negative',
        1,
        -1,
        1,
        -1,
        'You can hear, but not as well as others.',
        '{"mechanical_effects": ["-1 to all social rolls in big crowds or around loud noises."], "restrictions": [], "incompatible_traits": [], "notes": "", "source": "Railbound Trait Guide - Negative Traits", "requires_staff_approval": true, "trait_type": "negative", "tier": 1, "refund_points": 1}'::jsonb,
        true,
        true
    ),
(
        'negative_big_spender',
        'Big Spender',
        'negative',
        'negative',
        'negative',
        2,
        -2,
        2,
        -2,
        'When buying anything, it costs more money.',
        '{"mechanical_effects": ["Purchases cost 10% more."], "restrictions": [], "incompatible_traits": ["Logistics Mind"], "notes": "Cannot have this and Logistics Mind.", "source": "Railbound Trait Guide - Negative Traits", "requires_staff_approval": true, "trait_type": "negative", "tier": 2, "refund_points": 2}'::jsonb,
        true,
        true
    ),
(
        'negative_clumsy',
        'Clumsy',
        'negative',
        'negative',
        'negative',
        2,
        -2,
        2,
        -2,
        'Your items break twice as easily.',
        '{"mechanical_effects": ["Durability loss is doubled. If an item would take 1 durability damage, it takes 2 instead."], "restrictions": [], "incompatible_traits": [], "notes": "", "source": "Railbound Trait Guide - Negative Traits", "requires_staff_approval": true, "trait_type": "negative", "tier": 2, "refund_points": 2}'::jsonb,
        true,
        true
    ),
(
        'negative_in_debt',
        'In Debt',
        'negative',
        'negative',
        'negative',
        2,
        -2,
        2,
        -2,
        'At the end of every month, you owe some mysterious figure.',
        '{"mechanical_effects": ["Owe 100 crowns at the end of every month."], "restrictions": [], "incompatible_traits": [], "notes": "Source notes this may change if missions are not coming out.", "source": "Railbound Trait Guide - Negative Traits", "requires_staff_approval": true, "trait_type": "negative", "tier": 2, "refund_points": 2}'::jsonb,
        true,
        true
    ),
(
        'negative_deaf',
        'Deaf',
        'negative',
        'negative',
        'negative',
        2,
        -2,
        2,
        -2,
        'You cannot hear.',
        '{"mechanical_effects": ["Any check related to sense of hearing is a failure.", "Auditory illusions and charms do not work on this user."], "restrictions": [], "incompatible_traits": [], "notes": "", "source": "Railbound Trait Guide - Negative Traits", "requires_staff_approval": true, "trait_type": "negative", "tier": 2, "refund_points": 2}'::jsonb,
        true,
        true
    ),
(
        'negative_weak_body',
        'Weak Body',
        'negative',
        'negative',
        'negative',
        2,
        -2,
        2,
        -2,
        'Choose one physical stat that is permanently lowered by 5%.',
        '{"mechanical_effects": ["One physical stat is permanently lowered by 5%."], "restrictions": ["Chosen physical stat should be recorded on approval."], "incompatible_traits": ["Gorilla Strength", "Cat''s Grace", "Bear''s Fortitude"], "notes": "", "source": "Railbound Trait Guide - Negative Traits", "requires_staff_approval": true, "trait_type": "negative", "tier": 2, "refund_points": 2}'::jsonb,
        true,
        true
    ),
(
        'negative_inflamed_mana_circuits',
        'Inflamed Mana Circuits',
        'negative',
        'negative',
        'negative',
        2,
        -2,
        2,
        -2,
        'Choose either Mana or Magic Affinity. That stat is permanently lowered by 5%.',
        '{"mechanical_effects": ["Mana or Magic Affinity is permanently lowered by 5%."], "restrictions": ["Chosen magical stat should be recorded on approval."], "incompatible_traits": ["Dragon''s Insight", "Leviathan''s Depth"], "notes": "", "source": "Railbound Trait Guide - Negative Traits", "requires_staff_approval": true, "trait_type": "negative", "tier": 2, "refund_points": 2}'::jsonb,
        true,
        true
    ),
(
        'negative_hot_natured',
        'Hot-Natured',
        'negative',
        'negative',
        'negative',
        2,
        -2,
        2,
        -2,
        'You struggle in notable cold environments.',
        '{"mechanical_effects": ["-1 Luck on skill rolls while in a notable cold environment."], "restrictions": [], "incompatible_traits": [], "notes": "", "source": "Railbound Trait Guide - Negative Traits", "requires_staff_approval": true, "trait_type": "negative", "tier": 2, "refund_points": 2}'::jsonb,
        true,
        true
    ),
(
        'negative_cold_natured',
        'Cold-Natured',
        'negative',
        'negative',
        'negative',
        2,
        -2,
        2,
        -2,
        'You struggle in notable hot environments.',
        '{"mechanical_effects": ["-1 Luck on skill rolls while in a notable hot environment."], "restrictions": [], "incompatible_traits": [], "notes": "", "source": "Railbound Trait Guide - Negative Traits", "requires_staff_approval": true, "trait_type": "negative", "tier": 2, "refund_points": 2}'::jsonb,
        true,
        true
    ),
(
        'negative_visually_impaired',
        'Visually Impaired',
        'negative',
        'negative',
        'negative',
        2,
        -2,
        2,
        -2,
        'You have a significant seeing problem.',
        '{"mechanical_effects": ["All ranged attacks are capped at 7 meters maximum range.", "-1 to all perception rolls."], "restrictions": [], "incompatible_traits": [], "notes": "", "source": "Railbound Trait Guide - Negative Traits", "requires_staff_approval": true, "trait_type": "negative", "tier": 2, "refund_points": 2}'::jsonb,
        true,
        true
    ),
(
        'negative_easily_hurt',
        'Easily Hurt',
        'negative',
        'negative',
        'negative',
        3,
        -3,
        3,
        -3,
        'You gain twice the amount of injuries.',
        '{"mechanical_effects": ["Injuries are doubled. If you would receive one Tier 1 injury, you receive two Tier 1 injuries instead."], "restrictions": [], "incompatible_traits": [], "notes": "", "source": "Railbound Trait Guide - Negative Traits", "requires_staff_approval": true, "trait_type": "negative", "tier": 3, "refund_points": 3}'::jsonb,
        true,
        true
    ),
(
        'negative_got_a_prosthetic',
        'Got a Prosthetic',
        'negative',
        'negative',
        'negative',
        3,
        -3,
        3,
        -3,
        'You were born with a missing limb or received one at a young age and now have an automail limb.',
        '{"mechanical_effects": ["The prosthetic has durability that must be tracked.", "If the prosthetic breaks, you suffer a Tier 4 based debuff until it is repaired or replaced.", "During a mission or event, it can be removed or destroyed."], "restrictions": ["Prosthetic durability must be tracked."], "incompatible_traits": [], "notes": "", "source": "Railbound Trait Guide - Negative Traits", "requires_staff_approval": true, "trait_type": "negative", "tier": 3, "refund_points": 3}'::jsonb,
        true,
        true
    ),
(
        'negative_pyrophobia',
        'Pyrophobia',
        'negative',
        'negative',
        'negative',
        3,
        -3,
        3,
        -3,
        'Severe fear of fire.',
        '{"mechanical_effects": ["-2 Luck on skill rolls when too close to fire.", "-20% Reaction Score when dealing with fire."], "restrictions": ["Cannot work smelters or forges.", "Cannot work on combustion engines."], "incompatible_traits": [], "notes": "Severe effect.", "source": "Railbound Trait Guide - Negative Traits", "requires_staff_approval": true, "trait_type": "negative", "tier": 3, "refund_points": 3}'::jsonb,
        true,
        true
    ),
(
        'negative_claustrophobia',
        'Claustrophobia',
        'negative',
        'negative',
        'negative',
        3,
        -3,
        3,
        -3,
        'Severe fear of spaces with no exit or underground spaces.',
        '{"mechanical_effects": ["-2 Luck on skill rolls when in spaces with no exit or while underground."], "restrictions": ["Cannot enter enclosed spaces alone, including caves or hazard entries."], "incompatible_traits": [], "notes": "Severe effect.", "source": "Railbound Trait Guide - Negative Traits", "requires_staff_approval": true, "trait_type": "negative", "tier": 3, "refund_points": 3}'::jsonb,
        true,
        true
    ),
(
        'negative_acrophobia',
        'Acrophobia',
        'negative',
        'negative',
        'negative',
        3,
        -3,
        3,
        -3,
        'Severe fear of heights and drops.',
        '{"mechanical_effects": ["-2 Luck on skill rolls when near drops that are 10+ feet or greater."], "restrictions": ["Cannot enter or pilot floating, suspended, or raising platforms or vehicles alone."], "incompatible_traits": [], "notes": "Source text appears to omit the minus sign before 2 Luck. This import treats it as -2 Luck to match the other severe phobia traits.", "source": "Railbound Trait Guide - Negative Traits", "requires_staff_approval": true, "trait_type": "negative", "tier": 3, "refund_points": 3}'::jsonb,
        true,
        true
    ),
(
        'negative_source_sensitivity',
        'Source Sensitivity',
        'negative',
        'negative',
        'negative',
        3,
        -3,
        3,
        -3,
        'You are acutely attuned to Source, too attuned, and exposure to it is incredibly painful.',
        '{"mechanical_effects": ["Mana Skin is not sufficient for immunity near Source Wells.", "Reflexive Mana Skin can only provide shielding in weak Source Wells.", "You take 15% more output from magical abilities.", "As a mage, your Magical Safe Output is permanently less than 10%."], "restrictions": [], "incompatible_traits": [], "notes": "", "source": "Railbound Trait Guide - Negative Traits", "requires_staff_approval": true, "trait_type": "negative", "tier": 3, "refund_points": 3}'::jsonb,
        true,
        true
    ),
(
        'negative_mana_less',
        'Mana-Less',
        'negative',
        'negative',
        'negative',
        3,
        -3,
        3,
        -3,
        'For whatever reason, you were born with zero access to mana circuits. Some see it as a curse from the gods or simply terrible luck.',
        '{"mechanical_effects": ["Zero access to magic-based skills.", "Cannot use magic items unless someone else is fueling them.", "Locked from any skill or item that uses mana unless you have a way to circumvent it."], "restrictions": ["Cannot use mana-based skills normally.", "Cannot use mana-powered items normally."], "incompatible_traits": [], "notes": "Cleaned source typo: ''man''s circuits'' -> ''mana circuits''.", "source": "Railbound Trait Guide - Negative Traits", "requires_staff_approval": true, "trait_type": "negative", "tier": 3, "refund_points": 3}'::jsonb,
        true,
        true
    ),
(
        'negative_panic_attacks',
        'Panic Attacks',
        'negative',
        'negative',
        'negative',
        3,
        -3,
        3,
        -3,
        'Emotionally tense and dangerous scenarios may trigger panic attacks, anxiety, or a harried state where concentration becomes impossible.',
        '{"mechanical_effects": ["When triggered, roll 1d20. Special items or GMs may provide modifiers.", "On 1-9, the attack is triggered.", "On 10-20, you pass and successfully control your emotions.", "While active: -25% Reaction Score.", "While active: inability to target the trigger or proceed while the trigger remains present. This may be GM-guided.", "Ends when the trigger is removed or within 5 turns, whichever occurs first."], "restrictions": ["Emotional triggers must be defined in the OC sheet and must be reasonable.", "Combat trigger rolls occur each time your group is outnumbered."], "incompatible_traits": [], "notes": "", "source": "Railbound Trait Guide - Negative Traits", "requires_staff_approval": true, "trait_type": "negative", "tier": 3, "refund_points": 3}'::jsonb,
        true,
        true
    );
-- Verify
select trait_key, name, tier, point_value, refund_points, trait_type, is_active
from public.traits
where trait_type = 'negative'
order by tier, name;
