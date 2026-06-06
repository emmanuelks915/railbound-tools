-- LC Unit v1 migration
-- Adds bond_notes to source_beasts and ensures the table is correct.
-- Safe to run even if source_beasts already exists.

create table if not exists source_beasts (
  id               uuid        primary key default gen_random_uuid(),
  character_id     uuid        not null references characters(character_id) on delete cascade,
  guild_id         bigint      not null,
  beast_name       text        not null default '',
  beast_type       text        not null default 'utility' check (beast_type in ('combat', 'mount', 'utility')),
  description      text        not null default '',
  bond_notes       text        not null default '',
  image_url        text        not null default '',
  notes            text        not null default '',
  current_skills   text        not null default '',
  base_strength    int         not null default 5,
  base_dexterity   int         not null default 5,
  base_stamina     int         not null default 5,
  base_magic_affinity int      not null default 5,
  base_mana        int         not null default 5,
  xp               int         not null default 0,
  created_at       timestamptz not null default now(),
  updated_at       timestamptz not null default now(),
  unique (character_id)
);

-- Add bond_notes if upgrading from an older version
alter table source_beasts add column if not exists bond_notes text not null default '';

-- Source Beast Skills catalog
create table if not exists source_beast_skills (
  skill_key        text        primary key,
  guild_id         bigint,
  name             text        not null default '',
  beast_skill_type text        not null default 'utility' check (beast_skill_type in ('combat', 'mount', 'utility')),
  tier             int         not null default 1,
  cost             int         not null default 0,
  action_type      text        not null default '',
  prerequisites    text        not null default '',
  chain            text        not null default '',
  effects          text        not null default '',
  description      text        not null default '',
  source_label     text        not null default 'Source Beast Skill Catalog',
  sort_order       int         not null default 0,
  is_active        boolean     not null default true,
  is_purchasable   boolean     not null default false,
  created_at       timestamptz not null default now(),
  updated_at       timestamptz not null default now()
);

-- Index for skill_purchase_requests beast skill lookups
create index if not exists idx_skill_purchase_requests_source_label
  on skill_purchase_requests (guild_id, character_id, source_label);
