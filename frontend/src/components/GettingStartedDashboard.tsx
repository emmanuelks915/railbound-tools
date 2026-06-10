// GettingStartedDashboard.tsx
// Place at: frontend/src/components/GettingStartedDashboard.tsx

import React, { useState } from "react";
import {
  BookOpen, Sparkles, Globe, Scroll, Home, Map,
  ChevronRight, ChevronLeft, Check, AlertTriangle,
  Star, Shield, Swords, Zap, Wrench, Target, PawPrint, Users
} from "lucide-react";

type HubTab = "start" | "create" | "classes" | "skills" | "world" | "guide";

interface BuildState {
  city: string; classChoice: string; selectedTraits: string[];
  stats: Record<string,number>; selectedSkills: string[]; step: number;
}

const XP_BANDS = [
  {min:0,max:50,cost:1},{min:51,max:150,cost:2},{min:151,max:250,cost:4},
  {min:251,max:350,cost:6},{min:351,max:450,cost:8},{min:451,max:550,cost:10},
  {min:551,max:650,cost:12},{min:651,max:750,cost:14},
];
const STAT_KEYS = ["strength","dexterity","stamina","magic_affinity","mana"];
const STAT_LABELS: Record<string,string> = {
  strength:"Strength",dexterity:"Dexterity",stamina:"Stamina",
  magic_affinity:"Mag. Affinity",mana:"Mana"
};
function calcStatXP(from:number,to:number):number {
  let t=0; for(let i=from+1;i<=to;i++){const b=XP_BANDS.find(b=>i>=b.min&&i<=b.max);t+=b?b.cost:14;} return t;
}
function totalStatXP(s:Record<string,number>):number{return STAT_KEYS.reduce((a,k)=>a+calcStatXP(10,s[k]??10),0);}
function totalSkillXP(skills:string[],list:typeof STARTING_SKILLS):number{
  return skills.reduce((a,k)=>{const s=list.find(x=>x.key===k);return a+(s?.cost||0);},0);
}

