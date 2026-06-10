// GettingStartedDashboard.tsx
// Place at: frontend/src/components/GettingStartedDashboard.tsx
//
// WIRING (main.tsx):
//   1. import GettingStartedDashboard from "./components/GettingStartedDashboard";
//   2. Add "getting_started" to Tab type
//   3. Add ["getting_started", BookOpen, "Getting Started"] to tabs array
//   4. Add {tab === "getting_started" && <GettingStartedDashboard discordId={discordId} jump={setTab} />}
//
// WIRING (permissions.py):
//   Add "getting_started" to PLAYER_TABS (at the top)

import React, { useState } from "react";
import {
  BookOpen, Sparkles, Globe, Scroll, Home,
  ChevronRight, ChevronLeft, Check, AlertTriangle,
  Star, Shield, Swords, Zap, Wrench, Target, PawPrint, Users
} from "lucide-react";

// ── TYPES ─────────────────────────────────────────────────────────────────────

type HubTab = "start" | "create" | "skills" | "world" | "guide";

interface BuildState {
  city: string;
  classChoice: string;
  selectedTraits: string[];
  stats: Record<string, number>;
  selectedSkills: string[];
  step: number;
}

// ── XP / STAT HELPERS ────────────────────────────────────────────────────────

const XP_BANDS = [
  { min: 0,   max: 50,  cost: 1 },
  { min: 51,  max: 150, cost: 2 },
  { min: 151, max: 250, cost: 4 },
  { min: 251, max: 350, cost: 6 },
  { min: 351, max: 450, cost: 8 },
  { min: 451, max: 550, cost: 10 },
  { min: 551, max: 650, cost: 12 },
  { min: 651, max: 750, cost: 14 },
];

const STAT_KEYS = ["strength","dexterity","stamina","magic_affinity","mana"];
const STAT_LABELS: Record<string,string> = {
  strength:"Strength", dexterity:"Dexterity", stamina:"Stamina",
  magic_affinity:"Mag. Affinity", mana:"Mana"
};

function calcStatXP(from: number, to: number): number {
  let total = 0;
  for (let i = from + 1; i <= to; i++) {
    const band = XP_BANDS.find(b => i >= b.min && i <= b.max);
    total += band ? band.cost : 14;
  }
  return total;
}

function totalStatXP(stats: Record<string,number>): number {
  return STAT_KEYS.reduce((s,k) => s + calcStatXP(10, stats[k] ?? 10), 0);
}

function totalSkillXP(skills: string[], skillList: typeof STARTING_SKILLS): number {
  return skills.reduce((s, key) => {
    const sk = skillList.find(x => x.key === key);
    return s + (sk?.cost || 0);
  }, 0);
}

// ── DATA ──────────────────────────────────────────────────────────────────────

const CITIES = [
  { id:"lumenhold",  name:"Lumenhold",   tag:"Academy City",      desc:"Deep in the Red Desert. A city of scholars and Source researchers run by the Illuminated Conclave. Intellectual, intense, opinion-heavy." },
  { id:"gearford",   name:"Gearford",    tag:"Industrial Hub",    desc:"Built from labor. If you can build, fix, or improve something, you have a place. Merchant Council-controlled meritocracy." },
  { id:"flywheel",   name:"Flywheel",    tag:"Hydro City",        desc:"Most technologically advanced city-state, built on the Grand Wheel hydroelectric dam. Governed by the technocratic Directorate of Flow." },
  { id:"ashgate",    name:"Ashgate",     tag:"Trade Crossroads",  desc:"Where ancient trade routes converge. Wealth and information flow as freely as coin. The Vaelor dynasty rules — and shadows run deep." },
  { id:"thornwick",  name:"Thornwick",   tag:"Frontier City",     desc:"Built at the edge of the Blackwood Frontier. Hunters, trackers, wardens. Survival depends on cooperation, discipline, and strength." },
  { id:"cinder",     name:"Cinder",      tag:"Forge City",        desc:"Rebuilt from ash after the Burning of Cinderfell. Welcoming, hardworking city of smiths led by the beloved King Faren Zamor." },
  { id:"high_sable", name:"High Sable",  tag:"Cliff Fortress",    desc:"Carved into a sheer cliff face. Life revolves around vigilance and preparedness. Every citizen contributes to defense." },
  { id:"brassmere",  name:"Brassmere",   tag:"Industrial Port",   desc:"Gleams from afar, darker up close. Magic and machinery blur together here. The Experimental Bureau keeps dangerous secrets." },
  { id:"morthand",   name:"Morthand",    tag:"Theocracy",         desc:"Ruled by the masked Holy Tribunal. Peaceful, orderly, and deeply isolationist. Entry by permit only. The Covenant of the Veiled God controls all." },
  { id:"citadel",    name:"The Citadel", tag:"Imperial Seat",     desc:"Once a capital, always a capital. Imperator Vegard Ragon rules. The middle class thrives. The Imperial College is open to all." },
  { id:"outlands",   name:"The Outlands",tag:"No City-State",     desc:"Born beyond the city-states — a settlement, a caravan, or the wilderness. More freedom, less protection. Common for wanderers and mercenaries." },
];

const CLASSES = [
  { id:"none",       name:"All-Rounder",     trait:"No class trait",               cost:0, icon:Star,     desc:"Generalist with free trait points. Access to Keystone traits unavailable to class builds.",          bestFor:"Versatility, XP grinders, Keystone traits" },
  { id:"mana",       name:"Magecraft",        trait:"Mana Circuits (3pt)",          cost:3, icon:Zap,      desc:"Source-based magic through Forces and Schools. Spell approval required before use. Highest ceiling.", bestFor:"Magic offense, healing, support spells" },
  { id:"forgeborn",  name:"Forgecraft",       trait:"Forgeborn (3pt)",              cost:3, icon:Wrench,   desc:"Five crafting paths: Utility, Smithing, Snares, Demolition, Chemistry. Supply your whole team.",      bestFor:"Crafting, team support, traps, engineering" },
  { id:"gunslinger", name:"Guncraft",         trait:"Gunslinger Training (3pt)",    cost:3, icon:Target,   desc:"Multiple gun type tracks — not mutually exclusive. DEX-based ranged combat with momentum.",           bestFor:"Ranged combat, DEX builds, gun specialists" },
  { id:"companion",  name:"Beastmaster",      trait:"Loyal Companion (3pt)",        cost:3, icon:PawPrint, desc:"Two-character build: you + a Source Beast. Severs your Source access. Unique long-term growth arc.",   bestFor:"Unique RP, two-character coordination" },
  { id:"martial_h",  name:"Martial — Heavy",  trait:"No trait needed",              cost:0, icon:Swords,   desc:"Two-handed and heavy hafted weapons. Front-line brawler. Berserker, Taunt, Dominion.",                bestFor:"Melee tanking, aggro control, burst damage" },
  { id:"martial_l",  name:"Martial — Light",  trait:"No trait needed",              cost:0, icon:Swords,   desc:"One-handed weapons, shortblades, light polearms. Speed, feinting, and Parry.",                       bestFor:"Melee skirmishing, speed, counter-attacks" },
  { id:"martial_ma", name:"Martial Arts",     trait:"No trait needed",              cost:0, icon:Swords,   desc:"Unarmed combat — must be hands-free. +4% base damage. Grapples, disarms, and Form Mastery.",         bestFor:"Grappling, disarms, unarmed specialists" },
  { id:"medic",      name:"Field Medic",      trait:"Field Medic — subclass (2pt)", cost:2, icon:Shield,   desc:"Science-based healing without mana. Medkits, stabilization, surgery, compound medicines.",           bestFor:"Team healing, support, medical RP" },
  { id:"tactician",  name:"Tactician",        trait:"Tactician — subclass (2pt)",   cost:2, icon:Users,    desc:"Battlefield control. Buff allies, track targets, read the fight in real time. Force multiplier.",     bestFor:"Leadership, team coordination, group combat" },
  { id:"smuggler",   name:"Smuggler",         trait:"Smuggler — subclass (2pt)",    cost:2, icon:Star,     desc:"Concealment, underground routes, and black market access. High DEX, low direct conflict.",            bestFor:"Stealth, infiltration, information" },
  { id:"politician", name:"Politician",       trait:"Politician — subclass (2pt)",  cost:2, icon:Users,    desc:"Social influence, negotiation, passive income, and economic power. Most RP-intensive class.",         bestFor:"Social RP, economy, long-term planning" },
];

