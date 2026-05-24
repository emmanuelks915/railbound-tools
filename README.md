# OC Registry Guild Filter v1

Adds a player-facing filter to the OC Registry that uses the existing `affiliation` field as a mercenary guild filter.

## Why

Keystone does not currently track mercenary guild in a dedicated column, but most players put it in `affiliation`.

## What changes

The Citizen Registry gets a dropdown:

```txt
All guilds / affiliations
No affiliation listed
<unique affiliation values pulled from the registry>
```

The roster then only shows OCs whose `affiliation` matches the selected guild/affiliation.

## Run

```powershell
cd C:\Users\emman\OneDrive\Documents\railbound-tools-starter

Expand-Archive -Path "$env:USERPROFILE\Downloads\oc_registry_guild_filter_v1_patch.zip" -DestinationPath . -Force
python patch_oc_registry_guild_filter_v1.py
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
git commit -m "Add OC registry guild filter"
git push
```