const CLASS_GUIDES = [
  { id:"mercenary", name:"Mercenary", emoji:"🥾", tag:"Universal — No Trait Required", tagColor:"#2f6f73",
    difficulty:"Easy", role:"Utility / Stealth / Action Economy",
    desc:"The universal foundation — every character can access these regardless of class trait. Stealth, field navigation, action economy, and practical utility.",
    bestFor:"Every build. These skills support any playstyle.",
    traitNote:"No class trait required. Available to all characters.",
    statPriority:[
      {stat:"Dexterity",note:"PRIMARY for stealth builds — stealth formula is DEX × 0.4"},
      {stat:"Stamina",note:"Never neglect — affects wound thresholds and endurance"},
      {stat:"Strength",note:"Only if going combat-focused alongside this tree"},
    ],
    sampleBuild:{
      name:"The Shadow Runner",
      traits:["Light Foot (1pt)","Cat's Grace (1pt)","Sixth Sense (1pt)","Perceptive (1pt)","Threatening (1pt)"],
      stats:{strength:10,dexterity:60,stamina:30,magic_affinity:10,mana:10},statXP:70,
      skills:[
        {name:"Pilfer",cost:50,why:"Gate to Stealth chain — always first"},
        {name:"Stealth",cost:265,why:"Core skill — hide, sneak, ambush outside combat"},
        {name:"Magic Tool Use",cost:50,why:"Permanent QoL unlock for 50 XP"},
        {name:"Riding & Driving",cost:50,why:"Cheap mission mobility"},
      ],skillXP:415,remaining:115,
      notes:["Save 115 XP for DEX investment or toward Adept (requires 4 combat/class skills).","Free skill from Wayfarer origin: Local Study, Print Forgery, or Cartography."],
    },
    chains:[
      {label:"STEALTH",path:["Pilfer (T0)","Stealth (T1)","Misdirection (T2)"]},
      {label:"ECONOMY",path:["Adept (T2)","Operative (T3)","Veteran (T3)"]},
      {label:"UTILITY",path:["Pacing (T2 standalone)","Quartermastery (T2 standalone)"]},
    ],
    tips:[
      "Don't build everything at once. Pick stealth or combat early, then fill in QoL skills as you level.",
      "The Adept → Veteran chain needs both combat AND knowledge skills. Collect knowledge skills early.",
      "Magic Tool Use is 50 XP. Just buy it. Enchanted items appear in every session.",
      "Stealth requires significant DEX investment to be effective. Don't take it if you're dumping DEX.",
    ],
  },
  { id:"knowledge", name:"Knowledge", emoji:"📚", tag:"Universal — No Trait Required", tagColor:"#2f6f73",
    difficulty:"Easy", role:"Investigation / Expertise / Support Modifiers",
    desc:"Knowledge skills represent deep expertise. They stack with each other and with other class skills to multiply your effectiveness in any investigative scenario.",
    bestFor:"Any build that wants depth, lore access, and stacking modifiers.",
    traitNote:"No class trait required. Available to all characters.",
    statPriority:[
      {stat:"Stamina",note:"Need to survive to use your expertise"},
      {stat:"Dexterity",note:"Light investment for mobility"},
      {stat:"Strength",note:"Minimal — you're a support specialist"},
    ],
    sampleBuild:{
      name:"The Field Expert",
      traits:["Knowledgeable (2pt)","Perceptive (1pt)","Amateur Historian (2pt)"],
      stats:{strength:30,dexterity:40,stamina:60,magic_affinity:10,mana:10},statXP:100,
      skills:[
        {name:"Linguistics",cost:100,why:"Gate to Print Forgery and Codebreaking"},
        {name:"Doranswyr Historian",cost:100,why:"LORE ACCESS + gate to Martial Historian"},
        {name:"Biology",cost:100,why:"Diagnosis rolls + gate to Veterinary Study"},
        {name:"Chemistry",cost:100,why:"Stacks with Forgecraft and Field Medic"},
        {name:"Cartography",cost:150,why:"Cheapest trade skill; maps missions"},
      ],skillXP:550,remaining:0,
      notes:["Knowledgeable (+3) + Doranswyr Historian (+2) + Amateur Historian (+3) = +8 to historical checks at creation.","Free origin skill: take Linguistics or Doranswyr Historian and save 100 XP."],
    },
    chains:[
      {label:"LANGUAGE",path:["Linguistics (T0)","Print Forgery (T1)","Codebreaking (T1)"]},
      {label:"HISTORY",path:["Doranswyr Historian (T0)","Martial Historian (T1)"]},
      {label:"SCIENCE",path:["Biology (T0)","Veterinary Study (T1)"]},
      {label:"SCIENCE",path:["Geology (T0)","Metallurgy (T1)"]},
      {label:"RELIGION",path:["Catechumen (T0)","Luminary (T1)"]},
      {label:"TECH",path:["Chemistry/Physics (T0)","Steam Engines/Electricity/Automata (T1)"]},
    ],
    tips:[
      "Knowledge modifiers STACK. Biology + Veterinary Study + Field Medic all apply to an animal diagnosis roll simultaneously.",
      "Several knowledge skills are prerequisites for trade skills. Buy the academic skill first.",
      "The Knowledgeable (2pt) trait gives +3 to ALL knowledge skills. With 5+ knowledge skills, it pays for itself immediately.",
      "Local Study: City-States is free with an Origin Trait and can be taken multiple times with sufficient RP.",
    ],
  },
  { id:"allrounder", name:"All-Rounder", emoji:"⭐", tag:"No Class Trait — Open Progression", tagColor:"#888",
    difficulty:"Easy–Medium", role:"Generalist / XP Grinder / Keystone Synergy",
    desc:"Any character who skips a class trait. Those 3 freed-up points open Keystone traits unavailable to class builds — and you can dip into every tree at T0/T1.",
    bestFor:"Players who want breadth, Keystone traits, or the Self-Made Survivor XP snowball.",
    traitNote:"No class trait. Keystone traits (Self-Made Survivor, Selective Fortune, Quiet Benefactor) are ONLY available to All-Rounders.",
    statPriority:[
      {stat:"Strength or Dexterity",note:"Depends on weapon track — pick one to invest in"},
      {stat:"Stamina",note:"Always invest here — you still take hits"},
    ],
    sampleBuild:{
      name:"The Versatile Operative",
      traits:["Self-Made Survivor (3pt)","Sixth Sense (1pt)","Gorilla Strength (1pt)"],
      stats:{strength:60,dexterity:40,stamina:50,magic_affinity:10,mana:10},statXP:120,
      skills:[
        {name:"Heavy Armaments",cost:50,why:"Combat entry; +2% output; gate to Heavy track"},
        {name:"Taunt",cost:265,why:"Cheapest aggro tool at T1"},
        {name:"Magic Tool Use",cost:50,why:"50 XP QoL unlock"},
        {name:"Pilfer",cost:50,why:"Social utility + stealth gate"},
      ],skillXP:415,remaining:65,
      notes:["Self-Made Survivor gives 1.3× XP on missions. After 5 missions you'll be significantly ahead of class builds.","Self-Made Survivor CAPS your trait points at 5 — you cannot take negative traits.","Free skill from Bound origin: Doranswyr Historian."],
    },
    chains:[
      {label:"ACCESS",path:["T0 from any tree","T1 from any tree","T2+ blocked without class trait"]},
      {label:"KEYSTONE",path:["Self-Made Survivor (1.3× mission XP)","Selective Fortune (1.15× XP)","Quiet Benefactor (1.2× rewards for others)"]},
    ],
    tips:[
      "Self-Made Survivor is the best trait in the game for solo grinders. The 1.3× XP compounds over dozens of missions.",
      "You can dip into Magecraft T0/T1 (Standard band max), Forgecraft T0/T1, and Guncraft T0/T1 without a class trait.",
      "The Adept → Operative → Veteran chain needs combat AND knowledge skills. Collect both early.",
      "Keystone traits CANNOT combine with class traits. This is the ALL-ROUNDER exclusive advantage.",
    ],
  },
  { id:"fieldmedic", name:"Field Medic", emoji:"⛑️", tag:"Field Medic Trait — 2pt Subclass", tagColor:"#c8922a",
    difficulty:"Easy", role:"Team Healer / Support / Medical RP",
    desc:"Field Medics keep people alive without relying on mana. Defined by tools, knowledge of medicine, and the ability to act fast in dangerous situations.",
    bestFor:"Support-focused players; medical RP; team sustain in long missions.",
    traitNote:"Field Medic trait (2pt) required for T2+ skills. Basic triage is available to all.",
    statPriority:[
      {stat:"Stamina",note:"HIGH PRIORITY — you must stay standing to keep people alive"},
      {stat:"Dexterity",note:"Moderate — dodge so you survive the fights you're healing through"},
      {stat:"Strength",note:"Low — you're not the attacker"},
    ],
    sampleBuild:{
      name:"The Front-Line Medic",
      traits:["Field Medic (2pt)","Bears Fortitude (1pt)","Perceptive (1pt)","Sixth Sense (1pt)"],
      stats:{strength:10,dexterity:40,stamina:100,magic_affinity:10,mana:10},statXP:160,
      skills:[
        {name:"Basic Medkits",cost:20,why:"20 XP — required foundation for everything"},
        {name:"Stabilization",cost:100,why:"Stop a death even without a kit available"},
        {name:"Advanced Medkits",cost:265,why:"Required for Surgery and Compound Medicine"},
        {name:"Prepared Medic I",cost:100,why:"Double Basic kit carry immediately"},
      ],skillXP:485,remaining:0,
      notes:["Free skill from Brassmere: Chemistry (Compound Medicine synergy) or Biology (+2 diagnosis rolls).","Stabilization at 100 XP prevents the 'out of kits during a crisis' situation. Never skip it.","Cannot attack or react while using a medkit — position carefully."],
    },
    chains:[
      {label:"MEDKITS",path:["Basic Medkits (T0)","Advanced Medkits (T1)","Surgery (T2)"]},
      {label:"MEDKITS",path:["Advanced Medkits (T1)","Compound Medicine (T1)"]},
      {label:"PREPARED",path:["Prepared Medic I (T0)","Prepared Medic II (T1)","Prepared Medic III (T2)"]},
      {label:"STANDALONE",path:["Stabilization (T1)"]},
    ],
    tips:[
      "Stabilization lets you save someone without a medkit. Always have this skill.",
      "Compound Medicine requires a Recipe Journal submission. Start planning recipes as soon as you unlock Advanced Medkits.",
      "Biology and Chemistry knowledge skills cost 100 XP each and stack directly with your medic rolls. Buy them.",
      "Field Medic vs Restoration Mage: you can create shareable medicines and treat mundane mental ailments. A mage can't.",
    ],
  },
  { id:"tactician", name:"Tactician", emoji:"🗺️", tag:"Tactician Trait — 2pt Subclass", tagColor:"#c8922a",
    difficulty:"Medium", role:"Battlefield Control / Team Buffs / Command",
    desc:"Tacticians don't deal the most damage — they make everyone else more effective. Command, positioning, and well-timed orders define this class.",
    bestFor:"Leadership-focused players; group combat; 3+ person teams.",
    traitNote:"Tactician trait (2pt) required for T2+ skills.",
    statPriority:[
      {stat:"Stamina",note:"HIGH PRIORITY — if you go down, your team loses all buffs"},
      {stat:"Dexterity",note:"Moderate — stay mobile to give orders"},
      {stat:"Strength",note:"Low — your value is in orders, not personal output"},
    ],
    sampleBuild:{
      name:"The Battlefield Commander",
      traits:["Tactician (2pt)","Charming (1pt)","Natural Leader (2pt)"],
      stats:{strength:20,dexterity:50,stamina:100,magic_affinity:10,mana:10},statXP:170,
      skills:[
        {name:"Tactical Orders I",cost:100,why:"Core ability — 100 XP for immediate value"},
        {name:"Tactical Orders II",cost:265,why:"2 targets; cheap and essential next step"},
        {name:"Target Tracking",cost:100,why:"Persistent +1/+3 bonuses all scene"},
        {name:"Doranswyr Historian",cost:100,why:"Gate to Martial Historian; only 100 XP"},
      ],skillXP:565,remaining:0,
      notes:["Charming (+1) + Natural Leader (+3) = +4 to ALL social skills at creation.","Martial Historian (750 XP) gives one free field strategy boon per open-field battle. Make it your first mid-game target.","Free skill from Bound origin: Doranswyr Historian — saves 100 XP."],
    },
    chains:[
      {label:"ORDERS",path:["Tactical Orders I (T0)","Tactical Orders II (T1)","Tactical Orders III (T2)"]},
      {label:"STRATEGY",path:["Target Tracking (T0)","Battlefield Awareness (T2)"]},
    ],
    tips:[
      "Your Tactical Orders are CHOICE skills — pick the effect when you use them. Read the situation before choosing output boost vs. dodge boost.",
      "Battlefield Awareness is a 1d20 roll. Invest in Knowledge skills and Luck to push that roll up.",
      "You shine in groups. In solo scenes, build personal combat capability as a backup.",
      "Tactical Orders III enemy-mark stacks multiplicatively with other bonuses — focus-fire strategies become devastating.",
    ],
  },
  { id:"smuggler", name:"Smuggler", emoji:"💰", tag:"Smuggler Trait — 2pt Subclass", tagColor:"#c8922a",
    difficulty:"Medium", role:"Stealth / Infiltration / Black Market",
    desc:"Smugglers move goods, information, and people through spaces they have no business being in. High DEX, low direct conflict, and high creative problem-solving.",
    bestFor:"Players who love creative solutions, stealth, and avoiding direct confrontation.",
    traitNote:"Smuggler trait (2pt) required for T2+ skills.",
    statPriority:[
      {stat:"Dexterity",note:"HIGH PRIORITY — stealth formula is DEX × 0.4. This is your primary stat."},
      {stat:"Stamina",note:"Moderate — survive if caught"},
      {stat:"Strength",note:"Dump stat — you avoid fights"},
    ],
    sampleBuild:{
      name:"The Ghost",
      traits:["Smuggler (2pt)","Cat's Grace (1pt)","Light Foot (1pt)","Actor (1pt)"],
      stats:{strength:10,dexterity:110,stamina:50,magic_affinity:10,mana:10},statXP:190,
      skills:[
        {name:"Light Load",cost:20,why:"20 XP; one item at weight 0 — always worth it"},
        {name:"Concealment",cost:100,why:"+5 solo stealth checks; always active"},
        {name:"Safer Routes",cost:100,why:"Advantage on retreat and disengage rolls"},
        {name:"Pilfer",cost:50,why:"Gate to full Stealth chain"},
        {name:"Stealth",cost:265,why:"Proper hide/sneak/ambush capability"},
      ],skillXP:535,remaining:0,
      notes:["110 DEX + Light Foot (+1) + Concealment (+5) + Stealth T1 tier bonus: Stealth formula hits 60+ at creation.","Black Market Access is only 500 XP. Make it an early-mid target.","Free skill from Wayfarer: Local Study: City-States."],
    },
    chains:[
      {label:"CARRY",path:["Light Load (T0)","Hidden Compartments (T1)"]},
      {label:"STEALTH",path:["Concealment (T0)","Mass Concealment (T1)"]},
      {label:"ROUTES",path:["Safer Routes (T0)","Ghost Run (T2)"]},
      {label:"MARKET",path:["Black Market Access (T2 standalone)"]},
    ],
    tips:[
      "Your stealth formula is (DEX × 0.4) + (Max Skill Tier × 10) + modifiers. Invest heavily in DEX.",
      "Safer Routes costs 2 AP. Always have those AP available when things go wrong.",
      "Mass Concealment covers the whole team. Even solo, having it unlocked means you can cover a full party infiltration.",
      "Criminal background in your backstory doubles your Black Market Access social bonus from +2 to +4.",
    ],
  },
  { id:"politician", name:"Politician", emoji:"⚖️", tag:"Politician Trait — 2pt Subclass", tagColor:"#c8922a",
    difficulty:"Medium–Hard", role:"Social Influence / Economy / Long-Term Planning",
    desc:"Politicians shape outcomes through influence, not force. The most RP-intensive class in the server — and the most rewarding if you invest in social presence and long-term planning.",
    bestFor:"RP-heavy players who enjoy negotiation, alliances, and economic strategy.",
    traitNote:"Politician trait (2pt) required for T2+ skills.",
    statPriority:[
      {stat:"Stamina",note:"Moderate — still need to survive in the field"},
      {stat:"Dexterity",note:"Light investment for basic survival mobility"},
      {stat:"Strength",note:"Minimal — you don't fight your own battles"},
    ],
    sampleBuild:{
      name:"The Silver Tongue",
      traits:["Politician (2pt)","Charming (1pt)","Natural Leader (2pt)"],
      stats:{strength:10,dexterity:40,stamina:70,magic_affinity:10,mana:10},statXP:100,
      skills:[
        {name:"Silver Tongue",cost:20,why:"20 XP for permanent +1 persuasion — always first"},
        {name:"Passive Income",cost:100,why:"Start generating income immediately"},
        {name:"Reputation Management",cost:100,why:"Reduce failure fallout; gate to Political Network"},
        {name:"Master Negotiator",cost:265,why:"Once-per-scene ceasefire advantage roll"},
      ],skillXP:485,remaining:0,
      notes:["Charming (+1) + Natural Leader (+3) + Silver Tongue (+1) = +5 to all persuasion at creation.","Political Network (265 XP) is your most important mid-game purchase. Maintain your ally list from day one.","Free skill from Imperial/Citadel: Local Study, Doranswyr Historian, or Linguistics."],
    },
    chains:[
      {label:"INFLUENCE",path:["Silver Tongue (T0)","Master Negotiator (T1)"]},
      {label:"NETWORK",path:["Reputation Management (T0)","Political Network (T1)"]},
      {label:"ECONOMY",path:["Passive Income (T0)","Investment Making (T2)"]},
      {label:"STANDALONE",path:["Contractional Servitude (T1 — req Silver Tongue + Reputation Mgmt)"]},
    ],
    tips:[
      "Passive Income has a cap of 5 sources, each paying 10–50 currency/month. Start early and let it build.",
      "Political Network requires you to maintain an ally list. Keep relationships updated and actively develop NPC connections.",
      "Contractional Servitude turns captured enemies into 3-scene assets that act before OR after you. Use it on strong enemies.",
      "Natural Leader requires Charming. If you take Charming you cannot take Threatening — a genuine identity choice.",
    ],
  },
  { id:"martial", name:"Martial", emoji:"⚔️", tag:"No Trait Required — Tracks Are Permanent", tagColor:"#8b4513",
    difficulty:"Easy–Medium", role:"Melee Combat — Heavy / Light / Martial Arts",
    desc:"Pure combat. Three mutually exclusive weapon tracks — choose one permanently. Heavy is a front-line aggro brawler. Light is a speed skirmisher. Martial Arts is a grapple-and-control specialist.",
    bestFor:"Combat-focused players; any playstyle that involves direct melee.",
    traitNote:"No class trait required. Tracks are mutually exclusive and PERMANENT — choose before spending XP.",
    statPriority:[
      {stat:"Strength",note:"CORE for Heavy. Less important for Light and MA but never dump it."},
      {stat:"Dexterity",note:"CORE for Light and MA. Also affects attack speed universally."},
      {stat:"Stamina",note:"HIGH PRIORITY for all builds — affects wound thresholds and crash recovery."},
    ],
    sampleBuild:{
      name:"Heavy: Iron Vanguard / Light: The Knife / MA: The Brawler",
      traits:["Gorilla Strength or Cat's Grace (1pt)","Bears Fortitude (1pt)","Sixth Sense (1pt)","Adrenaline Junky (2pt)"],
      stats:{strength:100,dexterity:30,stamina:80,magic_affinity:10,mana:10},statXP:300,
      skills:[
        {name:"Heavy / Light / Martial Arts base",cost:50,why:"T0 base — buy immediately"},
        {name:"Taunt / Duelist / Offensive Defense",cost:265,why:"Your T1 core skill for your track"},
        {name:"Honed Strike / Crowd Feint / Brawler",cost:265,why:"T1 burst or survivability skill"},
      ],skillXP:580,remaining:0,
      notes:["600 XP: base (50) + two T1 skills (530) + stat investment leaves you spending across creation + first session.","Free skill from Indomitable/High Sable: Martial Historian — best pick for any combat build.","Simple Ranged (50 XP) is open to ALL tracks. Cheap fallback for long-range gaps."],
    },
    chains:[
      {label:"HEAVY",path:["Heavy Armaments (T0)","Taunt → Dominion","Berserker → Sweeping Strike","Honed Strike → Mastered Strike"]},
      {label:"LIGHT",path:["Light Armaments (T0)","Crowd Feint → Swashbuckler","Unbound → Disarm","Duelist → Parry"]},
      {label:"MA",path:["Martial Arts (T0)","Offensive Defense → Furious Technique","Trance → Disarm","Brawler → Grappler → Form Mastery (T3)"]},
    ],
    tips:[
      "PICK YOUR TRACK BEFORE SPENDING XP. Heavy, Light, and MA are permanent and mutually exclusive.",
      "Berserker and Unbound both cause stat crashes after use. Never pop them at full health — use them to close a fight.",
      "Martial Arts requires HANDS FREE. Any wielded weapon disables the style entirely.",
      "Adept needs 4 combat OR class skills. You hit this threshold naturally by mid-game without trying.",
    ],
  },
  { id:"magecraft", name:"Magecraft", emoji:"🔥", tag:"Mana Circuits — 3pt Class Trait", tagColor:"#3b7dbf",
    difficulty:"Hard", role:"Source Magic — Offense / Healing / Support / Utility",
    desc:"The most complex tree in Railbound. You need a Force AND a School to cast anything. ALL spells must be approved before use. Design your first spells at character creation and submit immediately.",
    bestFor:"Players who want complexity, the highest power ceiling, and deep magical identity.",
    traitNote:"Mana Circuits (3pt) required for T2+ and Heavy/Extreme power bands. All-Rounders can use T0/T1 at Standard band max.",
    statPriority:[
      {stat:"Magic Affinity",note:"HIGH PRIORITY — drives spell output, Safe Output Limits, and Fortified Circuits formula"},
      {stat:"Mana",note:"HIGH PRIORITY — your fuel. Bigger pool = more spells per fight"},
      {stat:"Stamina",note:"Moderate — you still take hits in the field"},
    ],
    sampleBuild:{
      name:"Fire Mage (Destruction) or Water Mage (Restoration)",
      traits:["Mana Circuits (3pt)","Magic Background (1pt)","Dragon's Insight or Leviathan Depth (1pt)"],
      stats:{strength:10,dexterity:30,stamina:40,magic_affinity:100,mana:80},statXP:270,
      skills:[
        {name:"Force T0 (FREE)",cost:0,why:"Auto-granted with Mana Circuits"},
        {name:"School of Magic (FREE)",cost:0,why:"Free via Magic Background trait"},
        {name:"Mana Skin",cost:50,why:"Always take this — 50 XP magical damage reduction"},
        {name:"Force T1: Attunement",cost:66,why:"1/4 price at creation; unlocks Force bonuses immediately"},
        {name:"Mana Sensing",cost:50,why:"Tactical information every scene"},
      ],skillXP:166,remaining:164,
      notes:["With Magic Background, your first School is FREE. Take Restoration (Water) or Destruction (Fire).","You MUST get spells approved before use. Submit them during character creation, not after.","164 XP remaining: save toward Overcharge (500 XP) or Regeneration (500 XP) as first mid-game targets."],
    },
    chains:[
      {label:"FORCES",path:["T0: Knowledge (FREE w/ MC)","T1: Attunement","T2: Mastery","T3: Sorcery"]},
      {label:"RESTORE",path:["Restoration (T1)","Advanced Restoration (T2)","Mastered Restoration (T3)","+ Purification (T2)"]},
      {label:"ABJURE",path:["Abjuration (T1)","Wards / Barriers (T2)","Reflection (T3)"]},
      {label:"DESTROY",path:["Destruction (T1)","Offensive Area Magic (T2)"]},
      {label:"ALTER",path:["Alteration (T1)","Reinforcement / Weakening (T2)","Transformation (T3)"]},
      {label:"TELEMA",path:["Telemancy (T1)","Illusion / Telekinetics (T2)","Runic Study (T3)"]},
      {label:"SKILLS",path:["Mana Skin (T0)","Reflexive Mana Skin (T1)","Overcharge (T2)","Regeneration (T2)","Fortified Circuits (T3)"]},
    ],
    tips:[
      "You MUST get spells approved before use. Design 2–3 starter spells and submit them during character creation.",
      "Forces and Schools are interdependent — you can only use a Force equal to or greater than the School's tier.",
      "Mana Skin is 50 XP. There is no reason not to have this on any mage.",
      "Power Bands are decided at casting time. Learn when to use Minimal (5 mana) vs Standard (25 mana). Don't always cast at maximum.",
    ],
  },
  { id:"forgecraft", name:"Forgecraft", emoji:"⚙️", tag:"Forgeborn — 3pt Class Trait", tagColor:"#b8721a",
    difficulty:"Medium", role:"Crafting / Repair / Field Support / Engineering",
    desc:"Five crafting paths: Utility, Smithing, Snares, Demolition, Chemistry. Supply the team with weapons, armor, traps, and gadgets. Handle locks and mechanical systems in the field.",
    bestFor:"Players who enjoy the economy, item creation, and being the team's supply backbone.",
    traitNote:"Forgeborn (3pt) required for T2+ skills. T0/T1 open to all.",
    statPriority:[
      {stat:"Strength",note:"Moderate — not a frontliner but still gets into scrapes"},
      {stat:"Dexterity",note:"Moderate — lockpicking timing and basic dodge"},
      {stat:"Stamina",note:"Moderate-high — need to survive to craft and support"},
    ],
    sampleBuild:{
      name:"The Workshop",
      traits:["Forgeborn (3pt)","Conscientious (1pt)","Pack Mule (1pt)"],
      stats:{strength:50,dexterity:50,stamina:60,magic_affinity:10,mana:10},statXP:160,
      skills:[
        {name:"Tool Proficiency",cost:20,why:"+2 to ALL tool rolls — you always use tools"},
        {name:"Lockpicking",cost:50,why:"Cheap; opens Lock Mechanism; universally useful"},
        {name:"Utility Beginner",cost:100,why:"Foundation of ALL Forgecraft — required first"},
        {name:"Smithing Rookie",cost:100,why:"Start crafting combat gear immediately"},
        {name:"Beginning Repairman",cost:100,why:"Repair to 1/3 value; team utility from day one"},
        {name:"Field Stabilizer",cost:100,why:"+10% ally clashing output; exceptional 100 XP value"},
      ],skillXP:470,remaining:0,
      notes:["Free skill from Industrialist/Flywheel: Metallurgy — +2% output or +10% durability on all forged items.","Field Stabilizer at 100 XP gives +10% output to an ally for 1 turn. Use it every single fight.","Weekly crafting cap is real — 3 items/week at Rookie. Plan ahead of missions."],
    },
    chains:[
      {label:"UTILITY",path:["Utility Beginner (T1)","Practitioner (T2)","Expert (T3) ← REQUIRED FIRST"]},
      {label:"SMITH",path:["Smithing Rookie (T1)","Novice (T2)","Extraordinaire (T3)"]},
      {label:"SNARES",path:["Snare Trainee (T1)","Apprentice (T2)","Master (T3)"]},
      {label:"DEMO",path:["Demo Learner (T1)","Trainee (T2)","Specialist (T3)"]},
      {label:"CHEM",path:["Chemical Assistant (T1)","Analyst (T2)","Scientist (T3)"]},
      {label:"REPAIR",path:["Beginning Repairman (T1)","Intermediate (T2)","Master Repairman (T3)"]},
      {label:"SUPPORT",path:["Field Stabilizer (T1)","Field Stabilizer Extraordinaire (T3)"]},
    ],
    tips:[
      "Utility Beginner is mandatory first. No other crafting path unlocks without it.",
      "Plan your crafting specialty at character creation. Pick ONE path after Utility and commit to it.",
      "Conscientious (1pt trait) means items at 0 durability can still be repaired. Critical for a crafter.",
      "Radio Countermeasure (T2, 750 XP) creates 3 radios for secure 5m communication AND lets you clash against communication spells.",
    ],
  },
  { id:"guncraft", name:"Guncraft", emoji:"🔫", tag:"Gunslinger Training — 3pt Class Trait", tagColor:"#8b3030",
    difficulty:"Medium", role:"Ranged Combat — Multiple Gun Type Tracks",
    desc:"Unlike Martial weapon tracks, gun type tracks are NOT mutually exclusive. Invest in multiple if you want. DEX-based ranged combat with growing momentum.",
    bestFor:"Combat players who want range, speed, and DEX-based play.",
    traitNote:"Gunslinger Training (3pt) required for T2+ skills. T0/T1 open to all.",
    statPriority:[
      {stat:"Dexterity",note:"HIGH PRIORITY — attack speed, dodge, and most guncraft mechanics scale with DEX"},
      {stat:"Stamina",note:"HIGH PRIORITY — survive long enough to keep shooting"},
      {stat:"Strength",note:"Low-moderate — melee fallback if enemies close distance"},
    ],
    sampleBuild:{
      name:"The Sharpshooter",
      traits:["Gunslinger Training (3pt)","Cat's Grace (1pt)","Sixth Sense (1pt)"],
      stats:{strength:10,dexterity:110,stamina:60,magic_affinity:10,mana:10},statXP:200,
      skills:[
        {name:"Fast Hands",cost:50,why:"50 XP; free action ammo swap — always purchase first"},
        {name:"Alert",cost:100,why:"Required for Eagle Eye; significantly harder to ambush"},
        {name:"Good Eyes",cost:265,why:"+5m throw range; required for Eagle Eye"},
        {name:"Rifle Training",cost:100,why:"T1 rifle skills + rifles; primary weapon track"},
      ],skillXP:515,remaining:0,
      notes:["Eagle Eye (750 XP) requires Good Eyes + Alert. Both purchased at creation — Eagle Eye is your first mid-game target.","Gun-Fu (900 XP) solves your biggest vulnerability: fire point blank to escape grapples.","Artillery and Shot Techniques tracks are NOT RELEASED yet. Don't plan XP around them."],
    },
    chains:[
      {label:"REVOLVER",path:["Wheelgun Familiarity (T1)","Quickdraw (T2)","Revolver Virtuoso (T3)"]},
      {label:"RIFLE",path:["Rifle Training (T1)","Sharpshooter (T2)","Deadeye Marksman (T3)"]},
      {label:"SHOTGUN",path:["Scattergun Familiarity (T1)","Close-Quarters (T2)","Breacher (T3)"]},
      {label:"GENERAL",path:["Fast Hands (T0)","Good Eyes + Alert (T1)","Eagle Eye (T2)"]},
      {label:"RELOAD",path:["Lesser Reload (T2)","Veteran Reload (T3)"]},
      {label:"OTHER",path:["Covered Shot (T1)","Gun-Fu (T2)","Gunmaster's Flow (T3)"]},
    ],
    tips:[
      "Gun tracks are NOT mutually exclusive — invest in Rifle AND Revolver if it fits your concept.",
      "Eagle Eye needs BOTH Good Eyes and Alert. Buy both early so Eagle Eye is accessible mid-game.",
      "Fast Hands is 50 XP and lets you swap ammo as a FREE action. Different ammo types have different effects.",
      "Covered Shot only gives the bonus while actively behind cover. Learn to use terrain.",
    ],
  },
  { id:"beastmaster", name:"Beastmaster", emoji:"🐊", tag:"Loyal Companion — 3pt Class Trait", tagColor:"#3d7a3d",
    difficulty:"Hard", role:"Two-Character Build — OC + Source Beast",
    desc:"A two-character build where you and your Source Beast grow together. Plan both your OC AND your Beast from day one. Everything is weaker alone but together you're a flexible persistent threat.",
    bestFor:"Players who want a unique long-term growth arc and two-character coordination.",
    traitNote:"Loyal Companion (3pt) required for T2+. Severs your direct Source access — you CANNOT cast spells or power magical items.",
    statPriority:[
      {stat:"Dexterity",note:"HIGH — your dodge and reaction directly protect the Beast from losing bonuses"},
      {stat:"Stamina",note:"HIGH — if you go down, your Beast loses all shared bonuses and Advanced Command"},
      {stat:"Beast Primary Stat",note:"Invest Beast XP into STR (Combat), STA (Mount), or Mana (Support)"},
    ],
    sampleBuild:{
      name:"The Bonded Pair",
      traits:["Loyal Companion (3pt)","Beast Handler (1pt)","Perceptive (1pt)"],
      stats:{strength:50,dexterity:80,stamina:80,magic_affinity:20,mana:10},statXP:250,
      skills:[
        {name:"Obedience",cost:50,why:"Advanced commands; first Beast utility step"},
        {name:"Proficient Command",cost:100,why:"Use Bonus Action to command Beast in combat"},
        {name:"Mauling",cost:265,why:"Beast grapple + attack; primary offensive tool"},
        {name:"Mana Skin",cost:50,why:"Runs on Beast's mana; magical damage reduction"},
      ],skillXP:465,remaining:0,
      notes:["Beast starts at 5 in all stats. Apply the 10% OC stat modifier immediately — this is FREE.","Beast Skills are currently LOCKED. Plan your path but hold the XP until they release.","Shared Experience (900 XP) is your most important mid-game investment — it funds the Beast long-term.","Free skill from Survivalist/Thornwick: Biology — stacks with Veterinary Study for treating your Beast."],
    },
    chains:[
      {label:"COMMAND",path:["Obedience (T0)","Proficient Command (T1)","Advanced Command (T2)"]},
      {label:"GROWTH",path:["Shared Experience (T2)","Shared Experience II (T3)"]},
      {label:"BOND",path:["Remote Sense (T2)","Spectral Bond (T3)"]},
      {label:"COMBAT",path:["Battle Bond (T1)","Bonded Soul (T2)"]},
      {label:"COMBAT",path:["Hound Strike (T1)","Ravaged Strike (T3)"]},
      {label:"MOUNT",path:["Increased Inventory (T1)","Escape Artist (T2)","True Rider (T3)"]},
      {label:"SUPPORT",path:["Magical Defense I (T1)","Magical Defense II (T2)","Barrier or Wards (T3)"]},
    ],
    tips:[
      "Your Beast starts at 5 in ALL stats. The 10% OC stat modifier is FREE and applies automatically — record both BASE and MODIFIED stats.",
      "Beast Skills are currently LOCKED. Plan but don't budget XP yet.",
      "You CANNOT access Source directly. Mana Skin and Mana Sensing run on your Beast's mana and affinity stats, not yours.",
      "Action economy is your core power ladder: sacrifice yours → Proficient Command → Advanced Command (Beast has its own).",
      "Source Beasts have half OC injury capacity. A single T4 is equivalent to a T5 for them. Protect your Beast.",
    ],
  },
];

