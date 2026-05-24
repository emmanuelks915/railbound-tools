from __future__ import annotations

from pathlib import Path


MAIN_PATH = Path("frontend/src/main.tsx")


def main() -> None:
    text = MAIN_PATH.read_text(encoding="utf-8")
    original = text

    # Backup once.
    backup_path = MAIN_PATH.with_suffix(".tsx.oc_skills_clean_display.bak")
    if not backup_path.exists():
        backup_path.write_text(text, encoding="utf-8")

    # Enrich pending requests with skill display names using the already-loaded catalog.
    old_pending_state = "    setSkillRequests(characterSkillData.requests || []);"
    new_pending_state = """    const enrichedRequests = (characterSkillData.requests || []).map((request: any) => {
      const skill = catalog.find((entry: any) => entry.skill_key === request.skill_key);

      return {
        ...request,
        skill_name: skill?.name || request.skill_key,
        tree: skill?.tree,
        tier: skill?.tier,
      };
    });

    setSkillRequests(enrichedRequests);"""

    if old_pending_state in text:
        text = text.replace(old_pending_state, new_pending_state, 1)

    # Remove the database key from owned skill rows.
    text = text.replace(
        """                      <strong>{skill.name || skill.skill_key}</strong>
                      <small>{skill.skill_key}</small>""",
        """                      <strong>{skill.name || skill.skill_key}</strong>""",
    )

    # Clean pending rows too: show the skill display name and remove request UUID.
    text = text.replace(
        """                      <strong>{request.skill_key}</strong>
                      <small>{request.request_id}</small>""",
        """                      <strong>{request.skill_name || request.skill_key}</strong>""",
    )

    if text != original:
        MAIN_PATH.write_text(text, encoding="utf-8")
        print("Patched frontend/src/main.tsx")
        print("Removed skill_key/request_id subtitles from OC owned skills panel.")
        print(f"Backup saved as {backup_path}")
    else:
        print("No changes made. The display may already be clean.")


if __name__ == "__main__":
    main()
