from pathlib import Path
import re

MAIN_PATH = Path("frontend/src/main.tsx")
CSS_PATH = Path("frontend/src/styles.css")
COMPONENT_PATH = Path("ActivityDashboard_component.tsx")
CSS_SOURCE_PATH = Path("activity_log_css_append.css")


def main():
    text = MAIN_PATH.read_text(encoding="utf-8")
    original = text

    activity_component = COMPONENT_PATH.read_text(encoding="utf-8")
    css_append = CSS_SOURCE_PATH.read_text(encoding="utf-8")

    tab_match = re.search(r'type Tab = ([^;]+);', text)
    if not tab_match:
        raise RuntimeError("Could not find type Tab union.")

    if '"activity"' not in tab_match.group(1):
        old_union = tab_match.group(0)
        new_union = old_union.replace('"home"', '"home" | "activity"', 1)
        text = text.replace(old_union, new_union, 1)

    if '["activity", ClipboardList, "Activity"]' not in text:
        marker = '    ["home", Home, "Dashboard"],'
        if marker not in text:
            raise RuntimeError("Could not find Dashboard tab marker.")
        text = text.replace(
            marker,
            marker + '\n    ["activity", ClipboardList, "Activity"],',
            1,
        )

    if 'tab === "activity"' not in text:
        marker = '      {tab === "planner" && <Planner'
        if marker not in text:
            raise RuntimeError("Could not find Planner render marker.")
        text = text.replace(
            marker,
            '      {tab === "activity" && <ActivityDashboard discordId={discordId} />}\n' + marker,
            1,
        )

    if "function ActivityDashboard" not in text:
        marker_candidates = [
            "function RpHubDashboard(",
            "function StaffQueue(",
            "function DerivedStatsCalculator(",
        ]

        marker = next((candidate for candidate in marker_candidates if candidate in text), None)

        if marker is None:
            raise RuntimeError("Could not find component marker to insert ActivityDashboard.")

        text = text.replace(marker, activity_component.rstrip() + "\n\n" + marker, 1)

    if text != original:
        MAIN_PATH.with_suffix(".tsx.activity_log.bak").write_text(original, encoding="utf-8")
        MAIN_PATH.write_text(text, encoding="utf-8")
        print("Patched Activity page into frontend/src/main.tsx")
        print("Backup saved as frontend/src/main.tsx.activity_log.bak")
    else:
        print("frontend/src/main.tsx already had Activity pieces")

    css = CSS_PATH.read_text(encoding="utf-8")
    if "Activity Log" not in css:
        CSS_PATH.write_text(css.rstrip() + "\n\n" + css_append.strip() + "\n", encoding="utf-8")
        print("Appended Activity CSS")
    else:
        print("Activity CSS already present")


if __name__ == "__main__":
    main()
