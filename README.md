# Add Shop Item Delete v1

Adds true permanent deletion for shop items.

## Backend

Adds:

```txt
DELETE /api/shop-owner/items/{item_id}
```

It checks that the logged-in user can manage the item’s storefront before deleting.

## Frontend

Adds a **Delete Item** button while editing an item.

```txt
Edit Item → Delete Item → confirmation prompt → item removed from shop_items
```

## Run

```powershell
cd C:\Users\emman\OneDrive\Documents\railbound-tools-starter

Expand-Archive -Path "$env:USERPROFILE\Downloads\add_shop_item_delete_v1_patch.zip" -DestinationPath . -Force
python patch_add_shop_item_delete_v1.py
```

Then:

```powershell
cd frontend
npm run build
```

Commit:

```powershell
cd ..
git add backend/app/routes/shop_owner.py frontend/src/main.tsx
git commit -m "Add shop item deletion"
git push
```
