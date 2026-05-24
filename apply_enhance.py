"""
apply_enhance.py
=================
Appends railbound_enhance.css to the END of frontend/src/styles.css.
Does NOT touch your colors, fonts, or layout — only adds animations
and polish on top of your existing design.

Run from project root:
    python apply_enhance.py
"""

import shutil
from pathlib import Path

ROOT = Path(".")
ENHANCE_SRC = Path(__file__).parent / "railbound_enhance.css"
STYLES = ROOT / "frontend" / "src" / "styles.css"
MARKER = "/* railbound_enhance — loaded */"

if not STYLES.exists():
    print(f"ERROR: Could not find {STYLES}")
    raise SystemExit(1)

content = STYLES.read_text(encoding="utf-8")

if MARKER in content:
    print("  Enhancement CSS already appended — nothing to do.")
    raise SystemExit(0)

enhance_css = ENHANCE_SRC.read_text(encoding="utf-8")

# Backup
backup = STYLES.with_suffix(".css.bak")
shutil.copy2(STYLES, backup)
print(f"  Backed up styles.css → {backup.name}")

# Append to end
STYLES.write_text(content.rstrip() + "\n\n" + MARKER + "\n" + enhance_css, encoding="utf-8")
print("  ✅ Enhancement CSS appended to styles.css")
print()
print("  What was added:")
print("    • Smooth fadeUp entrance for cards and list items (staggered)")
print("    • Hero section scale-in animation on load")
print("    • Hover lift + teal glow shadow on buttons")
print("    • Hover lift on cards, item cards, skill cards")
print("    • Activity timeline left-border color by type")
print("    • Skill card left-border state indicators")
print("    • Teal focus ring on all inputs/selects")
print("    • Pulse dot animation (.live-dot class)")
print("    • Shimmer skeleton class for loading states")
print("    • Smooth custom scrollbar in beige theme colors")
print("    • Mobile-safe (hover effects disabled on touch devices)")
print()
print("  Next:")
print("    git add -A")
print("    git commit -m \"feat: animation and polish enhancements\"")
print("    git push origin main")