const CITIES = [
  {id:"lumenhold",name:"Lumenhold",tag:"Academy City",desc:"Deep in the Red Desert. A city of scholars run by the Illuminated Conclave. Intellectual, intense, opinion-heavy."},
  {id:"gearford",name:"Gearford",tag:"Industrial Hub",desc:"Built from labor. If you can build, fix, or improve something, you have a place. Merchant Council meritocracy."},
  {id:"flywheel",name:"Flywheel",tag:"Hydro City",desc:"Most technologically advanced city-state, built on the Grand Wheel hydroelectric dam. Technocratic Directorate of Flow."},
  {id:"ashgate",name:"Ashgate",tag:"Trade Crossroads",desc:"Where ancient trade routes converge. Wealth and information flow as freely as coin. The Vaelor dynasty rules."},
  {id:"thornwick",name:"Thornwick",tag:"Frontier City",desc:"Built at the edge of the Blackwood Frontier. Hunters, trackers, wardens. Survival depends on discipline and strength."},
  {id:"cinder",name:"Cinder",tag:"Forge City",desc:"Rebuilt from ash after the Burning of Cinderfell. Welcoming city of smiths led by the beloved King Faren Zamor."},
  {id:"high_sable",name:"High Sable",tag:"Cliff Fortress",desc:"Carved into a sheer cliff face. Life revolves around vigilance and preparedness. Every citizen contributes to defense."},
  {id:"brassmere",name:"Brassmere",tag:"Industrial Port",desc:"Gleams from afar, darker up close. Magic and machinery blur together. The Experimental Bureau keeps secrets."},
  {id:"morthand",name:"Morthand",tag:"Theocracy",desc:"Ruled by the masked Holy Tribunal. Peaceful, orderly, deeply isolationist. Entry by permit only."},
  {id:"citadel",name:"The Citadel",tag:"Imperial Seat",desc:"Once a capital, always a capital. Imperator Vegard Ragon rules. The middle class thrives. Imperial College open to all."},
  {id:"outlands",name:"The Outlands",tag:"No City-State",desc:"Born beyond the city-states — a settlement, a caravan, or the wilderness. More freedom, less protection."},
];

