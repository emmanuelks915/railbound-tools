"""
apply_enhance2.py
==================
Appends railbound_enhance2.css to the END of frontend/src/styles.css.
Run from your repo root:
    python apply_enhance2.py
"""
import shutil
from pathlib import Path

ROOT = Path(".")
SRC = Path(__file__).parent / "railbound_enhance2.css"
STYLES = ROOT / "frontend" / "src" / "styles.css"
MARKER = "/* railbound_enhance2 — loaded */"

if not STYLES.exists():
    print(f"ERROR: Could not find {STYLES}. Are you in the repo root?")
    raise SystemExit(1)

content = STYLES.read_text(encoding="utf-8")

if MARKER in content:
    print("  Already applied — nothing to do.")
    raise SystemExit(0)

shutil.copy2(STYLES, STYLES.with_suffix(".css.bak2"))
print("  Backed up styles.css → styles.css.bak2")

STYLES.write_text(content.rstrip() + "\n\n" + MARKER + "\n" + SRC.read_text(encoding="utf-8"), encoding="utf-8")

print("  Done! What was added:")
print("    • Syne font on h1 (hero title only)")
print("    • Hero scale-in animation + deeper hover shadow")
print("    • Active tab teal glow, inactive tab hover lift")
print("    • Teal glow + lift on all primary buttons")
print("    • Cards lift + deepen shadow on hover")
print("    • Item/request cards lift + left border by status")
print("    • Summary stat boxes get teal top bar on hover")
print("    • Stat strip hover lift with teal glow")
print("    • List buttons slide right on hover")
print("    • Teal focus ring on all inputs/selects")
print("    • Staggered fadeUp on item lists")
print("    • Custom scrollbar in beige theme colors")
print()
print("  Next:")
print("    git add -A")
print("    git commit -m \"feat: visual polish v2\"")
print("    git push origin main")
