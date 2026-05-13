# Shop Image Upload Patch

Adds Supabase Storage image upload to shop listings.

## Commands from project root

```powershell
Expand-Archive -Path "$env:USERPROFILE\Downloads\shop_image_upload_patch.zip" -DestinationPath . -Force
python patch_shop_image_upload.py
```

## Supabase step

Run the SQL file this patch creates:

```txt
database/004_shop_images_storage_bucket.sql
```

It creates/updates a public `shop-images` bucket with an 8 MB limit.

## Install backend dependency and restart

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

## Frontend

```powershell
cd frontend
npm run dev
```

## Test

Go to:

```txt
Shops → Create Listing → Upload Image
```

The upload should populate the Image URL field and show in preview.

## Commit

```powershell
git add backend/app/config.py backend/app/routes/shops.py backend/requirements.txt backend/.env.example database/004_shop_images_storage_bucket.sql frontend/src/main.tsx frontend/src/styles.css
git commit -m "Add shop image uploads"
git push
```