const CLASSES_QUICK = [
  {id:"none",name:"All-Rounder",trait:"No class trait",cost:0,icon:Star,desc:"Generalist. Access to Keystone traits.",bestFor:"Versatility, XP grinders"},
  {id:"mana",name:"Magecraft",trait:"Mana Circuits (3pt)",cost:3,icon:Zap,desc:"Source magic. Spell approval required.",bestFor:"Magic offense, healing, utility"},
  {id:"forgeborn",name:"Forgecraft",trait:"Forgeborn (3pt)",cost:3,icon:Wrench,desc:"Five crafting paths. Supply the team.",bestFor:"Crafting, traps, engineering"},
  {id:"gunslinger",name:"Guncraft",trait:"Gunslinger Training (3pt)",cost:3,icon:Target,desc:"Multiple gun tracks. DEX-based combat.",bestFor:"Ranged combat, DEX builds"},
  {id:"companion",name:"Beastmaster",trait:"Loyal Companion (3pt)",cost:3,icon:PawPrint,desc:"Two-character build with Source Beast.",bestFor:"Unique RP, two-character play"},
  {id:"martial_h",name:"Martial — Heavy",trait:"No trait needed",cost:0,icon:Swords,desc:"Heavy weapons. Aggro, Berserker, Dominion.",bestFor:"Melee tanking, burst damage"},
  {id:"martial_l",name:"Martial — Light",trait:"No trait needed",cost:0,icon:Swords,desc:"Light weapons. Speed, feinting, Parry.",bestFor:"Skirmishing, counter-attacks"},
  {id:"martial_ma",name:"Martial Arts",trait:"No trait needed",cost:0,icon:Swords,desc:"Unarmed. +4% base damage. Grapples.",bestFor:"Grappling, disarms, unarmed"},
  {id:"medic",name:"Field Medic",trait:"Field Medic (2pt)",cost:2,icon:Shield,desc:"Science-based healing without mana.",bestFor:"Team healing, medical RP"},
  {id:"tactician",name:"Tactician",trait:"Tactician (2pt)",cost:2,icon:Users,desc:"Command, buff allies, read the fight.",bestFor:"Leadership, group combat"},
  {id:"smuggler",name:"Smuggler",trait:"Smuggler (2pt)",cost:2,icon:Star,desc:"Stealth, routes, black market.",bestFor:"Infiltration, information"},
  {id:"politician",name:"Politician",trait:"Politician (2pt)",cost:2,icon:Users,desc:"Influence, income, negotiation.",bestFor:"Social RP, economy"},
];

const TRAIT_TIERS = [
  {label:"Class Traits — 3pts each (MUTUALLY EXCLUSIVE)",note:"Pick only ONE. Cannot combine with Keystone traits.",
   traits:[{name:"Mana Circuits",cost:3,desc:"Unlocks Magecraft T2+. Free T0 Force."},{name:"Forgeborn",cost:3,desc:"Unlocks Forgecraft T2+."},{name:"Gunslinger Training",cost:3,desc:"Unlocks Guncraft T2+."},{name:"Loyal Companion",cost:3,desc:"Unlocks Beastmaster T2+. Severs Source access."}]},
  {label:"Subclass Traits — 2pts each",note:"Can combine with class traits.",
   traits:[{name:"Field Medic",cost:2,desc:"Unlocks Field Medic T2+."},{name:"Tactician",cost:2,desc:"Unlocks Tactician T2+."},{name:"Smuggler",cost:2,desc:"Unlocks Smuggler T2+."},{name:"Politician",cost:2,desc:"Unlocks Politician T2+."}]},
  {label:"Keystone Traits — 3pts each (ALL-ROUNDER ONLY)",note:"Cannot combine with class traits (except Greater Knowledge).",
   traits:[{name:"Self-Made Survivor",cost:3,desc:"1.3× XP from missions. Caps at 5pts."},{name:"Selective Fortune",cost:3,desc:"1.15× XP for you OR one ally. +1pt."},{name:"Quiet Benefactor",cost:3,desc:"1.2× rewards for others. +2pt."},{name:"Greater Knowledge",cost:3,desc:"Once/week: ask GM for secret info. Requires Source Sensitivity."}]},
  {label:"Reliable Traits — 2pts each",note:"Meaningful passive bonuses.",
   traits:[{name:"Knowledgeable",cost:2,desc:"+3 to ALL Knowledge checks."},{name:"Natural Leader",cost:2,desc:"Req Charming/Threatening. +3 social."},{name:"Adrenaline Junky",cost:2,desc:"Output boosts based on injuries carried."},{name:"Hardy Constitution",cost:2,desc:"Req Bears Fortitude. Reduces permanent injury effects."}]},
  {label:"Minor Traits — 1pt each",note:"Small but always-active bonuses.",
   traits:[{name:"Charming",cost:1,desc:"+1 Persuasion/Charm. Req for Natural Leader."},{name:"Threatening",cost:1,desc:"+1 Intimidation. Req for Natural Leader. Can't stack with Charming."},{name:"Sixth Sense",cost:1,desc:"+2% Reaction/Dodge. Always active."},{name:"Light Foot",cost:1,desc:"+1 to all stealth rolls."},{name:"Perceptive",cost:1,desc:"+1 to all observation checks."},{name:"Cat's Grace",cost:1,desc:"+5% DEX (permanent)."},{name:"Gorilla Strength",cost:1,desc:"+5% STR (permanent)."},{name:"Bears Fortitude",cost:1,desc:"+5% STA (permanent)."},{name:"Dragon's Insight",cost:1,desc:"+5% Mag Affinity → +10% via Merlin's Skill."},{name:"Leviathan Depth",cost:1,desc:"+5% Mana → +10% via Merlin's Skill."},{name:"Lucky Spark",cost:1,desc:"+1 Luck. Affects GM rolls."},{name:"Actor",cost:1,desc:"+1 deception; +2 in disguise."}]},
];

const STARTING_SKILLS = [
  {key:"pilfer",name:"Pilfer",cost:50,tree:"Mercenary",desc:"Sleight-of-hand, pickpocket. Gate to Stealth chain."},
  {key:"magic_tool",name:"Magic Tool Use",cost:50,tree:"Mercenary",desc:"Activate enchanted items."},
  {key:"riding",name:"Riding & Driving",cost:50,tree:"Mercenary",desc:"Ride mounts and drive vehicles."},
  {key:"stealth",name:"Stealth",cost:265,tree:"Mercenary",desc:"Hide, sneak, and set ambushes. Requires Pilfer."},
  {key:"simple_ranged",name:"Simple Ranged",cost:50,tree:"Martial",desc:"Use bows, crossbows, slingshots."},
  {key:"heavy_arms",name:"Heavy Armaments",cost:50,tree:"Martial",desc:"+2% damage with heavy weapons."},
  {key:"light_arms",name:"Light Armaments",cost:50,tree:"Martial",desc:"+2% damage with light weapons."},
  {key:"martial_arts",name:"Martial Arts",cost:50,tree:"Martial",desc:"+4% damage unarmed. Hands must be free."},
  {key:"taunt",name:"Taunt",cost:265,tree:"Martial",desc:"Draw enemy attention. −10% reaction to ally attacks."},
  {key:"berserker",name:"Berserker",cost:265,tree:"Martial",desc:"STR/DEX/STA ×1.10 for 3 turns. Crash after."},
  {key:"linguistics",name:"Linguistics",cost:100,tree:"Knowledge",desc:"+2 language checks. Gate to Print Forgery."},
  {key:"biology",name:"Biology",cost:100,tree:"Knowledge",desc:"Diagnose diseases. Gate to Vet Study."},
  {key:"history",name:"Doranswyr Historian",cost:100,tree:"Knowledge",desc:"LORE ACCESS. Gate to Martial Historian."},
  {key:"fast_hands",name:"Fast Hands",cost:50,tree:"Guncraft",desc:"Swap ammo or switch guns as a FREE action."},
  {key:"alert",name:"Alert",cost:100,tree:"Guncraft",desc:"Harder to ambush. Required for Eagle Eye."},
  {key:"wheelgun",name:"Wheelgun Familiarity",cost:100,tree:"Guncraft",desc:"Unlocks T1 revolver skills and revolvers."},
  {key:"rifle",name:"Rifle Training",cost:100,tree:"Guncraft",desc:"Unlocks T1 rifle skills and rifles."},
  {key:"mana_skin",name:"Mana Skin",cost:50,tree:"Magecraft",desc:"−10% magical damage taken. 2% mana/turn drain."},
  {key:"mana_sensing",name:"Mana Sensing",cost:50,tree:"Magecraft",desc:"Detect wards, catalysts, and mana-users in range."},
  {key:"tool_prof",name:"Tool Proficiency",cost:20,tree:"Forgecraft",desc:"+2 to ALL tool-use rolls."},
  {key:"lockpicking",name:"Lockpicking",cost:50,tree:"Forgecraft",desc:"+2 lockpicking. Gate to Lock Mechanism."},
  {key:"utility_beg",name:"Utility Beginner",cost:100,tree:"Forgecraft",desc:"Foundation of ALL Forgecraft. Required for every path."},
  {key:"field_stab",name:"Field Stabilizer",cost:100,tree:"Forgecraft",desc:"+10% ally clashing output for 1 turn."},
  {key:"basic_medkits",name:"Basic Medkits",cost:20,tree:"Field Medic",desc:"Craft and use basic medkits."},
  {key:"stabilization",name:"Stabilization",cost:100,tree:"Field Medic",desc:"Stabilise someone even without a medkit."},
  {key:"tactical_i",name:"Tactical Orders I",cost:100,tree:"Tactician",desc:"Buff 1 ally's output or dodge."},
  {key:"light_load",name:"Light Load",cost:20,tree:"Smuggler",desc:"Mark one item as weight 0."},
  {key:"concealment",name:"Concealment",cost:100,tree:"Smuggler",desc:"+5 to solo stealth checks. Always active."},
  {key:"silver_tongue",name:"Silver Tongue",cost:20,tree:"Politician",desc:"+1 to persuasion. Gate to Master Negotiator."},
  {key:"obedience",name:"Obedience",cost:50,tree:"Beastmaster",desc:"Give advanced non-combat commands to pets."},
  {key:"prof_command",name:"Proficient Command",cost:100,tree:"Beastmaster",desc:"Bonus Action to command companion in combat."},
];

