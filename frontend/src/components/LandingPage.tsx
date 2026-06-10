import { useEffect, useRef, useState } from "react";

interface LandingPageProps {
  onLogin: () => void;
}

export default function LandingPage({ onLogin }: LandingPageProps) {
  const [scrolled, setScrolled] = useState(false);
  const heroRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 40);
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  return (
    <div className="rb-landing">

      {/* ── NAV ── */}
      <nav className={`rb-nav ${scrolled ? "rb-nav--scrolled" : ""}`}>
        <span className="rb-nav-logo">Railbound</span>
        <button className="rb-nav-login" onClick={onLogin}>
          Login with Discord
        </button>
      </nav>

      {/* ── HERO ── */}
      <div className="rb-hero" ref={heroRef}>
        <div className="rb-hero-bg">
          <img
            src="/hero-train.gif"
            alt=""
            aria-hidden="true"
            className="rb-hero-gif"
            onError={(e) => { (e.target as HTMLImageElement).style.display = "none"; }}
          />
          <div className="rb-hero-overlay" />
        </div>
        <div className="rb-hero-content">
          <p className="rb-eyebrow">Doranswyr · 1845 A.R.</p>
          <h1 className="rb-title">
            The Republic fell.<br />
            <em>The rails still run.</em>
          </h1>
          <p className="rb-hero-sub">
            Railbound is a literate collaborative roleplay set in the fractured continent of Doranswyr —
            where nine city-states compete for power, mercenary guilds fill the void, and the only
            thread holding civilization together is rail.
          </p>
          <div className="rb-hero-actions">
            <button className="rb-btn-primary" onClick={onLogin}>
              Board the train
              <span className="rb-btn-arrow">→</span>
            </button>
            <a
              href="#world"
              className="rb-btn-ghost"
              onClick={(e) => {
                e.preventDefault();
                document.getElementById("world")?.scrollIntoView({ behavior: "smooth" });
              }}
            >
              Explore the world
            </a>
          </div>
        </div>
        <div className="rb-hero-scroll-hint" aria-hidden="true">
          <span>scroll</span>
          <div className="rb-scroll-line" />
        </div>
      </div>

      {/* ── WORLD ── */}
      <section className="rb-section" id="world">
        <div className="rb-section-inner">
          <div className="rb-label">The setting</div>
          <h2 className="rb-section-title">A continent on the edge</h2>
          <p className="rb-section-body">
            Thirty years ago, General Vegard Ragon stormed the Senate and ended 1,815 years of
            Republic rule. What followed wasn't conquest — it was fracture. Each city-state seized
            its independence, raised its walls, and began competing for resources, knowledge, and
            survival. The railroads are the only thread left holding civilization together.
          </p>
          <div className="rb-tags">
            {["Steam & early electricity", "Source magic", "Mercenary guilds", "Political intrigue", "Industrial era", "Great dragons"].map(t => (
              <span key={t} className="rb-tag">{t}</span>
            ))}
          </div>
        </div>
      </section>

      {/* ── CITY-STATES ── */}
      <section className="rb-section rb-section--alt">
        <div className="rb-section-inner">
          <div className="rb-label">Nine city-states</div>
          <h2 className="rb-section-title">Where will your story begin?</h2>
          <p className="rb-section-body">
            Every city-state has its own government, culture, laws, and secrets. Your character's
            home shapes who they are and who they'll become.
          </p>
          <div className="rb-cities-grid">
            {[
              { name: "Lumenhold", tag: "Knowledge & magic", detail: "A sprawling academy-city in the Red Desert. Ruled by the Illuminated Conclave through grants and permits, not force." },
              { name: "Gearford", tag: "Industry & labor", detail: "A city that rewards effort and punishes stagnation. Build, fix, or improve — or find another city." },
              { name: "Flywheel", tag: "Hydroelectric power", detail: "Built on the Grand Wheel dam. Governed by a technocratic meritocracy. The most advanced city in Doranswyr." },
              { name: "Ashgate", tag: "Trade & shadows", detail: "A crossroads city of commerce and quiet ambition. The Vaelor dynasty has ruled here longer than memory." },
              { name: "Thornwick", tag: "Frontier & beasts", detail: "Where civilization meets the Blackwood. Hunters, wardens, and beasthandlers call this city home." },
              { name: "Cinder", tag: "Smithing & resilience", detail: "Built from the ashes of Cinderfell. King Zamor rebuilt it through kindness and industrial ingenuity." },
              { name: "High Sable", tag: "Fortress & discipline", detail: "Carved into a cliff face. Survival comes from order and preparedness here — not comfort." },
              { name: "Morthand", tag: "Faith & isolation", detail: "The most reclusive city in Doranswyr. The Covenant of the Veiled God controls everything." },
              { name: "The Citadel", tag: "Empire reborn", detail: "The old capital, still standing. Ragon rules now, and the middle class has never had it better." },
            ].map(c => (
              <div key={c.name} className="rb-city-card">
                <div className="rb-city-name">{c.name}</div>
                <div className="rb-city-tag">{c.tag}</div>
                <div className="rb-city-detail">{c.detail}</div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── GUILDS ── */}
      <section className="rb-section">
        <div className="rb-section-inner">
          <div className="rb-label">Mercenary guilds</div>
          <h2 className="rb-section-title">The world's only neutral power</h2>
          <p className="rb-section-body">
            When the Republic fell, its protection fell with it. Four guilds rose to fill the gap —
            not bound to any city, loyal only to contract. They exist between order and chaos, between
            law and necessity.
          </p>
          <div className="rb-guilds-grid">
            {[
              {
                name: "The Gilded Index",
                role: "Knowledge · Magic · Structured power",
                body: "They watched archives burn and responded by reclaiming everything others abandoned. They preserve what nations cannot."
              },
              {
                name: "The Black Spur",
                role: "Hunters · Assassins · Trackers",
                body: "Formed when criminals slipped through the cracks of the new world order. If you're a target, they will eventually find you."
              },
              {
                name: "The Iron Covenant",
                role: "Protection · Escort · Defense",
                body: "Veterans and loyal retainers who believed someone should stand between the people and the wilderness. If they're hired, you live."
              },
              {
                name: "The Ragged Signal",
                role: "Influence · Information · Control",
                body: "They don't take territory by occupying it — they ensure nothing moves without their knowledge. Secrets are their currency."
              },
            ].map(g => (
              <div key={g.name} className="rb-guild-card">
                <div className="rb-guild-name">{g.name}</div>
                <div className="rb-guild-role">{g.role}</div>
                <div className="rb-guild-body">{g.body}</div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── TOOLS ── */}
      <section className="rb-section rb-section--alt">
        <div className="rb-section-inner">
          <div className="rb-label">Keystone Tools</div>
          <h2 className="rb-section-title">Your character, fully realized</h2>
          <p className="rb-section-body">
            Railbound runs a custom stat and progression system tracked through a purpose-built
            website. No spreadsheets, no manual DMs. Everything lives in one place.
          </p>
          <div className="rb-tools-grid">
            {[
              { icon: "📋", title: "OC dashboard", body: "Stats, XP, skills, and progression tracked in real time." },
              { icon: "🎒", title: "Inventory & loadouts", body: "Manage items, build scene loadouts, track carry capacity." },
              { icon: "🏪", title: "Market district", body: "NPC and player shops, purchase requests, order tracking." },
              { icon: "⚔️", title: "Combat calculator", body: "Derived stats, attack math, and injury tracking on the fly." },
              { icon: "🌿", title: "Loyal companion", body: "Track your bonded beast's stats and skills." },
              { icon: "✨", title: "Skills & crafting", body: "Skill trees, XP costs, prerequisites, and recipe links." },
            ].map(t => (
              <div key={t.title} className="rb-tool-card">
                <div className="rb-tool-icon">{t.icon}</div>
                <div className="rb-tool-title">{t.title}</div>
                <div className="rb-tool-body">{t.body}</div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── DRAGONS ── */}
      <section className="rb-section">
        <div className="rb-section-inner">
          <div className="rb-label">The nine great dragons</div>
          <h2 className="rb-section-title">Ancient forces, not gods</h2>
          <p className="rb-section-body">
            They existed before the Republic and will remain long after everything else is gone.
            Most people know them only by title — fragments of truth shaped into legend over centuries.
          </p>
          <div className="rb-dragons-grid">
            {[
              { title: "The Youngest", name: "Zephyraxis", note: "Herbivorous. Gentle. Animals flock to its wake." },
              { title: "The Largest", name: "Thaloryx", note: "Its wingspan has never been observed in full. Sailors mistake its back for islands." },
              { title: "The Strongest", name: "Farissax", note: "Many heads, each its own mind. Even other dragons give it distance." },
              { title: "The Kindest", name: "Eldurgran", note: "The one most likely to understand humanity. Found at the center of the continent." },
              { title: "The Fastest", name: "Aetherisyl", note: "It appears. Compasses fail. Then it's gone before you're certain it was ever there." },
              { title: "The Loneliest", name: "Fuliginosus", note: "Deep in the ocean trenches. Hasn't spoken to a true equal in centuries." },
              { title: "The Wisest", name: "Tenebreia", note: "Disappeared 70 years ago. Even other dragons don't know what happened." },
              { title: "The Twin Oldest", name: "Aetherion & Netherion", note: "The first. Rarely seen. When they appear together, change follows." },
            ].map(d => (
              <div key={d.name} className="rb-dragon-card">
                <div className="rb-dragon-title">{d.title}</div>
                <div className="rb-dragon-name">{d.name}</div>
                <div className="rb-dragon-note">{d.note}</div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── CTA ── */}
      <section className="rb-cta">
        <div className="rb-cta-inner">
          <p className="rb-eyebrow" style={{ textAlign: "center", marginBottom: "1rem" }}>Ready?</p>
          <h2 className="rb-cta-title">The next train leaves when you do.</h2>
          <p className="rb-cta-sub">
            Create your character. Pick your city. Choose your guild.<br />
            The world is fractured. Where you fit in is up to you.
          </p>
          <button className="rb-btn-primary rb-btn-large" onClick={onLogin}>
            Login with Discord
            <span className="rb-btn-arrow">→</span>
          </button>
          <p className="rb-cta-note">18+ · Literate text-based roleplay · Discord required</p>
        </div>
      </section>

      {/* ── FOOTER ── */}
      <footer className="rb-footer">
        <span>Railbound · Doranswyr · 1845 A.R.</span>
        <span>Keystone Tools by the Railbound staff team</span>
      </footer>

    </div>
  );
}