const TRAIT_TIERS = [
  {
    label:"Class Traits — 3pts each (MUTUALLY EXCLUSIVE)",
    note:"Pick only ONE. Cannot combine with Keystone traits.",
    traits:[
      { name:"Mana Circuits",        cost:3, desc:"Unlocks Magecraft T2+. Free T0 Force + 1/4 cost at creation. Magic Tool Use free." },
      { name:"Forgeborn",            cost:3, desc:"Unlocks Forgecraft T2+. Core crafting and engineering class." },
      { name:"Gunslinger Training",  cost:3, desc:"Unlocks Guncraft T2+. Multiple gun type tracks." },
      { name:"Loyal Companion",      cost:3, desc:"Unlocks Beastmaster T2+. Grants Source Beast. Severs direct Source access." },
    ],
  },
  {
    label:"Subclass Traits — 2pts each",
    note:"Can combine with class traits. Unlock T2+ in their trees.",
    traits:[
      { name:"Field Medic", cost:2, desc:"Unlocks Field Medic T2+. Science-based healing and surgery." },
      { name:"Tactician",   cost:2, desc:"Unlocks Tactician T2+. Battlefield orders and coordination." },
      { name:"Smuggler",    cost:2, desc:"Unlocks Smuggler T2+. Concealment, routes, black market." },
      { name:"Politician",  cost:2, desc:"Unlocks Politician T2+. Influence, economy, negotiation." },
    ],
  },
  {
    label:"Keystone Traits — 3pts each (ALL-ROUNDER ONLY)",
    note:"Cannot combine with class traits (except Greater Knowledge).",
    traits:[
      { name:"Self-Made Survivor", cost:3, desc:"1.3× XP from missions. Caps your total at 5pts — no negatives." },
      { name:"Selective Fortune",  cost:3, desc:"1.15× XP for you OR one ally per mission. +1 trait point (max 6)." },
      { name:"Quiet Benefactor",   cost:3, desc:"1.2× rewards for others, not yourself. +2 trait points (max 7)." },
      { name:"Greater Knowledge",  cost:3, desc:"Once per week: ask GM for info your char wouldn't normally know. Requires Source Sensitivity negative trait." },
    ],
  },
  {
    label:"Reliable Traits — 2pts each",
    note:"Meaningful passive bonuses.",
    traits:[
      { name:"Knowledgeable",      cost:2, desc:"+3 to ALL Knowledge skill checks." },
      { name:"Natural Leader",     cost:2, desc:"Requires Charming or Threatening. +3 to ALL social skills." },
      { name:"Adrenaline Junky",   cost:2, desc:"Output boosts based on injuries currently carried." },
      { name:"Hardy Constitution", cost:2, desc:"Requires Bears Fortitude. Reduces permanent injury effects." },
    ],
  },
  {
    label:"Minor Traits — 1pt each",
    note:"Small but always-active bonuses.",
    traits:[
      { name:"Charming",         cost:1, desc:"+1 Persuasion, Charm, Negotiation. Required for Natural Leader." },
      { name:"Threatening",      cost:1, desc:"+1 Intimidation, Extortion. Required for Natural Leader. Cannot stack with Charming." },
      { name:"Sixth Sense",      cost:1, desc:"+2% Reaction Score and Dodge. Always active." },
      { name:"Light Foot",       cost:1, desc:"+1 to all stealth rolls. Always active." },
      { name:"Perceptive",       cost:1, desc:"+1 to all observation/perception checks." },
      { name:"Cat's Grace",      cost:1, desc:"+5% Dexterity (permanent)." },
      { name:"Gorilla Strength", cost:1, desc:"+5% Strength (permanent)." },
      { name:"Bears Fortitude",  cost:1, desc:"+5% Stamina (permanent)." },
      { name:"Dragon's Insight", cost:1, desc:"+5% Magic Affinity → +10% via Merlin's Skill passive." },
      { name:"Leviathan Depth",  cost:1, desc:"+5% Mana → +10% via Merlin's Skill passive." },
      { name:"Lucky Spark",      cost:1, desc:"+1 Luck. Affects GM rolls and situational modifiers." },
      { name:"Actor",            cost:1, desc:"+1 deception and lying; +2 in disguise." },
    ],
  },
];

const STARTING_SKILLS = [
  // Mercenary
  { key:"pilfer",        name:"Pilfer",             cost:50,  tree:"Mercenary",   tier:0, desc:"Sleight-of-hand, pickpocket, and plant items. Gate to Stealth chain." },
  { key:"magic_tool",    name:"Magic Tool Use",     cost:50,  tree:"Mercenary",   tier:0, desc:"Activate enchanted items. Free with Mana Circuits or Magic Background." },
  { key:"riding",        name:"Riding & Driving",   cost:50,  tree:"Mercenary",   tier:0, desc:"Ride mounts and drive harnessed vehicles." },
  { key:"stealth",       name:"Stealth",            cost:265, tree:"Mercenary",   tier:1, desc:"Hide, sneak, and set ambushes outside of combat. Requires Pilfer." },
  { key:"pacing",        name:"Pacing",             cost:750, tree:"Mercenary",   tier:2, desc:"Permanent +1 AP in all scenes. High value mid-game target." },
  // Martial
  { key:"simple_ranged", name:"Simple Ranged",      cost:50,  tree:"Martial",     tier:0, desc:"Use bows, crossbows, and slingshots. Open to all weapon tracks." },
  { key:"heavy_arms",    name:"Heavy Armaments",    cost:50,  tree:"Martial",     tier:0, desc:"+2% damage with heavy weapons. Gate to Heavy track." },
  { key:"light_arms",    name:"Light Armaments",    cost:50,  tree:"Martial",     tier:0, desc:"+2% damage with light weapons. Gate to Light track." },
  { key:"martial_arts",  name:"Martial Arts",       cost:50,  tree:"Martial",     tier:0, desc:"+4% damage unarmed. Gate to MA track. Hands must be free." },
  { key:"taunt",         name:"Taunt",              cost:265, tree:"Martial",     tier:1, desc:"Draw enemy attention. −10% reaction penalty to ally attacks for 1 turn." },
  { key:"berserker",     name:"Berserker",          cost:265, tree:"Martial",     tier:1, desc:"STR/DEX/STA ×1.10 for 3 turns. Crash: all ×0.8 after. Requires Heavy Arms." },
  // Knowledge
  { key:"linguistics",   name:"Linguistics",        cost:100, tree:"Knowledge",   tier:0, desc:"+2 language checks. Gate to Print Forgery and Codebreaking." },
  { key:"biology",       name:"Biology",            cost:100, tree:"Knowledge",   tier:0, desc:"Recognise diseases. Gate to Veterinary Study. Stacks with Field Medic." },
  { key:"history",       name:"Doranswyr Historian", cost:100,tree:"Knowledge",   tier:0, desc:"LORE ACCESS to the Republic. Gate to Martial Historian." },
  // Guncraft
  { key:"fast_hands",    name:"Fast Hands",         cost:50,  tree:"Guncraft",    tier:0, desc:"Swap ammo or switch guns as a FREE action. Always take this first." },
  { key:"alert",         name:"Alert",              cost:100, tree:"Guncraft",    tier:1, desc:"Significantly harder to ambush. Required for Eagle Eye." },
  { key:"wheelgun",      name:"Wheelgun Familiarity", cost:100, tree:"Guncraft", tier:1, desc:"Unlocks T1 revolver skills and revolvers." },
  { key:"rifle",         name:"Rifle Training",     cost:100, tree:"Guncraft",    tier:1, desc:"Unlocks T1 rifle skills and rifles." },
  // Magecraft
  { key:"mana_skin",     name:"Mana Skin",          cost:50,  tree:"Magecraft",   tier:0, desc:"−10% magical damage taken. 2% mana/turn drain while active." },
  { key:"mana_sensing",  name:"Mana Sensing",       cost:50,  tree:"Magecraft",   tier:0, desc:"Detect wards, catalysts, and living things with mana in range." },
  // Forgecraft
  { key:"tool_prof",     name:"Tool Proficiency",   cost:20,  tree:"Forgecraft",  tier:0, desc:"+2 to ALL tool-use rolls. Always worth it." },
  { key:"lockpicking",   name:"Lockpicking",        cost:50,  tree:"Forgecraft",  tier:0, desc:"+2 lockpicking rolls. Gate to Lock Mechanism." },
  { key:"utility_beg",   name:"Utility Beginner",   cost:100, tree:"Forgecraft",  tier:1, desc:"Foundation of ALL Forgecraft. Required for every crafting path." },
  { key:"field_stab",    name:"Field Stabilizer",   cost:100, tree:"Forgecraft",  tier:1, desc:"1 AP + Bonus Action: ally gains +10% clashing output for 1 turn." },
  // Field Medic
  { key:"basic_medkits", name:"Basic Medkits",      cost:20,  tree:"Field Medic", tier:0, desc:"Craft and use basic medkits. First purchase for any healer." },
  { key:"stabilization", name:"Stabilization",      cost:100, tree:"Field Medic", tier:1, desc:"Stabilise someone even without a medkit available." },
  // Tactician
  { key:"tactical_i",    name:"Tactical Orders I",  cost:100, tree:"Tactician",   tier:0, desc:"Buff 1 ally's output or dodge. Costs a bonus action." },
  // Smuggler
  { key:"light_load",    name:"Light Load",         cost:20,  tree:"Smuggler",    tier:0, desc:"Mark one item as weight 0. Always worth it early." },
  { key:"concealment",   name:"Concealment",        cost:100, tree:"Smuggler",    tier:0, desc:"+5 to solo stealth checks. Always active." },
  // Politician
  { key:"silver_tongue", name:"Silver Tongue",      cost:20,  tree:"Politician",  tier:0, desc:"+1 to persuasion. Permanent. Gate to Master Negotiator." },
  // Beastmaster
  { key:"obedience",     name:"Obedience",          cost:50,  tree:"Beastmaster", tier:0, desc:"Give advanced non-combat commands to mounts and pets." },
  { key:"prof_command",  name:"Proficient Command", cost:100, tree:"Beastmaster", tier:1, desc:"Use a Bonus Action to command your companion in combat." },
];

