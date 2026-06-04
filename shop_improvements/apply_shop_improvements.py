"""
apply_shop_improvements.py
===========================
Runs both shop improvement patches in order.
Run from railbound-tools-starter/ folder:
    python apply_shop_improvements.py
"""
import subprocess, sys
from pathlib import Path

def run(script):
    print(f"\n{'─'*55}")
    print(f"  Running: {script}")
    print('─'*55)
    result = subprocess.run([sys.executable, script])
    if result.returncode != 0:
        print(f"\n  ❌ {script} failed. Fix above error before continuing.")
        raise SystemExit(result.returncode)

if not Path("backend").exists() or not Path("frontend").exists():
    print("ERROR: Run from railbound-tools-starter/ folder.")
    raise SystemExit(1)

print("=" * 55)
print("  Shop Improvements — Backend + Frontend")
print("=" * 55)

run("fix_shop_owner_deny_refund.py")
run("fix_shop_frontend_ux.py")

print()
print("=" * 55)
print("  All done! Commit and push:")
print()
print('  git add -A')
print('  git commit -m "fix/ux: shop deny refund + order UX improvements"')
print('  git push origin main')
print("=" * 55)
