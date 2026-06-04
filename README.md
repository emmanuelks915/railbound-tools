# Repair Staff Trait Grant Component v4

This fixes the build error:

```txt
Unexpected token at {!embedded ? (
```

Instead of trying to repair the broken JSX fragment, this patch rewrites the entire `StaffTraitGrantCard` component with a clean known-good version.

## What it does

```txt
- replaces broken StaffTraitGrantCard component
- keeps Grant / Remove Trait Only inside Staff Action Center
- passes maintenanceForm.character_id into the trait tool
- removes duplicate OC picker when embedded
- removes request-note-block wrapper when embedded
```

## Run

```powershell
cd C:\Users\emman\OneDrive\Documents\railbound-tools-starter

Expand-Archive -Path "$env:USERPROFILE\Downloads\repair_staff_trait_grant_component_v4_patch.zip" -DestinationPath . -Force
python patch_repair_staff_trait_grant_component_v4.py
```

Then:

```powershell
cd frontend
npm run build
```

Commit:

```powershell
cd ..
git add frontend/src/main.tsx
git commit -m "Repair staff trait grant component"
git push
```
