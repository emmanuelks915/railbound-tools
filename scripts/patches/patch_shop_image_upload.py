
from __future__ import annotations

from pathlib import Path


ROOT = Path.cwd()
BACKEND = ROOT / "backend" / "app"
FRONTEND_MAIN = ROOT / "frontend" / "src" / "main.tsx"
STYLES = ROOT / "frontend" / "src" / "styles.css"
CONFIG = BACKEND / "config.py"
SHOPS = BACKEND / "routes" / "shops.py"
REQS = ROOT / "backend" / "requirements.txt"
ENV_EXAMPLE = ROOT / "backend" / ".env.example"
DATABASE_DIR = ROOT / "database"


SQL = '''-- 004_shop_images_storage_bucket.sql
-- Public bucket for shop listing images uploaded through Railbound Tools.

insert into storage.buckets (
  id,
  name,
  public,
  file_size_limit,
  allowed_mime_types
)
values (
  'shop-images',
  'shop-images',
  true,
  8388608,
  array['image/png', 'image/jpeg', 'image/webp', 'image/gif']
)
on conflict (id) do update
set
  public = excluded.public,
  file_size_limit = excluded.file_size_limit,
  allowed_mime_types = excluded.allowed_mime_types;
'''


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def write(path: Path, text: str):
    path.write_text(text, encoding="utf-8")


def backup(path: Path):
    backup_path = path.with_suffix(path.suffix + ".image_upload.bak")
    if not backup_path.exists() and path.exists():
        backup_path.write_text(path.read_text(encoding="utf-8"), encoding="utf-8")


def add_import_name(text: str, from_module: str, name: str) -> str:
    line_prefix = f"from {from_module} import "
    lines = text.splitlines()

    for i, line in enumerate(lines):
        if line.startswith(line_prefix):
            imported = [part.strip() for part in line[len(line_prefix):].split(",")]
            if name not in imported:
                imported.append(name)
                lines[i] = line_prefix + ", ".join(imported)
            return "\n".join(lines) + ("\n" if text.endswith("\n") else "")

    insert_index = 0
    for i, line in enumerate(lines):
        if line.startswith("from __future__"):
            insert_index = i + 1
        elif line.startswith("import ") or line.startswith("from "):
            insert_index = i + 1

    lines.insert(insert_index, f"{line_prefix}{name}")
    return "\n".join(lines) + ("\n" if text.endswith("\n") else "")


def add_plain_import(text: str, line_to_add: str) -> str:
    if line_to_add in text:
        return text

    lines = text.splitlines()
    insert_index = 0

    for i, line in enumerate(lines):
        if line.startswith("from __future__"):
            insert_index = i + 1
        elif line.startswith("import ") or line.startswith("from "):
            insert_index = i + 1

    lines.insert(insert_index, line_to_add)
    return "\n".join(lines) + ("\n" if text.endswith("\n") else "")


def patch_config():
    text = read(CONFIG)
    original = text
    backup(CONFIG)

    if "supabase_storage_bucket" not in text:
        marker = '    supabase_service_role_key: str | None = None\n'
        if marker not in text:
            marker = '    supabase_secret_key: str | None = None\n'

        if marker not in text:
            raise RuntimeError("Could not find Supabase key settings in backend/app/config.py.")

        text = text.replace(marker, marker + '    supabase_storage_bucket: str = "shop-images"\n', 1)

    if text != original:
        write(CONFIG, text)
        print("Patched backend/app/config.py")
    else:
        print("backend/app/config.py already patched")


def patch_requirements():
    if not REQS.exists():
        print("backend/requirements.txt not found; skipping requirements patch")
        return

    text = read(REQS)
    original = text

    if "python-multipart" not in text.lower():
        if not text.endswith("\n"):
            text += "\n"
        text += "python-multipart\n"

    if text != original:
        backup(REQS)
        write(REQS, text)
        print("Patched backend/requirements.txt")
    else:
        print("backend/requirements.txt already has python-multipart")