const CREATION_STEPS = [
  { id:1, title:"Background",  subtitle:"Where are you from?" },
  { id:2, title:"Class",       subtitle:"What do you do?" },
  { id:3, title:"Traits",      subtitle:"Who are you?" },
  { id:4, title:"Stats",       subtitle:"How are you built?" },
  { id:5, title:"Skills",      subtitle:"What have you learned?" },
  { id:6, title:"Review",      subtitle:"Your starting build" },
];

// ── MAIN COMPONENT ────────────────────────────────────────────────────────────

export default function GettingStartedDashboard({
  discordId,
  jump,
}: {
  discordId: string;
  jump?: (tab: any) => void;
}) {
  const [hubTab, setHubTab] = useState<HubTab>("start");
  const [build, setBuild] = useState<BuildState>({
    city: "", classChoice: "", selectedTraits: [],
    stats: { strength:10, dexterity:10, stamina:10, magic_affinity:10, mana:10 },
    selectedSkills: [], step: 1,
  });

  // ── Derived values ────────────────────────────────────────
  const statXP   = totalStatXP(build.stats);
  const skillXP  = totalSkillXP(build.selectedSkills, STARTING_SKILLS);
  const xpSpent  = statXP + skillXP;
  const xpLeft   = 600 - xpSpent;
  const xpPct    = Math.min(100, (xpSpent / 600) * 100);

  const traitPtsUsed = build.selectedTraits.reduce((sum, t) => {
    for (const tier of TRAIT_TIERS) {
      const found = tier.traits.find(x => x.name === t);
      if (found) return sum + found.cost;
    }
    return sum;
  }, 0);
  const traitLeft = 5 - traitPtsUsed;

  function updateStep(n: number) { setBuild(prev => ({ ...prev, step: n })); }

  function toggleTrait(name: string, cost: number) {
    if (build.selectedTraits.includes(name)) {
      setBuild(prev => ({ ...prev, selectedTraits: prev.selectedTraits.filter(t => t !== name) }));
    } else {
      if (traitPtsUsed + cost > 5) return;
      setBuild(prev => ({ ...prev, selectedTraits: [...prev.selectedTraits, name] }));
    }
  }

  function toggleSkill(key: string, cost: number) {
    if (build.selectedSkills.includes(key)) {
      setBuild(prev => ({ ...prev, selectedSkills: prev.selectedSkills.filter(s => s !== key) }));
    } else {
      if (xpLeft < cost) return;
      setBuild(prev => ({ ...prev, selectedSkills: [...prev.selectedSkills, key] }));
    }
  }

  // ── Shared styles ─────────────────────────────────────────
  const pill = (active: boolean, color = "#2f6f73"): React.CSSProperties => ({
    padding: "10px 14px",
    border: `1px solid ${active ? color : "#e0d4c4"}`,
    borderRadius: "8px",
    cursor: "pointer",
    background: active ? `${color}10` : "white",
    transition: "all 0.12s",
  });

  const xpColor = xpLeft < 0 ? "#e05555" : xpLeft < 80 ? "#c8922a" : "#2f6f73";

  const XPBadge = () => (
    <span style={{
      fontFamily:"monospace", fontSize:"13px", fontWeight:700,
      color: xpColor, background:`${xpColor}18`,
      padding:"4px 12px", borderRadius:"6px",
    }}>
      {xpLeft < 0 ? `${Math.abs(xpLeft)} XP over` : `${xpLeft} XP left`}
    </span>
  );

  const XPBar = () => (
    <div style={{ marginBottom:"20px" }}>
      <div style={{ height:"7px", background:"#e0d4c4", borderRadius:"4px", overflow:"hidden", marginBottom:"6px" }}>
        <div style={{ height:"100%", width:`${xpPct}%`, background: xpLeft < 0 ? "#e05555" : "#2f6f73", transition:"width 0.2s", borderRadius:"4px" }} />
      </div>
      <div style={{ display:"flex", justifyContent:"space-between", fontSize:"12px", color:"#888" }}>
        <span>Stats: <strong>{statXP}</strong></span>
        <span>Skills: <strong>{skillXP}</strong></span>
        <span style={{ color: xpColor, fontWeight:700 }}>{xpSpent} / 600 XP</span>
      </div>
    </div>
  );

  const BackNext = ({ onBack, onNext, nextLabel = "Next", nextDisabled = false }: any) => (
    <div style={{ display:"flex", justifyContent:"space-between", marginTop:"20px" }}>
      <button className="ghost" onClick={onBack} style={{ display:"flex", alignItems:"center", gap:"6px" }}>
        <ChevronLeft size={15}/> Back
      </button>
      <button onClick={onNext} disabled={nextDisabled} style={{ display:"flex", alignItems:"center", gap:"6px" }}>
        {nextLabel} <ChevronRight size={15}/>
      </button>
    </div>
  );

  // ── HUB TABS ──────────────────────────────────────────────
  const HUB_TABS: { id:HubTab; label:string; icon:React.ReactNode }[] = [
    { id:"start",  label:"Start Here",         icon:<Home size={14}/> },
    { id:"create", label:"Character Creation", icon:<BookOpen size={14}/> },
    { id:"skills", label:"Skills",             icon:<Sparkles size={14}/> },
    { id:"world",  label:"World",              icon:<Globe size={14}/> },
    { id:"guide",  label:"Server Guide",       icon:<Scroll size={14}/> },
  ];

  return (
    <section>
      {/* ── PAGE HEADER + INNER TABS ── */}
      <div style={{ padding:"24px 28px 0", borderBottom:"1px solid #e0d4c4" }}>
        <span className="activity-type-label">Getting Started</span>
        <h2 style={{ margin:"6px 0 4px" }}>Railbound Player Hub</h2>
        <p className="muted-text" style={{ fontSize:"13px", marginBottom:"16px" }}>
          Everything a new player needs — character creation, skill reference, world lore, and server guide.
        </p>
        <div style={{ display:"flex", gap:"2px", flexWrap:"wrap" }}>
          {HUB_TABS.map(t => (
            <button
              key={t.id}
              onClick={() => setHubTab(t.id)}
              className={hubTab === t.id ? "" : "ghost"}
              style={{
                display:"flex", alignItems:"center", gap:"6px",
                fontSize:"13px", padding:"9px 16px",
                borderRadius:"8px 8px 0 0",
                marginBottom:"-1px",
                borderBottom: hubTab === t.id ? "2px solid #2f6f73" : "2px solid transparent",
              }}
            >
              {t.icon} {t.label}
            </button>
          ))}
        </div>
      </div>

      <div style={{ padding:"28px" }}>

        {/* ══════════════════════════════════════════════════
            START HERE
        ══════════════════════════════════════════════════ */}
        {hubTab === "start" && (
          <div style={{ maxWidth:"820px" }}>

            <div className="card" style={{ marginBottom:"20px", borderLeft:"4px solid #2f6f73" }}>
              <h3 style={{ marginBottom:"8px" }}>Welcome to Railbound RP</h3>
              <p style={{ fontSize:"14px", color:"#555", lineHeight:"1.7", marginBottom:"10px" }}>
                Railbound is a Discord roleplay server set in <strong>Doranswyr</strong> — a fractured continent in its early industrial era (~1845). Steam engines and revolvers exist alongside Source magic, mythical beasts, and the ruins of a 1,800-year-old Republic that collapsed 30 years ago.
              </p>
              <p style={{ fontSize:"14px", color:"#555", lineHeight:"1.7" }}>
                You play as a character working within one of four <strong>mercenary guilds</strong> — neutral contractors who operate across all city-states, bound by contracts rather than national loyalty.
              </p>
            </div>

            <h3 style={{ marginBottom:"14px" }}>What to do first</h3>
            <div style={{ display:"grid", gridTemplateColumns:"repeat(auto-fill, minmax(220px,1fr))", gap:"10px", marginBottom:"24px" }}>
              {[
                { num:"01", title:"Read the rules",          desc:"Check #rules and #server-info before anything else." },
                { num:"02", title:"Use the Character Creator", desc:"Click the Character Creation tab above and follow the guided flow." },
                { num:"03", title:"Fill out your OC sheet",  desc:"Copy the OC Draft Template Google Doc and fill it out completely." },
                { num:"04", title:"Submit for approval",     desc:"Open a ticket in #oc-submissions with your sheet link." },
                { num:"05", title:"Get your guild role",     desc:"Once approved, staff assigns your guild and OC roles." },
                { num:"06", title:"Start RPing",             desc:"Head to an open RP channel or sign up for a mission." },
              ].map(s => (
                <div key={s.num} className="card" style={{ padding:"14px" }}>
                  <div style={{ display:"flex", alignItems:"center", gap:"8px", marginBottom:"6px" }}>
                    <span style={{ fontFamily:"monospace", fontSize:"11px", color:"#2f6f73", fontWeight:700, background:"#2f6f7315", padding:"3px 7px", borderRadius:"4px" }}>{s.num}</span>
                    <strong style={{ fontSize:"13px" }}>{s.title}</strong>
                  </div>
                  <p className="muted-text" style={{ fontSize:"12px", lineHeight:"1.5" }}>{s.desc}</p>
                </div>
              ))}
            </div>

            <h3 style={{ marginBottom:"12px" }}>Explore the hub</h3>
            <div style={{ display:"flex", gap:"10px", flexWrap:"wrap" }}>
              <button onClick={() => setHubTab("create")} style={{ display:"flex", alignItems:"center", gap:"7px" }}>
                <BookOpen size={15}/> Build Your Character
              </button>
              <button className="ghost" onClick={() => setHubTab("world")} style={{ display:"flex", alignItems:"center", gap:"7px" }}>
                <Globe size={15}/> Explore the World
              </button>
              <button className="ghost" onClick={() => setHubTab("skills")} style={{ display:"flex", alignItems:"center", gap:"7px" }}>
                <Sparkles size={15}/> Browse Skills
              </button>
              <button className="ghost" onClick={() => setHubTab("guide")} style={{ display:"flex", alignItems:"center", gap:"7px" }}>
                <Scroll size={15}/> Server Guide
              </button>
            </div>
          </div>
        )}

        {/* ══════════════════════════════════════════════════
            CHARACTER CREATION — GUIDED FLOW
        ══════════════════════════════════════════════════ */}
        {hubTab === "create" && (
          <div style={{ maxWidth:"900px" }}>

            {/* Step progress */}
            <div style={{ display:"flex", gap:"0", marginBottom:"28px", overflowX:"auto" }}>
              {CREATION_STEPS.map(s => {
                const done    = build.step > s.id;
                const current = build.step === s.id;
                return (
                  <div
                    key={s.id}
                    onClick={() => updateStep(s.id)}
                    style={{
                      flex:"1", minWidth:"90px", padding:"10px 8px", textAlign:"center",
                      borderBottom:`3px solid ${current ? "#2f6f73" : done ? "#4caf7d" : "#e0d4c4"}`,
                      cursor:"pointer", opacity: build.step < s.id ? 0.5 : 1, transition:"all 0.15s",
                    }}
                  >
                    <div style={{ fontSize:"11px", fontWeight:700, fontFamily:"monospace", letterSpacing:"1px", marginBottom:"2px",
                      color: current ? "#2f6f73" : done ? "#4caf7d" : "#aaa" }}>
                      {done ? "✓" : `0${s.id}`}
                    </div>
                    <div style={{ fontSize:"12px", fontWeight:600, color: current ? "#2c241e" : "#777" }}>{s.title}</div>
                    <div style={{ fontSize:"10px", color:"#aaa" }}>{s.subtitle}</div>
                  </div>
                );
              })}
            </div>

            {/* ── STEP 1: Background ── */}
            {build.step === 1 && (
              <div>
                <h3 style={{ marginBottom:"6px" }}>Where did your character come from?</h3>
                <p className="muted-text" style={{ fontSize:"13px", marginBottom:"18px" }}>
                  Your origin shapes your free Origin Trait (doesn't count toward your 5pt budget) and determines what your character naturally knows about the world.
                </p>
                <div style={{ display:"grid", gridTemplateColumns:"repeat(auto-fill, minmax(250px,1fr))", gap:"10px", marginBottom:"20px" }}>
                  {CITIES.map(city => (
                    <div
                      key={city.id}
                      onClick={() => setBuild(prev => ({ ...prev, city: city.id }))}
                      style={pill(build.city === city.id)}
                    >
                      <div style={{ display:"flex", alignItems:"center", gap:"8px", marginBottom:"5px" }}>
                        <strong style={{ fontSize:"14px", flex:1 }}>{city.name}</strong>
                        {build.city === city.id && <Check size={13} color="#2f6f73"/>}
                        <span className="activity-type-label" style={{ fontSize:"9px" }}>{city.tag}</span>
                      </div>
                      <p className="muted-text" style={{ fontSize:"12px", lineHeight:"1.5" }}>{city.desc}</p>
                    </div>
                  ))}
                </div>
                <div style={{ display:"flex", justifyContent:"flex-end" }}>
                  <button onClick={() => updateStep(2)} disabled={!build.city} style={{ display:"flex", alignItems:"center", gap:"6px" }}>
                    Next: Your Class <ChevronRight size={15}/>
                  </button>
                </div>
              </div>
            )}

            {/* ── STEP 2: Class ── */}
            {build.step === 2 && (
              <div>
                <h3 style={{ marginBottom:"6px" }}>What does your character do?</h3>
                <p className="muted-text" style={{ fontSize:"13px", marginBottom:"18px" }}>
                  Class traits are <strong>mutually exclusive</strong> — pick only one. They cost 3pts (class) or 2pts (subclass) from your 5pt trait budget. No class trait = All-Rounder, which keeps those 3pts free for Keystone traits.
                </p>
                <div style={{ display:"grid", gridTemplateColumns:"repeat(auto-fill, minmax(250px,1fr))", gap:"10px", marginBottom:"20px" }}>
                  {CLASSES.map(cls => {
                    const Icon = cls.icon;
                    const active = build.classChoice === cls.id;
                    return (
                      <div
                        key={cls.id}
                        onClick={() => setBuild(prev => ({ ...prev, classChoice: cls.id, selectedTraits: [] }))}
                        style={pill(active)}
                      >
                        <div style={{ display:"flex", alignItems:"center", gap:"8px", marginBottom:"5px" }}>
                          <Icon size={15} color={active ? "#2f6f73" : "#888"}/>
                          <strong style={{ fontSize:"13px", flex:1 }}>{cls.name}</strong>
                          {active && <Check size={13} color="#2f6f73"/>}
                          <span className="activity-type-label" style={{ fontSize:"9px" }}>{cls.cost > 0 ? `${cls.cost}pt` : "Free"}</span>
                        </div>
                        <p style={{ fontSize:"10px", color:"#999", fontStyle:"italic", marginBottom:"5px" }}>{cls.trait}</p>
                        <p className="muted-text" style={{ fontSize:"12px", lineHeight:"1.5", marginBottom:"5px" }}>{cls.desc}</p>
                        <p style={{ fontSize:"11px", color:"#2f6f73" }}><strong>Best for:</strong> {cls.bestFor}</p>
                      </div>
                    );
                  })}
                </div>
                <BackNext onBack={() => updateStep(1)} onNext={() => updateStep(3)} nextDisabled={!build.classChoice}/>
              </div>
            )}

            {/* ── STEP 3: Traits ── */}
            {build.step === 3 && (
              <div>
                <div style={{ display:"flex", alignItems:"center", gap:"14px", marginBottom:"6px", flexWrap:"wrap" }}>
                  <h3>Choose your traits</h3>
                  <span style={{ fontFamily:"monospace", fontSize:"13px", fontWeight:700,
                    color: traitLeft < 0 ? "#e05555" : traitLeft === 0 ? "#4caf7d" : "#2f6f73",
                    background: traitLeft < 0 ? "#e0555520" : "#2f6f7315", padding:"4px 12px", borderRadius:"6px" }}>
                    {traitPtsUsed} / 5 pts used
                  </span>
                </div>
                <p className="muted-text" style={{ fontSize:"13px", marginBottom:"18px" }}>
                  You have <strong>5 trait points</strong> + 1 free Origin Trait. Taking Negative Traits refunds points (up to 8 pts total). Your class choice above has already been noted — if it has a 2–3pt cost, allocate accordingly.
                </p>

                {TRAIT_TIERS.map(tier => (
                  <div key={tier.label} className="card" style={{ marginBottom:"14px", padding:"16px" }}>
                    <strong style={{ fontSize:"13px", display:"block", marginBottom:"3px" }}>{tier.label}</strong>
                    <p className="muted-text" style={{ fontSize:"11px", marginBottom:"12px" }}>{tier.note}</p>
                    <div style={{ display:"grid", gridTemplateColumns:"repeat(auto-fill, minmax(200px,1fr))", gap:"8px" }}>
                      {tier.traits.map(trait => {
                        const selected = build.selectedTraits.includes(trait.name);
                        const cantAfford = !selected && traitPtsUsed + trait.cost > 5;
                        return (
                          <div
                            key={trait.name}
                            onClick={() => !cantAfford && toggleTrait(trait.name, trait.cost)}
                            style={{
                              padding:"10px 12px", borderRadius:"6px",
                              border:`1px solid ${selected ? "#2f6f73" : "#e0d4c4"}`,
                              background: selected ? "#2f6f7310" : cantAfford ? "#faf7f3" : "white",
                              cursor: cantAfford ? "not-allowed" : "pointer",
                              opacity: cantAfford ? 0.5 : 1, transition:"all 0.12s",
                            }}
                          >
                            <div style={{ display:"flex", alignItems:"center", gap:"6px", marginBottom:"4px" }}>
                              <strong style={{ fontSize:"13px", flex:1 }}>{trait.name}</strong>
                              <span style={{ fontFamily:"monospace", fontSize:"10px", fontWeight:700, color: selected ? "#2f6f73" : "#aaa" }}>{trait.cost}pt</span>
                              {selected && <Check size={12} color="#2f6f73"/>}
                            </div>
                            <p style={{ fontSize:"11px", color:"#666", lineHeight:"1.4" }}>{trait.desc}</p>
                          </div>
                        );
                      })}
                    </div>
                  </div>
                ))}

                <BackNext onBack={() => updateStep(2)} onNext={() => updateStep(4)}/>
              </div>
            )}

            {/* ── STEP 4: Stats ── */}
            {build.step === 4 && (
              <div>
                <div style={{ display:"flex", alignItems:"center", gap:"14px", flexWrap:"wrap", marginBottom:"6px" }}>
                  <h3>Set your starting stats</h3>
                  <XPBadge/>
                </div>
                <p className="muted-text" style={{ fontSize:"13px", marginBottom:"18px" }}>
                  All 5 stats start at <strong>10 for free</strong>. You have <strong>600 XP</strong> to split across stat raises AND skill purchases (next step). Drag the sliders to allocate.
                </p>
                <XPBar/>

                <div className="card" style={{ padding:"20px", marginBottom:"16px" }}>
                  {STAT_KEYS.map(key => {
                    const val = build.stats[key] ?? 10;
                    const xp  = calcStatXP(10, val);
                    return (
                      <div key={key} style={{ marginBottom:"18px" }}>
                        <div style={{ display:"flex", justifyContent:"space-between", marginBottom:"5px" }}>
                          <span style={{ fontSize:"14px", fontWeight:600 }}>{STAT_LABELS[key]}</span>
                          <span style={{ fontSize:"13px" }}>
                            <strong>{val}</strong>
                            <span className="muted-text" style={{ marginLeft:"8px" }}>{xp > 0 ? `+${xp} XP` : "free"}</span>
                          </span>
                        </div>
                        <input type="range" min={10} max={200} value={val}
                          onChange={e => setBuild(prev => ({ ...prev, stats: { ...prev.stats, [key]: Number(e.target.value) } }))}
                          style={{ width:"100%", accentColor:"#2f6f73" }}
                        />
                        <div style={{ display:"flex", justifyContent:"space-between", fontSize:"10px", color:"#ccc", marginTop:"2px" }}>
                          <span>10 free</span><span>50 (1xp/pt)</span><span>150 (2xp/pt)</span><span>200 (4xp/pt)</span>
                        </div>
                      </div>
                    );
                  })}
                </div>

                <div className="card" style={{ padding:"12px 16px", marginBottom:"20px" }}>
                  <strong style={{ fontSize:"12px", display:"block", marginBottom:"8px" }}>Cost reference</strong>
                  <div style={{ display:"flex", gap:"6px", flexWrap:"wrap" }}>
                    {XP_BANDS.slice(0,4).map(b => (
                      <span key={b.min} style={{ fontSize:"11px", background:"#f6efe4", padding:"3px 9px", borderRadius:"4px", color:"#666" }}>
                        {b.min}–{b.max}: <strong>{b.cost} xp/pt</strong>
                      </span>
                    ))}
                    <span style={{ fontSize:"11px", color:"#bbb", padding:"3px 0" }}>→ rises further above 250</span>
                  </div>
                </div>

                <BackNext onBack={() => updateStep(3)} onNext={() => updateStep(5)} nextLabel="Next: Skills"/>
              </div>
            )}

            {/* ── STEP 5: Skills ── */}
            {build.step === 5 && (
              <div>
                <div style={{ display:"flex", alignItems:"center", gap:"14px", flexWrap:"wrap", marginBottom:"6px" }}>
                  <h3>Choose starting skills</h3>
                  <XPBadge/>
                </div>
                <p className="muted-text" style={{ fontSize:"13px", marginBottom:"18px" }}>
                  Common first purchases shown here. For the full list use the Skills tab above. Grayed out = not enough XP remaining.
                </p>
                <XPBar/>

                {Array.from(new Set(STARTING_SKILLS.map(s => s.tree))).map(tree => (
                  <div key={tree} style={{ marginBottom:"16px" }}>
                    <div style={{ fontSize:"11px", fontWeight:700, letterSpacing:"2px", color:"#888", marginBottom:"8px", textTransform:"uppercase" }}>{tree}</div>
                    <div style={{ display:"grid", gridTemplateColumns:"repeat(auto-fill, minmax(210px,1fr))", gap:"8px" }}>
                      {STARTING_SKILLS.filter(s => s.tree === tree).map(skill => {
                        const selected    = build.selectedSkills.includes(skill.key);
                        const cantAfford  = !selected && xpLeft < skill.cost;
                        return (
                          <div
                            key={skill.key}
                            onClick={() => !cantAfford && toggleSkill(skill.key, skill.cost)}
                            style={{
                              padding:"10px 12px", borderRadius:"6px",
                              border:`1px solid ${selected ? "#2f6f73" : "#e0d4c4"}`,
                              background: selected ? "#2f6f7310" : cantAfford ? "#faf7f3" : "white",
                              cursor: cantAfford ? "not-allowed" : "pointer",
                              opacity: cantAfford ? 0.5 : 1, transition:"all 0.12s",
                            }}
                          >
                            <div style={{ display:"flex", alignItems:"center", gap:"6px", marginBottom:"4px" }}>
                              <strong style={{ fontSize:"13px", flex:1 }}>{skill.name}</strong>
                              <span style={{ fontFamily:"monospace", fontSize:"10px", fontWeight:700, color: selected ? "#2f6f73" : "#aaa" }}>{skill.cost} XP</span>
                              {selected && <Check size={12} color="#2f6f73"/>}
                            </div>
                            <p style={{ fontSize:"11px", color:"#666", lineHeight:"1.4" }}>{skill.desc}</p>
                          </div>
                        );
                      })}
                    </div>
                  </div>
                ))}

                <BackNext onBack={() => updateStep(4)} onNext={() => updateStep(6)} nextLabel="Review Build"/>
              </div>
            )}

            {/* ── STEP 6: Review ── */}
            {build.step === 6 && (
              <div>
                <h3 style={{ marginBottom:"4px" }}>Your Starting Build</h3>
                <p className="muted-text" style={{ fontSize:"13px", marginBottom:"20px" }}>
                  Use this as a reference when filling out your OC sheet and submitting for approval.
                </p>

                {xpLeft < 0 && (
                  <div style={{ background:"#e0555510", border:"1px solid #e05555", borderRadius:"6px", padding:"12px 16px", marginBottom:"16px", display:"flex", gap:"8px", alignItems:"flex-start" }}>
                    <AlertTriangle size={15} color="#e05555" style={{ flexShrink:0, marginTop:"2px" }}/>
                    <p style={{ fontSize:"13px", color:"#c03333" }}>
                      You're <strong>{Math.abs(xpLeft)} XP over budget</strong>. Go back and reduce stats or remove skills before submitting your OC.
                    </p>
                  </div>
                )}

                <div style={{ display:"grid", gridTemplateColumns:"1fr 1fr", gap:"14px", marginBottom:"14px" }}>

                  <div className="card" style={{ padding:"16px" }}>
                    <div className="card-title-row" style={{ marginBottom:"10px" }}>
                      <strong>Background & Class</strong>
                    </div>
                    <p style={{ fontSize:"13px", marginBottom:"6px" }}>
                      <span className="muted-text">Origin: </span>
                      <strong>{CITIES.find(c => c.id === build.city)?.name || "—"}</strong>
                    </p>
                    <p style={{ fontSize:"13px" }}>
                      <span className="muted-text">Class: </span>
                      <strong>{CLASSES.find(c => c.id === build.classChoice)?.name || "—"}</strong>
                    </p>
                  </div>

                  <div className="card" style={{ padding:"16px" }}>
                    <div className="card-title-row" style={{ marginBottom:"10px" }}>
                      <strong>XP Budget</strong>
                      <span className="activity-type-label">600 XP</span>
                    </div>
                    <div style={{ height:"6px", background:"#e0d4c4", borderRadius:"3px", marginBottom:"8px", overflow:"hidden" }}>
                      <div style={{ height:"100%", width:`${xpPct}%`, background: xpLeft < 0 ? "#e05555" : "#2f6f73", borderRadius:"3px" }}/>
                    </div>
                    <div style={{ display:"flex", justifyContent:"space-between", fontSize:"13px" }}>
                      <span className="muted-text">Spent: <strong>{xpSpent} XP</strong></span>
                      <span style={{ color: xpColor, fontWeight:700 }}>
                        {xpLeft >= 0 ? `${xpLeft} remaining` : `${Math.abs(xpLeft)} over`}
                      </span>
                    </div>
                  </div>
                </div>

                {/* Traits */}
                <div className="card" style={{ padding:"16px", marginBottom:"14px" }}>
                  <div className="card-title-row" style={{ marginBottom:"10px" }}>
                    <strong>Traits</strong>
                    <span className="activity-type-label">{traitPtsUsed} / 5 pts</span>
                  </div>
                  {build.selectedTraits.length === 0
                    ? <p className="muted-text" style={{ fontSize:"13px" }}>No traits selected.</p>
                    : (
                      <div style={{ display:"flex", gap:"6px", flexWrap:"wrap" }}>
                        {build.selectedTraits.map(t => {
                          let cost = 0;
                          for (const tier of TRAIT_TIERS) { const f = tier.traits.find(x => x.name === t); if (f) { cost = f.cost; break; } }
                          return (
                            <span key={t} style={{ fontSize:"12px", background:"#2f6f7315", color:"#2f6f73", padding:"4px 10px", borderRadius:"20px", border:"1px solid #2f6f7340" }}>
                              {t} ({cost}pt)
                            </span>
                          );
                        })}
                      </div>
                    )}
                </div>

                {/* Stats */}
                <div className="card" style={{ padding:"16px", marginBottom:"14px" }}>
                  <div className="card-title-row" style={{ marginBottom:"10px" }}>
                    <strong>Starting Stats</strong>
                    <span className="activity-type-label">{statXP} XP</span>
                  </div>
                  <div style={{ display:"grid", gridTemplateColumns:"repeat(5,1fr)", gap:"8px" }}>
                    {STAT_KEYS.map(key => {
                      const val = build.stats[key] ?? 10;
                      const xp  = calcStatXP(10, val);
                      return (
                        <div key={key} style={{ textAlign:"center", padding:"10px 6px", background:"#f6efe4", borderRadius:"6px" }}>
                          <div style={{ fontSize:"20px", fontWeight:800, color:"#2f6f73", lineHeight:1 }}>{val}</div>
                          <div style={{ fontSize:"10px", color:"#888", marginTop:"3px", letterSpacing:"0.5px" }}>{STAT_LABELS[key].replace(" ","").toUpperCase()}</div>
                          {xp > 0 && <div style={{ fontSize:"10px", color:"#2f6f73", marginTop:"2px" }}>+{xp}xp</div>}
                        </div>
                      );
                    })}
                  </div>
                </div>

                {/* Skills */}
                <div className="card" style={{ padding:"16px", marginBottom:"20px" }}>
                  <div className="card-title-row" style={{ marginBottom:"10px" }}>
                    <strong>Starting Skills</strong>
                    <span className="activity-type-label">{skillXP} XP</span>
                  </div>
                  {build.selectedSkills.length === 0
                    ? <p className="muted-text" style={{ fontSize:"13px" }}>No skills selected.</p>
                    : (
                      <div style={{ display:"flex", flexDirection:"column", gap:"6px" }}>
                        {build.selectedSkills.map(key => {
                          const s = STARTING_SKILLS.find(x => x.key === key);
                          return s ? (
                            <div key={key} style={{ display:"flex", alignItems:"center", gap:"8px", fontSize:"13px" }}>
                              <Check size={12} color="#4caf7d"/>
                              <strong>{s.name}</strong>
                              <span className="muted-text" style={{ fontSize:"12px" }}>({s.tree})</span>
                              <span style={{ marginLeft:"auto", fontFamily:"monospace", fontSize:"12px", color:"#888" }}>{s.cost} XP</span>
                            </div>
                          ) : null;
                        })}
                      </div>
                    )}
                </div>

                <div style={{ display:"flex", gap:"10px", justifyContent:"space-between" }}>
                  <button className="ghost" onClick={() => updateStep(5)} style={{ display:"flex", alignItems:"center", gap:"6px" }}>
                    <ChevronLeft size={15}/> Back
                  </button>
                  <div style={{ display:"flex", gap:"10px" }}>
                    <button className="ghost" onClick={() => setBuild({ city:"", classChoice:"", selectedTraits:[], stats:{strength:10,dexterity:10,stamina:10,magic_affinity:10,mana:10}, selectedSkills:[], step:1 })}>
                      Start Over
                    </button>
                    {jump && (
                      <button onClick={() => jump("register")} style={{ display:"flex", alignItems:"center", gap:"6px" }}>
                        Register OC <ChevronRight size={15}/>
                      </button>
                    )}
                  </div>
                </div>
              </div>
            )}
          </div>
        )}

        {/* ══════════════════════════════════════════════════
            SKILLS — Quick Reference
        ══════════════════════════════════════════════════ */}
        {hubTab === "skills" && (
          <div style={{ maxWidth:"860px" }}>
            <div className="card" style={{ marginBottom:"16px", borderLeft:"4px solid #2f6f73", padding:"16px" }}>
              <h3 style={{ marginBottom:"6px" }}>Skill Reference</h3>
              <p className="muted-text" style={{ fontSize:"13px", marginBottom:"12px" }}>
                Skill chains for every class tree. For the full interactive browser with search and filters, use the Skills tab in the main navigation.
              </p>
              {jump && (
                <button onClick={() => jump("skills")} style={{ display:"flex", alignItems:"center", gap:"7px", fontSize:"13px" }}>
                  <Sparkles size={15}/> Open Full Skills Dashboard
                </button>
              )}
            </div>

            {[
              { tree:"Mercenary",         color:"#2f6f73",  chains:["Pilfer → Stealth → Misdirection","Adept → Operative → Veteran","Pacing (standalone) | Quartermastery (standalone)"] },
              { tree:"Martial — Heavy",   color:"#8b4513",  chains:["Heavy Armaments → Taunt → Dominion","Heavy Armaments → Berserker → Sweeping Strike","Heavy Armaments → Honed Strike → Mastered Strike"] },
              { tree:"Martial — Light",   color:"#8b6914",  chains:["Light Armaments → Crowd Feint → Swashbuckler","Light Armaments → Unbound → Disarm","Light Armaments → Duelist → Parry"] },
              { tree:"Martial Arts",      color:"#6b4c8b",  chains:["Martial Arts → Offensive Defense → Furious Technique","Martial Arts → Trance → Disarm","Martial Arts → Brawler → Grappler → Form Mastery"] },
              { tree:"Magecraft",         color:"#3b7dbf",  chains:["Force T0 → T1 → T2 → T3 (Water / Earth / Wind / Fire)","Restoration → Advanced → Mastered | +Purification","Abjuration → Wards / Barriers → Reflection","Destruction → Offensive Area Magic | Offensive Wards","Mana Skin → Reflexive Mana Skin | Overcharge → Mastered Overcharge","Regeneration → Focused Regeneration | Enchantment (T3)"] },
              { tree:"Forgecraft",        color:"#b8721a",  chains:["Utility Beginner → Practitioner → Expert  ← REQUIRED FIRST","Smithing Rookie → Novice → Extraordinaire","Snare Trainee → Apprentice → Master","Demolition Learner → Trainee → Specialist","Chemical Assistant → Analyst → Scientist"] },
              { tree:"Guncraft",          color:"#8b3030",  chains:["Wheelgun Familiarity → Quickdraw → Revolver Virtuoso","Rifle Training → Sharpshooter → Deadeye","Scattergun Familiarity → Close-Quarters → Breacher","Good Eyes + Alert → Eagle Eye","Lesser Reload → Veteran Reload"] },
              { tree:"Beastmaster",       color:"#3d7a3d",  chains:["Obedience → Proficient Command → Advanced Command","Shared Experience → Shared Experience II","Remote Sense → Spectral Bond","Mauling (standalone OC combat skill)"] },
              { tree:"Field Medic",       color:"#2d7a7a",  chains:["Basic Medkits → Advanced Medkits → Surgery","Prepared Medic I → II → III","Compound Medicine (requires Advanced Medkits)","Stabilization (standalone)"] },
              { tree:"Tactician",         color:"#555",     chains:["Tactical Orders I → II → III","Target Tracking → Battlefield Awareness"] },
              { tree:"Smuggler",          color:"#7a3d7a",  chains:["Light Load → Hidden Compartments","Concealment → Mass Concealment","Safer Routes → Ghost Run","Black Market Access (standalone T2)"] },
              { tree:"Politician",        color:"#3d557a",  chains:["Silver Tongue → Master Negotiator","Reputation Management → Political Network","Passive Income → Investment Making","Contractional Servitude (requires Silver Tongue + Reputation Management)"] },
              { tree:"Knowledge",         color:"#888",     chains:["Linguistics → Print Forgery | Codebreaking","Geology → Metallurgy","Biology → Veterinary Study","Doranswyr Historian → Martial Historian","Catechumen → Luminary"] },
            ].map(s => (
              <div key={s.tree} className="card" style={{ marginBottom:"10px", padding:"14px 16px" }}>
                <div style={{ display:"flex", alignItems:"center", gap:"8px", marginBottom:"10px" }}>
                  <div style={{ width:"8px", height:"8px", borderRadius:"50%", background:s.color }}/>
                  <strong style={{ fontSize:"14px" }}>{s.tree}</strong>
                </div>
                {s.chains.map((chain, i) => (
                  <p key={i} style={{ fontSize:"12px", color:"#555", fontFamily:"monospace", lineHeight:"1.7" }}>{chain}</p>
                ))}
              </div>
            ))}
          </div>
        )}

        {/* ══════════════════════════════════════════════════
            WORLD
        ══════════════════════════════════════════════════ */}
        {hubTab === "world" && (
          <div style={{ maxWidth:"860px" }}>

            <div className="card" style={{ marginBottom:"20px", borderLeft:"4px solid #2f6f73", padding:"16px" }}>
              <h3 style={{ marginBottom:"8px" }}>The World of Doranswyr</h3>
              <p style={{ fontSize:"14px", color:"#555", lineHeight:"1.7" }}>
                Doranswyr is a massive continent (~3,000 miles east to west) set in its early industrial era. The 1,800-year-old Republic collapsed 30 years ago when General Vegard Ragon massacred the Senate on May 14th, 1815. The current year is <strong>1845</strong>. Ten city-states now scramble for power and survival — the only efficient travel between them is by railroad.
              </p>
            </div>

            <h3 style={{ marginBottom:"12px" }}>City-States</h3>
            <div style={{ display:"grid", gridTemplateColumns:"repeat(auto-fill, minmax(250px,1fr))", gap:"10px", marginBottom:"24px" }}>
              {CITIES.filter(c => c.id !== "outlands").map(city => (
                <div key={city.id} className="card" style={{ padding:"14px 16px" }}>
                  <div style={{ display:"flex", alignItems:"center", gap:"8px", marginBottom:"6px" }}>
                    <strong style={{ fontSize:"14px", flex:1 }}>{city.name}</strong>
                    <span className="activity-type-label" style={{ fontSize:"9px" }}>{city.tag}</span>
                  </div>
                  <p className="muted-text" style={{ fontSize:"12px", lineHeight:"1.5" }}>{city.desc}</p>
                </div>
              ))}
            </div>

            <h3 style={{ marginBottom:"12px" }}>The Four Mercenary Guilds</h3>
            <p className="muted-text" style={{ fontSize:"13px", lineHeight:"1.6", marginBottom:"12px" }}>
              When the Republic fell, its unified protection collapsed too. Mercenary guilds rose to fill the gap — neutral contractors not bound to any city-state. Your OC works within one of these four.
            </p>
            <div style={{ display:"grid", gridTemplateColumns:"repeat(auto-fill, minmax(200px,1fr))", gap:"10px", marginBottom:"24px" }}>
              {[
                { name:"Gilded Index",   desc:"Knowledge, magic, and structured power. They preserve what others let decay.", role:"Scholar / Arcanist / Battlemage" },
                { name:"Black Spur",     desc:"Hunters, assassins, and trackers. If a target needs to be found, they will find it.", role:"Hunter / Assassin / Tracker" },
                { name:"Iron Covenant",  desc:"Protection, escort, and defense. If someone hires them, that person lives.", role:"Guard / Escort / Defender" },
                { name:"Ragged Signal",  desc:"Influence, information, and control. They don't take territory — they take knowledge.", role:"Spy / Smuggler / Manipulator" },
              ].map(g => (
                <div key={g.name} className="card" style={{ padding:"14px 16px" }}>
                  <strong style={{ fontSize:"13px", display:"block", marginBottom:"6px" }}>{g.name}</strong>
                  <p className="muted-text" style={{ fontSize:"12px", lineHeight:"1.5", marginBottom:"6px" }}>{g.desc}</p>
                  <p style={{ fontSize:"11px", color:"#2f6f73" }}>{g.role}</p>
                </div>
              ))}
            </div>

            <h3 style={{ marginBottom:"12px" }}>Magic & Source</h3>
            <div className="card" style={{ padding:"16px", marginBottom:"20px" }}>
              <p style={{ fontSize:"13px", color:"#555", lineHeight:"1.7", marginBottom:"10px" }}>
                Magic is drawn from <strong>Source</strong> — an ever-present primordial energy permeating the world. Most people have dormant mana circuits but can't actively use them. Those who can are uncommon and viewed with cautious wariness. Magic is losing ground to science and industry. Only three places formally teach it: the Academy in Lumenhold, the Imperial College in the Citadel, and Brassmere's independent labs.
              </p>
              <p style={{ fontSize:"13px", color:"#555", lineHeight:"1.7", marginBottom:"10px" }}>
                <strong>Source Wells</strong> are areas of intense magical energy that warp their environments. Found within them are <strong>Bondroot Trees</strong> — ancient trees that can bond with pre-pubescent humans, severing their Source connection but granting them a living Source Beast companion for life. These people become <strong>Beasthandlers</strong>.
              </p>
              <p style={{ fontSize:"13px", color:"#555", lineHeight:"1.7" }}>
                The four elemental <strong>Forces</strong> (Water, Earth, Wind, Fire) are the safest way for mages to interact with Source — they act as interface channels, giving mages more control over the otherwise wild energy.
              </p>
            </div>

            <h3 style={{ marginBottom:"12px" }}>Technology Level</h3>
            <div style={{ display:"grid", gridTemplateColumns:"1fr 1fr", gap:"10px" }}>
              {[
                { label:"Present",  items:["Steam engines (widespread)","Railroads (primary inter-city travel)","Electricity (rare — Flywheel, Lumenhold, Cinder only)","Gasworks and gas lighting","Combustion engines (rare, restricted)","Revolvers and early firearms (custom-made, no real-world counterparts)","Skyrails (Citadel, Flywheel, Ashgate, High Sable only)"] },
                { label:"Absent",   items:["Planes or submarines","Complex or modern guns","Nuclear technology","Broadcast television (films exist; radio is common)","Antibiotics (disinfectants do exist)","Phones (pay phones in major cities; no inter-city calls)"] },
              ].map(section => (
                <div key={section.label} className="card" style={{ padding:"14px 16px" }}>
                  <strong style={{ fontSize:"13px", display:"block", marginBottom:"8px", color: section.label === "Present" ? "#2f6f73" : "#888" }}>
                    {section.label}
                  </strong>
                  {section.items.map(item => (
                    <p key={item} style={{ fontSize:"12px", color:"#555", marginBottom:"5px", display:"flex", gap:"8px" }}>
                      <span style={{ color: section.label === "Present" ? "#2f6f73" : "#ccc", flexShrink:0 }}>{section.label === "Present" ? "✓" : "✗"}</span>
                      {item}
                    </p>
                  ))}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* ══════════════════════════════════════════════════
            SERVER GUIDE
        ══════════════════════════════════════════════════ */}
        {hubTab === "guide" && (
          <div style={{ maxWidth:"860px" }}>
            {[
              {
                title:"How XP Works", color:"#2f6f73",
                items:[
                  { label:"Earning XP",        desc:"XP comes from RP scenes, missions, and events. Submit posts via the RP Hub tab to claim XP. Staff reviews and approves." },
                  { label:"Spending XP",        desc:"XP is spent on stat raises and skill purchases. Use the XP Planner tab to plan. Submit via Skills tab or through tickets." },
                  { label:"Starting XP",        desc:"New OCs start with 600 XP. All 5 stats start at 10 for FREE — only points above 10 cost XP." },
                  { label:"XP Rates by Source", desc:"Mission XP varies by difficulty. RP scene XP is based on post count and word count. Events may have bonus XP." },
                  { label:"Beast XP",           desc:"Source Beasts have a separate XP pool. They earn a % of your XP through the Shared Experience OC skill (900 XP)." },
                ],
              },
              {
                title:"How Missions Work", color:"#8b4513",
                items:[
                  { label:"Finding Missions",   desc:"Check the Mission Board tab in Keystone. Missions list difficulty, party size, BST requirements, and rewards." },
                  { label:"BST",                desc:"Base Stat Total — the sum of all your core stats. Used to match you to appropriate missions." },
                  { label:"Signing Up",         desc:"Sign up via Keystone. Some missions have a priority window for specific guilds before opening to all." },
                  { label:"Rewards",            desc:"Missions pay out currency and XP. Staff posts results after the mission concludes." },
                  { label:"Active Missions",    desc:"You may have a limited number of active missions at once. Check your current count before signing up." },
                ],
              },
              {
                title:"Combat Basics", color:"#6b4c8b",
                items:[
                  { label:"Action Economy",     desc:"Each character has Actions, Reactions, Bonus Actions, and Free Actions per turn. Skills like Adept add more." },
                  { label:"Injury Tiers",       desc:"T1 (minor scratch) → T5 (critical / life-threatening). Source Beasts have half the injury capacity of their OC." },
                  { label:"Clashing",           desc:"Direct combat exchanges. Your output is compared to your opponent's reaction to determine damage." },
                  { label:"Safe Output Limit",  desc:"Mages: there's a cap on how much magical power you can output before taking self-damage. Fortified Circuits helps." },
                  { label:"Combat Calculator",  desc:"Use the Combat Calculator tab in Keystone to calculate derived stats, check formulas, and track fights." },
                ],
              },
              {
                title:"How to Submit Things", color:"#3d7a3d",
                items:[
                  { label:"New OC",             desc:"Fill out the OC Draft Template Google Doc → link it in #oc-submissions → open a ticket. Staff approves before you can RP." },
                  { label:"Skill Purchases",    desc:"Skills tab in Keystone → find skill → click Purchase. Staff approves and XP is deducted automatically." },
                  { label:"Stat Increases",     desc:"XP Planner tab → set target stats → submit. Staff approves and XP is deducted." },
                  { label:"Spells (Mages)",     desc:"Design your spell using the Spell Template → submit via ticket → wait for approval. You CANNOT cast until approved." },
                  { label:"Crafted Items",      desc:"Forgeborn: catalog items in your Player Journal. Submit via the Shop tab in Keystone." },
                  { label:"Source Beast Skills",desc:"Beast Skills are currently locked pending a balance pass. Plan your path but hold the XP until they release." },
                ],
              },
              {
                title:"Key Channels & Resources", color:"#b8721a",
                items:[
                  { label:"#rules",             desc:"Read before doing anything else." },
                  { label:"#mentor",            desc:"Ask staff or veteran players for help. No question is too basic here." },
                  { label:"#oc-submissions",    desc:"Submit your OC sheet for staff approval." },
                  { label:"#skill-purchases",   desc:"Or use the Skills tab in Keystone directly — it handles the process automatically." },
                  { label:"#spell-submissions", desc:"Submit new spells for approval. Required before use." },
                  { label:"Keystone (this site)",desc:"OC dashboard, XP planner, inventory, skills, shops, combat calculator, missions — all here." },
                ],
              },
            ].map(section => (
              <div key={section.title} className="card" style={{ marginBottom:"14px", padding:0, overflow:"hidden" }}>
                <div style={{ padding:"13px 16px", borderBottom:"1px solid #e0d4c4", borderLeft:`4px solid ${section.color}` }}>
                  <strong style={{ fontSize:"15px" }}>{section.title}</strong>
                </div>
                <div style={{ padding:"14px 16px" }}>
                  {section.items.map(item => (
                    <div key={item.label} style={{ display:"flex", gap:"12px", fontSize:"13px", marginBottom:"10px" }}>
                      <strong style={{ flexShrink:0, width:"155px", color:"#2c241e" }}>{item.label}</strong>
                      <span style={{ color:"#555", lineHeight:"1.55" }}>{item.desc}</span>
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        )}

      </div>
    </section>
  );
}

/*
────────────────────────────────────────────────────────────
WIRING CHECKLIST
────────────────────────────────────────────────────────────
frontend/src/main.tsx

1. IMPORT (top of file):
   import GettingStartedDashboard from "./components/GettingStartedDashboard";

2. LUCIDE IMPORT — add BookOpen to line 3:
   import { BookOpen, Calculator, ... } from "lucide-react";

3. TAB TYPE (line 24) — add "getting_started":
   type Tab = "home" | "getting_started" | "activity" | ...

4. TABS ARRAY (~line 156) — add after "home":
   ["getting_started", BookOpen, "Getting Started"],

5. RENDER (~line 264) — add after the home block:
   {tab === "getting_started" && (
     <GettingStartedDashboard discordId={discordId} jump={setTab} />
   )}

backend/app/routes/permissions.py

6. PLAYER_TABS — add at the top:
   PLAYER_TABS = [
     "getting_started",
     "dashboard",
     ...
   ]
────────────────────────────────────────────────────────────
*/