const CREATION_STEPS = [
  {id:1,title:"Background",subtitle:"Where are you from?"},
  {id:2,title:"Class",subtitle:"What do you do?"},
  {id:3,title:"Traits",subtitle:"Who are you?"},
  {id:4,title:"Stats",subtitle:"How are you built?"},
  {id:5,title:"Skills",subtitle:"What have you learned?"},
  {id:6,title:"Review",subtitle:"Your starting build"},
];

export default function GettingStartedDashboard({discordId,jump}:{discordId:string;jump?:(tab:any)=>void;}) {
  const [hubTab,setHubTab]=useState<HubTab>("start");
  const [selectedClass,setSelectedClass]=useState<string|null>(null);
  const [build,setBuild]=useState<BuildState>({
    city:"",classChoice:"",selectedTraits:[],
    stats:{strength:10,dexterity:10,stamina:10,magic_affinity:10,mana:10},
    selectedSkills:[],step:1,
  });

  const statXP=totalStatXP(build.stats);
  const skillXP=totalSkillXP(build.selectedSkills,STARTING_SKILLS);
  const xpSpent=statXP+skillXP;
  const xpLeft=600-xpSpent;
  const xpPct=Math.min(100,(xpSpent/600)*100);
  const xpColor=xpLeft<0?"#e05555":xpLeft<80?"#c8922a":"#2f6f73";

  const traitPtsUsed=build.selectedTraits.reduce((sum,t)=>{
    for(const tier of TRAIT_TIERS){const f=tier.traits.find(x=>x.name===t);if(f)return sum+f.cost;}return sum;
  },0);

  function updateStep(n:number){setBuild(p=>({...p,step:n}));}
  function toggleTrait(name:string,cost:number){
    if(build.selectedTraits.includes(name)){setBuild(p=>({...p,selectedTraits:p.selectedTraits.filter(t=>t!==name)}));}
    else{if(traitPtsUsed+cost>5)return;setBuild(p=>({...p,selectedTraits:[...p.selectedTraits,name]}));}
  }
  function toggleSkill(key:string,cost:number){
    if(build.selectedSkills.includes(key)){setBuild(p=>({...p,selectedSkills:p.selectedSkills.filter(s=>s!==key)}));}
    else{if(xpLeft<cost)return;setBuild(p=>({...p,selectedSkills:[...p.selectedSkills,key]}));}
  }

  const pill=(active:boolean,color="#2f6f73"):React.CSSProperties=>({
    padding:"10px 14px",border:`1px solid ${active?color:"#e0d4c4"}`,borderRadius:"8px",
    cursor:"pointer",background:active?`${color}10`:"white",transition:"all 0.12s",
  });
  const xc=xpColor;
  const XPBadge=()=><span style={{fontFamily:"monospace",fontSize:"13px",fontWeight:700,color:xc,background:`${xc}18`,padding:"4px 12px",borderRadius:"6px"}}>{xpLeft<0?`${Math.abs(xpLeft)} XP over`:`${xpLeft} XP left`}</span>;
  const XPBar=()=>(
    <div style={{marginBottom:"20px"}}>
      <div style={{height:"7px",background:"#e0d4c4",borderRadius:"4px",overflow:"hidden",marginBottom:"6px"}}>
        <div style={{height:"100%",width:`${xpPct}%`,background:xpLeft<0?"#e05555":"#2f6f73",transition:"width 0.2s",borderRadius:"4px"}}/>
      </div>
      <div style={{display:"flex",justifyContent:"space-between",fontSize:"12px",color:"#888"}}>
        <span>Stats: <strong>{statXP}</strong></span><span>Skills: <strong>{skillXP}</strong></span>
        <span style={{color:xc,fontWeight:700}}>{xpSpent} / 600 XP</span>
      </div>
    </div>
  );
  const BackNext=({onBack,onNext,nextLabel="Next",nextDisabled=false}:any)=>(
    <div style={{display:"flex",justifyContent:"space-between",marginTop:"20px"}}>
      <button className="ghost" onClick={onBack} style={{display:"flex",alignItems:"center",gap:"6px"}}><ChevronLeft size={15}/>Back</button>
      <button onClick={onNext} disabled={nextDisabled} style={{display:"flex",alignItems:"center",gap:"6px"}}>{nextLabel}<ChevronRight size={15}/></button>
    </div>
  );

  const HUB_TABS:[{id:HubTab;label:string;icon:React.ReactNode}] = [
    {id:"start",label:"Start Here",icon:<Home size={14}/>},
    {id:"create",label:"Character Creation",icon:<BookOpen size={14}/>},
    {id:"classes",label:"Class Guides",icon:<Map size={14}/>},
    {id:"skills",label:"Skills",icon:<Sparkles size={14}/>},
    {id:"world",label:"World",icon:<Globe size={14}/>},
    {id:"guide",label:"Server Guide",icon:<Scroll size={14}/>},
  ] as any;

  const TabBar=({onClassTab=false}:{onClassTab?:boolean})=>(
    <div style={{padding:"24px 28px 0",borderBottom:"1px solid #e0d4c4"}}>
      <span className="activity-type-label">Getting Started</span>
      <h2 style={{margin:"6px 0 4px"}}>Railbound Player Hub</h2>
      <p className="muted-text" style={{fontSize:"13px",marginBottom:"16px"}}>Everything a new player needs — character creation, skill reference, world lore, and server guide.</p>
      <div style={{display:"flex",gap:"2px",flexWrap:"wrap"}}>
        {HUB_TABS.map((t:any)=>(
          <button key={t.id} onClick={()=>{setHubTab(t.id);if(t.id!=="classes")setSelectedClass(null);}}
            className={hubTab===t.id?"":"ghost"}
            style={{display:"flex",alignItems:"center",gap:"6px",fontSize:"13px",padding:"9px 16px",
              borderRadius:"8px 8px 0 0",marginBottom:"-1px",
              borderBottom:hubTab===t.id?"2px solid #2f6f73":"2px solid transparent"}}>
            {t.icon}{t.label}
          </button>
        ))}
      </div>
    </div>
  );

  // ── FULL CLASS GUIDE VIEW ─────────────────────────────────────────────────
  const activeGuide=selectedClass?CLASS_GUIDES.find(g=>g.id===selectedClass):null;
  if(hubTab==="classes"&&activeGuide){
    const g=activeGuide;
    return(
      <section>
        <TabBar/>
        <div style={{padding:"28px",maxWidth:"900px"}}>
          <button className="ghost" onClick={()=>setSelectedClass(null)}
            style={{display:"flex",alignItems:"center",gap:"6px",marginBottom:"24px",fontSize:"13px"}}>
            <ChevronLeft size={15}/>All Classes
          </button>
          {/* Hero */}
          <div className="card" style={{padding:"24px 28px",marginBottom:"20px",borderLeft:`4px solid ${g.tagColor}`,background:`linear-gradient(135deg,${g.tagColor}08,#f6efe4)`}}>
            <div style={{display:"flex",alignItems:"flex-start",gap:"16px",flexWrap:"wrap"}}>
              <span style={{fontSize:"48px",lineHeight:1}}>{g.emoji}</span>
              <div style={{flex:1}}>
                <div style={{display:"flex",alignItems:"center",gap:"10px",flexWrap:"wrap",marginBottom:"6px"}}>
                  <h2 style={{margin:0}}>{g.name}</h2>
                  <span className="activity-type-label" style={{background:`${g.tagColor}15`,color:g.tagColor}}>{g.tag}</span>
                  <span className="activity-type-label">{g.difficulty}</span>
                </div>
                <p style={{fontSize:"13px",color:"#555",lineHeight:"1.6",marginBottom:"8px"}}>{g.desc}</p>
                <p style={{fontSize:"13px",color:g.tagColor,fontWeight:600}}>Best for: {g.bestFor}</p>
              </div>
            </div>
          </div>
          {/* Trait + Stat priority */}
          <div style={{display:"grid",gridTemplateColumns:"1fr 1fr",gap:"16px",marginBottom:"16px"}}>
            <div className="card" style={{padding:"16px"}}>
              <div className="card-title-row" style={{marginBottom:"10px"}}><strong>Trait Requirement</strong></div>
              <p style={{fontSize:"13px",color:"#555",lineHeight:"1.6"}}>{g.traitNote}</p>
            </div>
            <div className="card" style={{padding:"16px"}}>
              <div className="card-title-row" style={{marginBottom:"10px"}}><strong>Stat Priority</strong></div>
              {g.statPriority.map((s:any)=>(
                <div key={s.stat} style={{marginBottom:"6px",fontSize:"13px"}}>
                  <strong style={{color:"#2f6f73"}}>{s.stat}: </strong><span style={{color:"#555"}}>{s.note}</span>
                </div>
              ))}
            </div>
          </div>
          {/* Skill chains */}
          <div className="card" style={{padding:"16px",marginBottom:"16px"}}>
            <div className="card-title-row" style={{marginBottom:"14px"}}>
              <strong>Skill Chains</strong>
              <span className="activity-type-label">Gray=T0 · Green=T1 · Blue=T2 · Orange=T3</span>
            </div>
            {g.chains.map((chain:any,ci:number)=>(
              <div key={ci} style={{display:"flex",alignItems:"center",gap:"6px",marginBottom:"8px",flexWrap:"wrap"}}>
                <span style={{fontFamily:"monospace",fontSize:"10px",color:"#888",width:"75px",flexShrink:0,letterSpacing:"1px"}}>{chain.label}</span>
                {chain.path.map((node:string,ni:number)=>{
                  const c=node.includes("T0")?"#888":node.includes("T1")?"#4caf7d":node.includes("T2")?"#4488dd":node.includes("T3")?"#dd7733":"#888";
                  return(
                    <React.Fragment key={ni}>
                      <span style={{fontFamily:"monospace",fontSize:"11px",color:c,border:`1px solid ${c}`,padding:"3px 8px",borderRadius:"4px",background:`${c}10`}}>{node}</span>
                      {ni<chain.path.length-1&&<span style={{color:"#ccc",fontSize:"12px"}}>→</span>}
                    </React.Fragment>
                  );
                })}
              </div>
            ))}
          </div>
          {/* Sample build */}
          <div className="card" style={{padding:0,overflow:"hidden",marginBottom:"16px"}}>
            <div style={{padding:"14px 18px",background:"#2c241e"}}>
              <span style={{fontFamily:"monospace",fontSize:"11px",color:"#888",letterSpacing:"2px"}}>⚙ SAMPLE STARTING BUILD — </span>
              <span style={{fontFamily:"monospace",fontSize:"13px",fontWeight:700,color:"white"}}>{g.sampleBuild.name.toUpperCase()}</span>
            </div>
            <div style={{display:"grid",gridTemplateColumns:"1fr 1fr",borderBottom:"1px solid #e0d4c4"}}>
              <div style={{padding:"16px",borderRight:"1px solid #e0d4c4"}}>
                <div style={{fontSize:"11px",fontWeight:700,letterSpacing:"2px",color:"#888",marginBottom:"10px"}}>TRAITS</div>
                {g.sampleBuild.traits.map((t:string)=>(
                  <div key={t} style={{fontSize:"13px",color:"#2c241e",marginBottom:"5px",display:"flex",gap:"6px"}}>
                    <Check size={12} color="#2f6f73" style={{flexShrink:0,marginTop:"2px"}}/>{t}
                  </div>
                ))}
              </div>
              <div style={{padding:"16px"}}>
                <div style={{fontSize:"11px",fontWeight:700,letterSpacing:"2px",color:"#888",marginBottom:"10px"}}>STARTING STATS</div>
                {STAT_KEYS.map(key=>{
                  const val=(g.sampleBuild.stats as any)[key]??10;
                  const xp=calcStatXP(10,val);
                  return(
                    <div key={key} style={{display:"flex",justifyContent:"space-between",fontSize:"13px",marginBottom:"5px"}}>
                      <span style={{color:"#888"}}>{STAT_LABELS[key]}</span>
                      <span><strong>{val}</strong>{xp>0&&<span style={{color:"#2f6f73",marginLeft:"6px",fontSize:"11px"}}>+{xp}xp</span>}</span>
                    </div>
                  );
                })}
              </div>
            </div>
            <div style={{padding:"14px 18px 4px",borderBottom:"1px solid #e0d4c4"}}>
              <div style={{fontSize:"11px",fontWeight:700,letterSpacing:"2px",color:"#888",marginBottom:"10px"}}>
                SKILL PURCHASES — {g.sampleBuild.skillXP+g.sampleBuild.statXP} XP SPENT | {g.sampleBuild.remaining} XP REMAINING
              </div>
              {g.sampleBuild.skills.map((s:any)=>(
                <div key={s.name} style={{display:"flex",alignItems:"center",gap:"10px",marginBottom:"8px",fontSize:"13px"}}>
                  <strong style={{width:"190px",flexShrink:0}}>{s.name}</strong>
                  <span style={{color:"#888",fontFamily:"monospace",fontSize:"11px"}}>{s.cost} XP</span>
                  <span style={{color:"#555"}}>— {s.why}</span>
                </div>
              ))}
            </div>
            <div style={{padding:"14px 18px",background:"#faf7f3"}}>
              {g.sampleBuild.notes.map((n:string,i:number)=>(
                <p key={i} style={{fontSize:"12px",color:"#666",marginBottom:"5px",display:"flex",gap:"8px"}}>
                  <span style={{color:"#2f6f73",flexShrink:0}}>◆</span>{n}
                </p>
              ))}
            </div>
          </div>
          {/* Tips */}
          <div className="card" style={{padding:"16px"}}>
            <div className="card-title-row" style={{marginBottom:"14px"}}><strong>Tips & Reminders</strong></div>
            {g.tips.map((tip:string,i:number)=>(
              <div key={i} style={{display:"flex",gap:"10px",marginBottom:"10px",fontSize:"13px"}}>
                <span style={{color:"#2f6f73",flexShrink:0,marginTop:"2px"}}>◆</span>
                <span style={{color:"#555",lineHeight:"1.6"}}>{tip}</span>
              </div>
            ))}
          </div>
        </div>
      </section>
    );
  }

  // ── MAIN HUB ─────────────────────────────────────────────────────────────
  return(
    <section>
      <TabBar/>
      <div style={{padding:"28px"}}>

        {/* START HERE */}
        {hubTab==="start"&&(
          <div style={{maxWidth:"820px"}}>
            <div className="card" style={{marginBottom:"20px",borderLeft:"4px solid #2f6f73"}}>
              <h3 style={{marginBottom:"8px"}}>Welcome to Railbound RP</h3>
              <p style={{fontSize:"14px",color:"#555",lineHeight:"1.7",marginBottom:"10px"}}>
                Railbound is a Discord roleplay server set in <strong>Doranswyr</strong> — a fractured continent in its early industrial era (~1845). Steam engines and revolvers exist alongside Source magic, mythical beasts, and the ruins of a 1,800-year-old Republic that collapsed 30 years ago.
              </p>
              <p style={{fontSize:"14px",color:"#555",lineHeight:"1.7"}}>
                You play as a character working within one of four <strong>mercenary guilds</strong> — neutral contractors who operate across all city-states, bound by contracts rather than national loyalty.
              </p>
            </div>
            <h3 style={{marginBottom:"14px"}}>What to do first</h3>
            <div style={{display:"grid",gridTemplateColumns:"repeat(auto-fill, minmax(220px,1fr))",gap:"10px",marginBottom:"24px"}}>
              {[{num:"01",title:"Read the rules",desc:"Check #rules and #server-info before anything else."},{num:"02",title:"Use the Character Creator",desc:"Click the Character Creation tab and follow the guided flow."},{num:"03",title:"Fill out your OC sheet",desc:"Copy the OC Draft Template Google Doc and fill it out completely."},{num:"04",title:"Submit for approval",desc:"Open a ticket in #oc-submissions with your sheet link."},{num:"05",title:"Get your guild role",desc:"Once approved, staff assigns your guild and OC roles."},{num:"06",title:"Start RPing",desc:"Head to an open RP channel or sign up for a mission."}].map(s=>(
                <div key={s.num} className="card" style={{padding:"14px"}}>
                  <div style={{display:"flex",alignItems:"center",gap:"8px",marginBottom:"6px"}}>
                    <span style={{fontFamily:"monospace",fontSize:"11px",color:"#2f6f73",fontWeight:700,background:"#2f6f7315",padding:"3px 7px",borderRadius:"4px"}}>{s.num}</span>
                    <strong style={{fontSize:"13px"}}>{s.title}</strong>
                  </div>
                  <p className="muted-text" style={{fontSize:"12px",lineHeight:"1.5"}}>{s.desc}</p>
                </div>
              ))}
            </div>
            <h3 style={{marginBottom:"12px"}}>Explore the hub</h3>
            <div style={{display:"flex",gap:"10px",flexWrap:"wrap"}}>
              <button onClick={()=>setHubTab("create")} style={{display:"flex",alignItems:"center",gap:"7px"}}><BookOpen size={15}/>Build Your Character</button>
              <button className="ghost" onClick={()=>setHubTab("classes")} style={{display:"flex",alignItems:"center",gap:"7px"}}><Map size={15}/>Class Guides</button>
              <button className="ghost" onClick={()=>setHubTab("world")} style={{display:"flex",alignItems:"center",gap:"7px"}}><Globe size={15}/>Explore the World</button>
              <button className="ghost" onClick={()=>setHubTab("skills")} style={{display:"flex",alignItems:"center",gap:"7px"}}><Sparkles size={15}/>Browse Skills</button>
              <button className="ghost" onClick={()=>setHubTab("guide")} style={{display:"flex",alignItems:"center",gap:"7px"}}><Scroll size={15}/>Server Guide</button>
            </div>
          </div>
        )}

        {/* CHARACTER CREATION */}
        {hubTab==="create"&&(
          <div style={{maxWidth:"900px"}}>
            <div style={{display:"flex",gap:"0",marginBottom:"28px",overflowX:"auto"}}>
              {CREATION_STEPS.map(s=>{
                const done=build.step>s.id;const cur=build.step===s.id;
                return(
                  <div key={s.id} onClick={()=>updateStep(s.id)} style={{flex:"1",minWidth:"90px",padding:"10px 8px",textAlign:"center",
                    borderBottom:`3px solid ${cur?"#2f6f73":done?"#4caf7d":"#e0d4c4"}`,
                    cursor:"pointer",opacity:build.step<s.id?0.5:1,transition:"all 0.15s"}}>
                    <div style={{fontSize:"11px",fontWeight:700,fontFamily:"monospace",marginBottom:"2px",color:cur?"#2f6f73":done?"#4caf7d":"#aaa"}}>{done?"✓":`0${s.id}`}</div>
                    <div style={{fontSize:"12px",fontWeight:600,color:cur?"#2c241e":"#777"}}>{s.title}</div>
                    <div style={{fontSize:"10px",color:"#aaa"}}>{s.subtitle}</div>
                  </div>
                );
              })}
            </div>
            {build.step===1&&(
              <div>
                <h3 style={{marginBottom:"6px"}}>Where did your character come from?</h3>
                <p className="muted-text" style={{fontSize:"13px",marginBottom:"18px"}}>Your origin shapes your free Origin Trait (doesn't count toward your 5pt budget).</p>
                <div style={{display:"grid",gridTemplateColumns:"repeat(auto-fill, minmax(250px,1fr))",gap:"10px",marginBottom:"20px"}}>
                  {CITIES.map(c=>(
                    <div key={c.id} onClick={()=>setBuild(p=>({...p,city:c.id}))} style={pill(build.city===c.id)}>
                      <div style={{display:"flex",alignItems:"center",gap:"8px",marginBottom:"5px"}}>
                        <strong style={{fontSize:"14px",flex:1}}>{c.name}</strong>
                        {build.city===c.id&&<Check size={13} color="#2f6f73"/>}
                        <span className="activity-type-label" style={{fontSize:"9px"}}>{c.tag}</span>
                      </div>
                      <p className="muted-text" style={{fontSize:"12px",lineHeight:"1.5"}}>{c.desc}</p>
                    </div>
                  ))}
                </div>
                <div style={{display:"flex",justifyContent:"flex-end"}}>
                  <button onClick={()=>updateStep(2)} disabled={!build.city} style={{display:"flex",alignItems:"center",gap:"6px"}}>Next: Your Class<ChevronRight size={15}/></button>
                </div>
              </div>
            )}
            {build.step===2&&(
              <div>
                <h3 style={{marginBottom:"6px"}}>What does your character do?</h3>
                <p className="muted-text" style={{fontSize:"13px",marginBottom:"18px"}}>
                  Class traits are <strong>mutually exclusive</strong>. No class trait = All-Rounder, freeing 3pts for Keystone traits.
                  <button className="ghost" onClick={()=>setHubTab("classes")} style={{marginLeft:"10px",fontSize:"12px",padding:"3px 10px"}}>Full class guides →</button>
                </p>
                <div style={{display:"grid",gridTemplateColumns:"repeat(auto-fill, minmax(250px,1fr))",gap:"10px",marginBottom:"20px"}}>
                  {CLASSES_QUICK.map(cls=>{
                    const Icon=cls.icon;const active=build.classChoice===cls.id;
                    return(
                      <div key={cls.id} onClick={()=>setBuild(p=>({...p,classChoice:cls.id,selectedTraits:[]}))} style={pill(active)}>
                        <div style={{display:"flex",alignItems:"center",gap:"8px",marginBottom:"5px"}}>
                          <Icon size={15} color={active?"#2f6f73":"#888"}/><strong style={{fontSize:"13px",flex:1}}>{cls.name}</strong>
                          {active&&<Check size={13} color="#2f6f73"/>}
                          <span className="activity-type-label" style={{fontSize:"9px"}}>{cls.cost>0?`${cls.cost}pt`:"Free"}</span>
                        </div>
                        <p style={{fontSize:"10px",color:"#999",fontStyle:"italic",marginBottom:"5px"}}>{cls.trait}</p>
                        <p className="muted-text" style={{fontSize:"12px",lineHeight:"1.5",marginBottom:"5px"}}>{cls.desc}</p>
                        <p style={{fontSize:"11px",color:"#2f6f73"}}><strong>Best for:</strong> {cls.bestFor}</p>
                      </div>
                    );
                  })}
                </div>
                <BackNext onBack={()=>updateStep(1)} onNext={()=>updateStep(3)} nextDisabled={!build.classChoice}/>
              </div>
            )}
            {build.step===3&&(
              <div>
                <div style={{display:"flex",alignItems:"center",gap:"14px",marginBottom:"6px",flexWrap:"wrap"}}>
                  <h3>Choose your traits</h3>
                  <span style={{fontFamily:"monospace",fontSize:"13px",fontWeight:700,color:traitPtsUsed>5?"#e05555":traitPtsUsed===5?"#4caf7d":"#2f6f73",background:traitPtsUsed>5?"#e0555520":"#2f6f7315",padding:"4px 12px",borderRadius:"6px"}}>{traitPtsUsed} / 5 pts used</span>
                </div>
                <p className="muted-text" style={{fontSize:"13px",marginBottom:"18px"}}>You have <strong>5 trait points</strong> + 1 free Origin Trait. Negative Traits can extend this to 8 pts.</p>
                {TRAIT_TIERS.map(tier=>(
                  <div key={tier.label} className="card" style={{marginBottom:"14px",padding:"16px"}}>
                    <strong style={{fontSize:"13px",display:"block",marginBottom:"3px"}}>{tier.label}</strong>
                    <p className="muted-text" style={{fontSize:"11px",marginBottom:"12px"}}>{tier.note}</p>
                    <div style={{display:"grid",gridTemplateColumns:"repeat(auto-fill, minmax(200px,1fr))",gap:"8px"}}>
                      {tier.traits.map(trait=>{
                        const sel=build.selectedTraits.includes(trait.name);
                        const cant=!sel&&traitPtsUsed+trait.cost>5;
                        return(
                          <div key={trait.name} onClick={()=>!cant&&toggleTrait(trait.name,trait.cost)} style={{padding:"10px 12px",borderRadius:"6px",border:`1px solid ${sel?"#2f6f73":"#e0d4c4"}`,background:sel?"#2f6f7310":cant?"#faf7f3":"white",cursor:cant?"not-allowed":"pointer",opacity:cant?0.5:1,transition:"all 0.12s"}}>
                            <div style={{display:"flex",alignItems:"center",gap:"6px",marginBottom:"4px"}}>
                              <strong style={{fontSize:"13px",flex:1}}>{trait.name}</strong>
                              <span style={{fontFamily:"monospace",fontSize:"10px",fontWeight:700,color:sel?"#2f6f73":"#aaa"}}>{trait.cost}pt</span>
                              {sel&&<Check size={12} color="#2f6f73"/>}
                            </div>
                            <p style={{fontSize:"11px",color:"#666",lineHeight:"1.4"}}>{trait.desc}</p>
                          </div>
                        );
                      })}
                    </div>
                  </div>
                ))}
                <BackNext onBack={()=>updateStep(2)} onNext={()=>updateStep(4)}/>
              </div>
            )}
            {build.step===4&&(
              <div>
                <div style={{display:"flex",alignItems:"center",gap:"14px",flexWrap:"wrap",marginBottom:"6px"}}><h3>Set your starting stats</h3><XPBadge/></div>
                <p className="muted-text" style={{fontSize:"13px",marginBottom:"18px"}}>All 5 stats start at <strong>10 for free</strong>. 600 XP splits across stat raises AND skill purchases.</p>
                <XPBar/>
                <div className="card" style={{padding:"20px",marginBottom:"16px"}}>
                  {STAT_KEYS.map(key=>{
                    const val=build.stats[key]??10;const xp=calcStatXP(10,val);
                    return(
                      <div key={key} style={{marginBottom:"18px"}}>
                        <div style={{display:"flex",justifyContent:"space-between",marginBottom:"5px"}}>
                          <span style={{fontSize:"14px",fontWeight:600}}>{STAT_LABELS[key]}</span>
                          <span style={{fontSize:"13px"}}><strong>{val}</strong><span className="muted-text" style={{marginLeft:"8px"}}>{xp>0?`+${xp} XP`:"free"}</span></span>
                        </div>
                        <input type="range" min={10} max={200} value={val} onChange={e=>setBuild(p=>({...p,stats:{...p.stats,[key]:Number(e.target.value)}}))} style={{width:"100%",accentColor:"#2f6f73"}}/>
                        <div style={{display:"flex",justifyContent:"space-between",fontSize:"10px",color:"#ccc",marginTop:"2px"}}><span>10 free</span><span>50 (1xp)</span><span>150 (2xp)</span><span>200 (4xp)</span></div>
                      </div>
                    );
                  })}
                </div>
                <BackNext onBack={()=>updateStep(3)} onNext={()=>updateStep(5)} nextLabel="Next: Skills"/>
              </div>
            )}
            {build.step===5&&(
              <div>
                <div style={{display:"flex",alignItems:"center",gap:"14px",flexWrap:"wrap",marginBottom:"6px"}}><h3>Choose starting skills</h3><XPBadge/></div>
                <p className="muted-text" style={{fontSize:"13px",marginBottom:"18px"}}>Common first purchases. Full list in the Skills tab.</p>
                <XPBar/>
                {Array.from(new Set(STARTING_SKILLS.map(s=>s.tree))).map(tree=>(
                  <div key={tree} style={{marginBottom:"16px"}}>
                    <div style={{fontSize:"11px",fontWeight:700,letterSpacing:"2px",color:"#888",marginBottom:"8px",textTransform:"uppercase"}}>{tree}</div>
                    <div style={{display:"grid",gridTemplateColumns:"repeat(auto-fill, minmax(210px,1fr))",gap:"8px"}}>
                      {STARTING_SKILLS.filter(s=>s.tree===tree).map(skill=>{
                        const sel=build.selectedSkills.includes(skill.key);const cant=!sel&&xpLeft<skill.cost;
                        return(
                          <div key={skill.key} onClick={()=>!cant&&toggleSkill(skill.key,skill.cost)} style={{padding:"10px 12px",borderRadius:"6px",border:`1px solid ${sel?"#2f6f73":"#e0d4c4"}`,background:sel?"#2f6f7310":cant?"#faf7f3":"white",cursor:cant?"not-allowed":"pointer",opacity:cant?0.5:1,transition:"all 0.12s"}}>
                            <div style={{display:"flex",alignItems:"center",gap:"6px",marginBottom:"4px"}}>
                              <strong style={{fontSize:"13px",flex:1}}>{skill.name}</strong>
                              <span style={{fontFamily:"monospace",fontSize:"10px",fontWeight:700,color:sel?"#2f6f73":"#aaa"}}>{skill.cost} XP</span>
                              {sel&&<Check size={12} color="#2f6f73"/>}
                            </div>
                            <p style={{fontSize:"11px",color:"#666",lineHeight:"1.4"}}>{skill.desc}</p>
                          </div>
                        );
                      })}
                    </div>
                  </div>
                ))}
                <BackNext onBack={()=>updateStep(4)} onNext={()=>updateStep(6)} nextLabel="Review Build"/>
              </div>
            )}
            {build.step===6&&(
              <div>
                <h3 style={{marginBottom:"4px"}}>Your Starting Build</h3>
                <p className="muted-text" style={{fontSize:"13px",marginBottom:"20px"}}>Use this as a reference when filling out your OC sheet.</p>
                {xpLeft<0&&(<div style={{background:"#e0555510",border:"1px solid #e05555",borderRadius:"6px",padding:"12px 16px",marginBottom:"16px",display:"flex",gap:"8px"}}><AlertTriangle size={15} color="#e05555" style={{flexShrink:0,marginTop:"2px"}}/><p style={{fontSize:"13px",color:"#c03333"}}>You're <strong>{Math.abs(xpLeft)} XP over budget</strong>. Go back and reduce stats or remove skills.</p></div>)}
                <div style={{display:"grid",gridTemplateColumns:"1fr 1fr",gap:"14px",marginBottom:"14px"}}>
                  <div className="card" style={{padding:"16px"}}>
                    <div className="card-title-row" style={{marginBottom:"10px"}}><strong>Background & Class</strong></div>
                    <p style={{fontSize:"13px",marginBottom:"6px"}}><span className="muted-text">Origin: </span><strong>{CITIES.find(c=>c.id===build.city)?.name||"—"}</strong></p>
                    <p style={{fontSize:"13px"}}><span className="muted-text">Class: </span><strong>{CLASSES_QUICK.find(c=>c.id===build.classChoice)?.name||"—"}</strong></p>
                  </div>
                  <div className="card" style={{padding:"16px"}}>
                    <div className="card-title-row" style={{marginBottom:"10px"}}><strong>XP Budget</strong><span className="activity-type-label">600 XP</span></div>
                    <div style={{height:"6px",background:"#e0d4c4",borderRadius:"3px",marginBottom:"8px",overflow:"hidden"}}><div style={{height:"100%",width:`${xpPct}%`,background:xpLeft<0?"#e05555":"#2f6f73",borderRadius:"3px"}}/></div>
                    <div style={{display:"flex",justifyContent:"space-between",fontSize:"13px"}}><span className="muted-text">Spent: <strong>{xpSpent} XP</strong></span><span style={{color:xpColor,fontWeight:700}}>{xpLeft>=0?`${xpLeft} remaining`:`${Math.abs(xpLeft)} over`}</span></div>
                  </div>
                </div>
                <div className="card" style={{padding:"16px",marginBottom:"14px"}}>
                  <div className="card-title-row" style={{marginBottom:"10px"}}><strong>Traits</strong><span className="activity-type-label">{traitPtsUsed} / 5 pts</span></div>
                  {build.selectedTraits.length===0?<p className="muted-text" style={{fontSize:"13px"}}>No traits selected.</p>:<div style={{display:"flex",gap:"6px",flexWrap:"wrap"}}>{build.selectedTraits.map(t=>{let c=0;for(const tier of TRAIT_TIERS){const f=tier.traits.find(x=>x.name===t);if(f){c=f.cost;break;}}return <span key={t} style={{fontSize:"12px",background:"#2f6f7315",color:"#2f6f73",padding:"4px 10px",borderRadius:"20px",border:"1px solid #2f6f7340"}}>{t} ({c}pt)</span>;})}</div>}
                </div>
                <div className="card" style={{padding:"16px",marginBottom:"14px"}}>
                  <div className="card-title-row" style={{marginBottom:"10px"}}><strong>Starting Stats</strong><span className="activity-type-label">{statXP} XP</span></div>
                  <div style={{display:"grid",gridTemplateColumns:"repeat(5,1fr)",gap:"8px"}}>
                    {STAT_KEYS.map(key=>{const val=build.stats[key]??10;const xp=calcStatXP(10,val);return(<div key={key} style={{textAlign:"center",padding:"10px 6px",background:"#f6efe4",borderRadius:"6px"}}><div style={{fontSize:"20px",fontWeight:800,color:"#2f6f73",lineHeight:1}}>{val}</div><div style={{fontSize:"10px",color:"#888",marginTop:"3px"}}>{STAT_LABELS[key].replace(" ","").toUpperCase()}</div>{xp>0&&<div style={{fontSize:"10px",color:"#2f6f73",marginTop:"2px"}}>+{xp}xp</div>}</div>);})}
                  </div>
                </div>
                <div className="card" style={{padding:"16px",marginBottom:"20px"}}>
                  <div className="card-title-row" style={{marginBottom:"10px"}}><strong>Starting Skills</strong><span className="activity-type-label">{skillXP} XP</span></div>
                  {build.selectedSkills.length===0?<p className="muted-text" style={{fontSize:"13px"}}>No skills selected.</p>:<div style={{display:"flex",flexDirection:"column",gap:"6px"}}>{build.selectedSkills.map(key=>{const s=STARTING_SKILLS.find(x=>x.key===key);return s?(<div key={key} style={{display:"flex",alignItems:"center",gap:"8px",fontSize:"13px"}}><Check size={12} color="#4caf7d"/><strong>{s.name}</strong><span className="muted-text" style={{fontSize:"12px"}}>({s.tree})</span><span style={{marginLeft:"auto",fontFamily:"monospace",fontSize:"12px",color:"#888"}}>{s.cost} XP</span></div>):null;})}</div>}
                </div>
                <div style={{display:"flex",gap:"10px",justifyContent:"space-between"}}>
                  <button className="ghost" onClick={()=>updateStep(5)} style={{display:"flex",alignItems:"center",gap:"6px"}}><ChevronLeft size={15}/>Back</button>
                  <div style={{display:"flex",gap:"10px"}}>
                    <button className="ghost" onClick={()=>setBuild({city:"",classChoice:"",selectedTraits:[],stats:{strength:10,dexterity:10,stamina:10,magic_affinity:10,mana:10},selectedSkills:[],step:1})}>Start Over</button>
                    {jump&&<button onClick={()=>jump("register")} style={{display:"flex",alignItems:"center",gap:"6px"}}>Register OC<ChevronRight size={15}/></button>}
                  </div>
                </div>
              </div>
            )}
          </div>
        )}

        {/* CLASS GUIDES OVERVIEW */}
        {hubTab==="classes"&&(
          <div style={{maxWidth:"900px"}}>
            <div className="card" style={{marginBottom:"20px",borderLeft:"4px solid #2f6f73",padding:"16px"}}>
              <h3 style={{marginBottom:"6px"}}>Class Guides</h3>
              <p className="muted-text" style={{fontSize:"13px"}}>Full guides for every class — skill chains, stat priorities, sample 600 XP builds. Click any class to open its guide.</p>
            </div>
            <div style={{display:"grid",gridTemplateColumns:"repeat(auto-fill, minmax(260px,1fr))",gap:"12px"}}>
              {CLASS_GUIDES.map(g=>(
                <div key={g.id} onClick={()=>setSelectedClass(g.id)} className="card"
                  style={{padding:0,overflow:"hidden",cursor:"pointer",transition:"all 0.18s",borderLeft:`4px solid ${g.tagColor}`}}>
                  <div style={{padding:"16px 18px 12px",borderBottom:"1px solid #e0d4c4"}}>
                    <div style={{display:"flex",alignItems:"center",gap:"10px",marginBottom:"6px"}}>
                      <span style={{fontSize:"24px"}}>{g.emoji}</span>
                      <div style={{flex:1}}>
                        <strong style={{fontSize:"15px",display:"block"}}>{g.name}</strong>
                        <span style={{fontFamily:"monospace",fontSize:"10px",color:g.tagColor,letterSpacing:"1px"}}>{g.difficulty.toUpperCase()}</span>
                      </div>
                      <ChevronRight size={16} color="#ccc"/>
                    </div>
                    <p className="muted-text" style={{fontSize:"12px",lineHeight:"1.5"}}>{g.desc.length>100?g.desc.slice(0,100)+"…":g.desc}</p>
                  </div>
                  <div style={{padding:"10px 18px",display:"flex",justifyContent:"space-between",alignItems:"center",background:"#faf7f3"}}>
                    <span style={{fontSize:"11px",color:"#888"}}>{g.role}</span>
                    <span style={{fontSize:"11px",background:`${g.tagColor}15`,color:g.tagColor,padding:"2px 8px",borderRadius:"10px",fontWeight:600,border:`1px solid ${g.tagColor}30`}}>
                      {g.tag.includes("No trait")||g.tag.includes("Universal")?"Free":g.tag.includes("3pt")?"3pt":"2pt"}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* SKILLS */}
        {hubTab==="skills"&&(
          <div style={{maxWidth:"860px"}}>
            <div className="card" style={{marginBottom:"16px",borderLeft:"4px solid #2f6f73",padding:"16px"}}>
              <h3 style={{marginBottom:"6px"}}>Skill Reference</h3>
              <p className="muted-text" style={{fontSize:"13px",marginBottom:"12px"}}>Skill chains for every tree. Full interactive browser available in the main Skills tab.</p>
              {jump&&<button onClick={()=>jump("skills")} style={{display:"flex",alignItems:"center",gap:"7px",fontSize:"13px"}}><Sparkles size={15}/>Open Full Skills Dashboard</button>}
            </div>
            {[
              {tree:"Mercenary",color:"#2f6f73",chains:["Pilfer → Stealth → Misdirection","Adept → Operative → Veteran","Pacing (standalone) | Quartermastery (standalone)"]},
              {tree:"Martial — Heavy",color:"#8b4513",chains:["Heavy Armaments → Taunt → Dominion","Heavy Armaments → Berserker → Sweeping Strike","Heavy Armaments → Honed Strike → Mastered Strike"]},
              {tree:"Martial — Light",color:"#8b6914",chains:["Light Armaments → Crowd Feint → Swashbuckler","Light Armaments → Unbound → Disarm","Light Armaments → Duelist → Parry"]},
              {tree:"Martial Arts",color:"#6b4c8b",chains:["Martial Arts → Offensive Defense → Furious Technique","Martial Arts → Trance → Disarm","Martial Arts → Brawler → Grappler → Form Mastery"]},
              {tree:"Magecraft",color:"#3b7dbf",chains:["Force T0 → T1 → T2 → T3 (Water/Earth/Wind/Fire)","Restoration → Advanced → Mastered | +Purification","Abjuration → Wards/Barriers → Reflection","Destruction → Offensive Area Magic","Mana Skin → Reflexive Mana Skin | Overcharge → Mastered","Regeneration → Focused Regeneration | Enchantment (T3)"]},
              {tree:"Forgecraft",color:"#b8721a",chains:["Utility Beginner → Practitioner → Expert ← REQUIRED FIRST","Smithing Rookie → Novice → Extraordinaire","Snare Trainee → Apprentice → Master","Demo Learner → Trainee → Specialist","Chemical Assistant → Analyst → Scientist"]},
              {tree:"Guncraft",color:"#8b3030",chains:["Wheelgun → Quickdraw → Virtuoso","Rifle Training → Sharpshooter → Deadeye","Scattergun → Close-Quarters → Breacher","Good Eyes + Alert → Eagle Eye","Lesser Reload → Veteran Reload"]},
              {tree:"Beastmaster",color:"#3d7a3d",chains:["Obedience → Proficient Command → Advanced Command","Shared Experience → Shared Experience II","Remote Sense → Spectral Bond"]},
              {tree:"Field Medic",color:"#2d7a7a",chains:["Basic Medkits → Advanced Medkits → Surgery","Prepared Medic I → II → III","Compound Medicine (req Advanced Medkits)","Stabilization (standalone)"]},
              {tree:"Tactician",color:"#555",chains:["Tactical Orders I → II → III","Target Tracking → Battlefield Awareness"]},
              {tree:"Smuggler",color:"#7a3d7a",chains:["Light Load → Hidden Compartments","Concealment → Mass Concealment","Safer Routes → Ghost Run","Black Market Access (T2 standalone)"]},
              {tree:"Politician",color:"#3d557a",chains:["Silver Tongue → Master Negotiator","Reputation Management → Political Network","Passive Income → Investment Making","Contractional Servitude (req Silver Tongue + Reputation Mgmt)"]},
              {tree:"Knowledge",color:"#888",chains:["Linguistics → Print Forgery | Codebreaking","Geology → Metallurgy","Biology → Veterinary Study","Doranswyr Historian → Martial Historian","Catechumen → Luminary"]},
            ].map(s=>(
              <div key={s.tree} className="card" style={{marginBottom:"10px",padding:"14px 16px"}}>
                <div style={{display:"flex",alignItems:"center",gap:"8px",marginBottom:"10px"}}>
                  <div style={{width:"8px",height:"8px",borderRadius:"50%",background:s.color}}/><strong style={{fontSize:"14px"}}>{s.tree}</strong>
                </div>
                {s.chains.map((c,i)=><p key={i} style={{fontSize:"12px",color:"#555",fontFamily:"monospace",lineHeight:"1.7"}}>{c}</p>)}
              </div>
            ))}
          </div>
        )}

        {/* WORLD */}
        {hubTab==="world"&&(
          <div style={{maxWidth:"860px"}}>
            <div className="card" style={{marginBottom:"20px",borderLeft:"4px solid #2f6f73",padding:"16px"}}>
              <h3 style={{marginBottom:"8px"}}>The World of Doranswyr</h3>
              <p style={{fontSize:"14px",color:"#555",lineHeight:"1.7"}}>Doranswyr is a massive continent (~3,000 miles east to west) set in its early industrial era. The Republic collapsed 30 years ago. The current year is <strong>1845</strong>. Ten city-states scramble for power and survival — the only efficient travel between them is by railroad.</p>
            </div>
            <h3 style={{marginBottom:"12px"}}>City-States</h3>
            <div style={{display:"grid",gridTemplateColumns:"repeat(auto-fill, minmax(250px,1fr))",gap:"10px",marginBottom:"24px"}}>
              {CITIES.filter(c=>c.id!=="outlands").map(c=>(<div key={c.id} className="card" style={{padding:"14px 16px"}}><div style={{display:"flex",alignItems:"center",gap:"8px",marginBottom:"6px"}}><strong style={{fontSize:"14px",flex:1}}>{c.name}</strong><span className="activity-type-label" style={{fontSize:"9px"}}>{c.tag}</span></div><p className="muted-text" style={{fontSize:"12px",lineHeight:"1.5"}}>{c.desc}</p></div>))}
            </div>
            <h3 style={{marginBottom:"12px"}}>The Four Mercenary Guilds</h3>
            <div style={{display:"grid",gridTemplateColumns:"repeat(auto-fill, minmax(200px,1fr))",gap:"10px",marginBottom:"24px"}}>
              {[{name:"Gilded Index",desc:"Knowledge, magic, and structured power.",role:"Scholar / Arcanist / Battlemage"},{name:"Black Spur",desc:"Hunters, assassins, and trackers.",role:"Hunter / Assassin / Tracker"},{name:"Iron Covenant",desc:"Protection, escort, and defense.",role:"Guard / Escort / Defender"},{name:"Ragged Signal",desc:"Influence, information, and control.",role:"Spy / Smuggler / Manipulator"}].map(g=>(<div key={g.name} className="card" style={{padding:"14px 16px"}}><strong style={{fontSize:"13px",display:"block",marginBottom:"6px"}}>{g.name}</strong><p className="muted-text" style={{fontSize:"12px",lineHeight:"1.5",marginBottom:"6px"}}>{g.desc}</p><p style={{fontSize:"11px",color:"#2f6f73"}}>{g.role}</p></div>))}
            </div>
            <h3 style={{marginBottom:"12px"}}>Magic & Source</h3>
            <div className="card" style={{padding:"16px"}}>
              <p style={{fontSize:"13px",color:"#555",lineHeight:"1.7",marginBottom:"10px"}}>Magic is drawn from <strong>Source</strong> — an ever-present primordial energy. Most people have dormant mana circuits but can't use them. Only three places formally teach it: Lumenhold Academy, the Imperial College in the Citadel, and Brassmere's independent labs.</p>
              <p style={{fontSize:"13px",color:"#555",lineHeight:"1.7"}}><strong>Bondroot Trees</strong> in Source Wells can bond with pre-pubescent humans, severing their Source connection but granting them a living Source Beast companion for life. These people become <strong>Beasthandlers</strong>.</p>
            </div>
          </div>
        )}

        {/* SERVER GUIDE */}
        {hubTab==="guide"&&(
          <div style={{maxWidth:"860px"}}>
            {[
              {title:"How XP Works",color:"#2f6f73",items:[{label:"Earning XP",desc:"XP comes from RP scenes, missions, and events. Submit posts via the RP Hub tab to claim XP. Staff reviews and approves."},{label:"Spending XP",desc:"XP is spent on stat raises and skill purchases. Use the XP Planner tab to plan. Submit via Skills tab or through tickets."},{label:"Starting XP",desc:"New OCs start with 600 XP. All 5 stats start at 10 for FREE — only points above 10 cost XP."},{label:"Beast XP",desc:"Source Beasts have a separate XP pool. They earn a % of your XP through the Shared Experience OC skill (900 XP)."}]},
              {title:"How Missions Work",color:"#8b4513",items:[{label:"Finding Missions",desc:"Check the Mission Board tab in Keystone. Missions list difficulty, party size, BST requirements, and rewards."},{label:"BST",desc:"Base Stat Total — the sum of all your core stats. Used to match you to appropriate missions."},{label:"Signing Up",desc:"Sign up via Keystone. Some missions have a priority window for specific guilds before opening to all."},{label:"Rewards",desc:"Missions pay out currency and XP. Staff posts results after the mission concludes."}]},
              {title:"Combat Basics",color:"#6b4c8b",items:[{label:"Action Economy",desc:"Each character has Actions, Reactions, Bonus Actions, and Free Actions per turn. Skills like Adept add more."},{label:"Injury Tiers",desc:"T1 (minor) → T5 (critical/life-threatening). Source Beasts have half OC injury capacity."},{label:"Clashing",desc:"Direct combat exchanges. Your output is compared to your opponent's reaction to determine damage."},{label:"Combat Calculator",desc:"Use the Combat Calculator tab in Keystone to calculate derived stats and track fights."}]},
              {title:"How to Submit Things",color:"#3d7a3d",items:[{label:"New OC",desc:"Fill out the OC Draft Template → link in #oc-submissions → open a ticket. Staff approves before you can RP."},{label:"Skill Purchases",desc:"Skills tab in Keystone → find skill → click Purchase. Staff approves and XP is deducted automatically."},{label:"Stat Increases",desc:"XP Planner tab → set target stats → submit. Staff approves and XP is deducted."},{label:"Spells (Mages)",desc:"Design spell using the Spell Template → submit via ticket → wait for approval. You CANNOT cast until approved."},{label:"Beast Skills",desc:"Currently LOCKED pending a balance pass. Plan your path but hold the XP until they release."}]},
              {title:"Key Channels & Resources",color:"#b8721a",items:[{label:"#rules",desc:"Read before doing anything else."},{label:"#mentor",desc:"Ask staff or veteran players for help. No question is too basic."},{label:"#oc-submissions",desc:"Submit your OC sheet for staff approval."},{label:"#spell-submissions",desc:"Submit new spells for approval. Required before use."},{label:"Keystone (this site)",desc:"OC dashboard, XP planner, inventory, skills, shops, combat calculator, missions — all here."}]},
            ].map(section=>(
              <div key={section.title} className="card" style={{marginBottom:"14px",padding:0,overflow:"hidden"}}>
                <div style={{padding:"13px 16px",borderBottom:"1px solid #e0d4c4",borderLeft:`4px solid ${section.color}`}}><strong style={{fontSize:"15px"}}>{section.title}</strong></div>
                <div style={{padding:"14px 16px"}}>
                  {section.items.map(item=>(<div key={item.label} style={{display:"flex",gap:"12px",fontSize:"13px",marginBottom:"10px"}}><strong style={{flexShrink:0,width:"155px",color:"#2c241e"}}>{item.label}</strong><span style={{color:"#555",lineHeight:"1.55"}}>{item.desc}</span></div>))}
                </div>
              </div>
            ))}
          </div>
        )}

      </div>
    </section>
  );
}