def patch_env_example():
    if not ENV_EXAMPLE.exists():
        print("backend/.env.example not found; skipping env example patch")
        return

    text = read(ENV_EXAMPLE)
    original = text

    if "SUPABASE_STORAGE_BUCKET" not in text:
        if not text.endswith("\n"):
            text += "\n"
        text += "SUPABASE_STORAGE_BUCKET=shop-images\n"

    if text != original:
        backup(ENV_EXAMPLE)
        write(ENV_EXAMPLE, text)
        print("Patched backend/.env.example")
    else:
        print("backend/.env.example already patched")


def patch_sql():
    DATABASE_DIR.mkdir(exist_ok=True)
    sql_path = DATABASE_DIR / "004_shop_images_storage_bucket.sql"

    if not sql_path.exists():
        sql_path.write_text(SQL, encoding="utf-8")
        print("Created database/004_shop_images_storage_bucket.sql")
    else:
        print("database/004_shop_images_storage_bucket.sql already exists")


def patch_shops_backend():
    text = read(SHOPS)
    original = text
    backup(SHOPS)

    text = add_plain_import(text, "from uuid import uuid4")
    text = add_plain_import(text, "import httpx")
    text = add_import_name(text, "fastapi", "File")
    text = add_import_name(text, "fastapi", "UploadFile")
    text = add_plain_import(text, "from app.config import get_settings")

    helper = '''
_ALLOWED_SHOP_IMAGE_TYPES = {
    "image/png": "png",
    "image/jpeg": "jpg",
    "image/webp": "webp",
    "image/gif": "gif",
}

_MAX_SHOP_IMAGE_BYTES = 8 * 1024 * 1024


def _storage_public_url(bucket: str, object_path: str) -> str:
    settings = get_settings()
    base_url = settings.supabase_url.rstrip("/")
    return f"{base_url}/storage/v1/object/public/{bucket}/{object_path}"


def _storage_upload_url(bucket: str, object_path: str) -> str:
    settings = get_settings()
    base_url = settings.supabase_url.rstrip("/")
    return f"{base_url}/storage/v1/object/{bucket}/{object_path}"
'''

    if "_ALLOWED_SHOP_IMAGE_TYPES" not in text:
        marker = 'router = APIRouter(prefix="/api/shops", tags=["shops"])\n'
        if marker not in text:
            raise RuntimeError("Could not find shops router marker.")
        text = text.replace(marker, marker + helper + "\n", 1)

    route = '''
@router.post("/{company_id}/images")
def upload_shop_image(
    company_id: str,
    file: UploadFile = File(...),
    actor_discord_id: int | None = Depends(actor_from_header),
):
    actor = require_actor(actor_discord_id)
    sb = get_supabase()
    gid = get_guild_id()

    require_company_manager(sb, company_id, actor, min_rank=2)

    content_type = (file.content_type or "").split(";")[0].strip().lower()

    if content_type not in _ALLOWED_SHOP_IMAGE_TYPES:
        raise HTTPException(
            status_code=400,
            detail="Unsupported image type. Use PNG, JPG, WEBP, or GIF.",
        )

    data = file.file.read()

    if not data:
        raise HTTPException(status_code=400, detail="Image file is empty.")

    if len(data) > _MAX_SHOP_IMAGE_BYTES:
        raise HTTPException(status_code=400, detail="Image must be 8 MB or smaller.")

    settings = get_settings()
    bucket = settings.supabase_storage_bucket
    ext = _ALLOWED_SHOP_IMAGE_TYPES[content_type]
    object_path = f"shop-listings/{gid}/{company_id}/{uuid4()}.{ext}"

    headers = {
        "apikey": settings.supabase_admin_key,
        "Content-Type": content_type,
        "Cache-Control": "3600",
        "x-upsert": "false",
    }

    upload_url = _storage_upload_url(bucket, object_path)

    try:
        response = httpx.post(
            upload_url,
            content=data,
            headers=headers,
            timeout=30.0,
        )
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Image upload failed: {exc}") from exc

    if response.status_code >= 400:
        detail = response.text or "Image upload failed."
        raise HTTPException(status_code=400, detail=detail)

    public_url = _storage_public_url(bucket, object_path)

    return {
        "ok": True,
        "bucket": bucket,
        "path": object_path,
        "url": public_url,
        "content_type": content_type,
        "size_bytes": len(data),
    }

'''

    if 'def upload_shop_image(' not in text:
        marker = '@router.post("/{company_id}/items")'
        if marker not in text:
            raise RuntimeError("Could not find create shop item route marker.")
        text = text.replace(marker, route + "\n" + marker, 1)

    if text != original:
        write(SHOPS, text)
        print("Patched backend/app/routes/shops.py")
    else:
        print("backend/app/routes/shops.py already patched")


def patch_frontend():
    text = read(FRONTEND_MAIN)
    original = text
    backup(FRONTEND_MAIN)

    marker = '  const [message, setMessage] = useState("");\n  const [createOpen, setCreateOpen] = useState(true);'
    replacement = '  const [message, setMessage] = useState("");\n  const [uploadingImage, setUploadingImage] = useState(false);\n  const [createOpen, setCreateOpen] = useState(true);'

    if "uploadingImage" not in text:
        if marker not in text:
            raise RuntimeError("Could not find ShopDashboard message/createOpen state marker.")
        text = text.replace(marker, replacement, 1)

    upload_function = '''
  async function uploadListingImage(file: File | null) {
    if (!file) return;

    if (!shopId) {
      setMessage("Select a shop before uploading an image.");
      return;
    }

    setUploadingImage(true);
    setMessage("Uploading image...");

    const formData = new FormData();
    formData.append("file", file);

    try {
      const headers = new Headers();
      if (discordId) headers.set("X-Discord-Id", discordId);

      const response = await fetch(`${API_BASE}/api/shops/${shopId}/images`, {
        method: "POST",
        headers,
        body: formData,
      });

      const data = await response.json().catch(() => ({}));

      if (!response.ok) {
        throw new Error(data.detail || "Image upload failed.");
      }

      updateListingForm("image_url", data.url || "");
      setMessage("Image uploaded and attached to the listing.");
    } catch (error: any) {
      setMessage(error.message || "Image upload failed.");
    } finally {
      setUploadingImage(false);
    }
  }

'''

    if "uploadListingImage" not in text:
        marker = "  async function createListing() {"
        if marker not in text:
            raise RuntimeError("Could not find createListing function marker.")
        text = text.replace(marker, upload_function + marker, 1)

    old = '''                <label>
                  Image URL
                  <input value={listingForm.image_url} onChange={(e) => updateListingForm("image_url", e.target.value)} placeholder="https://..." />
                </label>'''

    new = '''                <label>
                  Image URL
                  <input value={listingForm.image_url} onChange={(e) => updateListingForm("image_url", e.target.value)} placeholder="https://..." />
                </label>
                <label>
                  Upload Image
                  <input
                    type="file"
                    accept="image/png,image/jpeg,image/webp,image/gif"
                    disabled={uploadingImage}
                    onChange={(e) => uploadListingImage(e.target.files?.[0] || null)}
                  />
                  <small>{uploadingImage ? "Uploading..." : "PNG, JPG, WEBP, or GIF. Max 8 MB."}</small>
                </label>'''

    if "Upload Image" not in text:
        if old not in text:
            raise RuntimeError("Could not find Image URL label block in ShopDashboard.")
        text = text.replace(old, new, 1)

    if text != original:
        write(FRONTEND_MAIN, text)
        print("Patched frontend/src/main.tsx")
    else:
        print("frontend/src/main.tsx already patched")

    css = read(STYLES)
    css_original = css

    css_append = '''
/* Shop image upload */

.shop-create-card input[type="file"] {
  padding: 0.7rem;
  background: rgba(255, 255, 255, 0.72);
}

.shop-create-card label small {
  color: rgba(44, 31, 22, 0.62);
}
'''

    if "Shop image upload" not in css:
        css = css.rstrip() + "\n\n" + css_append.strip() + "\n"

    if css != css_original:
        backup(STYLES)
        write(STYLES, css)
        print("Patched frontend/src/styles.css")
    else:
        print("frontend/src/styles.css already patched")


def main():
    patch_config()
    patch_requirements()
    patch_env_example()
    patch_sql()
    patch_shops_backend()
    patch_frontend()

    print("")
    print("Done.")
    print("Next: run database/004_shop_images_storage_bucket.sql in Supabase SQL Editor.")
    print("Then run pip install -r backend/requirements.txt and restart backend/frontend.")


if __name__ == "__main__":
    main()
