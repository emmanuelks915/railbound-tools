from __future__ import annotations

from pathlib import Path


MAIN_PATH = Path("frontend/src/main.tsx")
CSS_PATH = Path("frontend/src/styles.css")

UPLOAD_FUNCTION = '\n  async function uploadListingImage(file: File | null) {\n    if (!file) return;\n\n    if (!shopId) {\n      setMessage("Select a shop before uploading an image.");\n      return;\n    }\n\n    setUploadingImage(true);\n    setMessage("Uploading image...");\n\n    const formData = new FormData();\n    formData.append("file", file);\n\n    try {\n      const headers = new Headers();\n      if (discordId) headers.set("X-Discord-Id", discordId);\n\n      const response = await fetch(`${API_BASE}/api/shops/${shopId}/images`, {\n        method: "POST",\n        headers,\n        body: formData,\n      });\n\n      const data = await response.json().catch(() => ({}));\n\n      if (!response.ok) {\n        throw new Error(data.detail || "Image upload failed.");\n      }\n\n      updateListingForm("image_url", data.url || "");\n      setMessage("Image uploaded and attached to the listing.");\n    } catch (error: any) {\n      setMessage(error.message || "Image upload failed.");\n    } finally {\n      setUploadingImage(false);\n    }\n  }\n\n'
OLD_LABEL = '                <label>\n                  Image URL\n                  <input value={listingForm.image_url} onChange={(e) => updateListingForm("image_url", e.target.value)} placeholder="https://..." />\n                </label>'
NEW_LABEL = '                <label>\n                  Image URL\n                  <input value={listingForm.image_url} onChange={(e) => updateListingForm("image_url", e.target.value)} placeholder="https://..." />\n                </label>\n                <label>\n                  Upload Image\n                  <input\n                    type="file"\n                    accept="image/png,image/jpeg,image/webp,image/gif"\n                    disabled={uploadingImage}\n                    onChange={(e) => uploadListingImage(e.target.files?.[0] || null)}\n                  />\n                  <small>{uploadingImage ? "Uploading..." : "PNG, JPG, WEBP, or GIF. Max 8 MB."}</small>\n                </label>'
CSS_APPEND = '\n/* Shop image upload */\n\n.shop-create-card input[type="file"] {\n  padding: 0.7rem;\n  background: rgba(255, 255, 255, 0.72);\n}\n\n.shop-create-card label small {\n  color: rgba(44, 31, 22, 0.62);\n}\n'


def find_function_block(text: str, function_name: str) -> tuple[int, int]:
    start = text.find(f"function {function_name}(")
    if start == -1:
        raise RuntimeError(f"Could not find function {function_name}.")

    brace_start = text.find("{", start)
    if brace_start == -1:
        raise RuntimeError(f"Could not find opening brace for {function_name}.")

    depth = 0
    in_string: str | None = None
    escaped = False
    in_line_comment = False
    in_block_comment = False

    for i in range(brace_start, len(text)):
        ch = text[i]
        nxt = text[i + 1] if i + 1 < len(text) else ""

        if in_line_comment:
            if ch == "\n":
                in_line_comment = False
            continue

        if in_block_comment:
            if ch == "*" and nxt == "/":
                in_block_comment = False
            continue

        if in_string:
            if escaped:
                escaped = False
            elif ch == "\\":
                escaped = True
            elif ch == in_string:
                in_string = None
            continue

        if ch == "/" and nxt == "/":
            in_line_comment = True
            continue

        if ch == "/" and nxt == "*":
            in_block_comment = True
            continue

        if ch in ("'", '"', "`"):
            in_string = ch
            continue

        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return start, i + 1

    raise RuntimeError(f"Could not find closing brace for {function_name}.")


def patch_shop_dashboard(block: str) -> str:
    if "uploadingImage" not in block:
        message_line = '  const [message, setMessage] = useState("");\n'
        if message_line not in block:
            raise RuntimeError("Could not find message state inside ShopDashboard.")

        block = block.replace(
            message_line,
            message_line + '  const [uploadingImage, setUploadingImage] = useState(false);\n',
            1,
        )

    if "uploadListingImage" not in block:
        marker = "  async function createListing() {"
        if marker not in block:
            raise RuntimeError("Could not find createListing function in ShopDashboard.")
        block = block.replace(marker, UPLOAD_FUNCTION + marker, 1)

    if "Upload Image" not in block:
        if OLD_LABEL not in block:
            raise RuntimeError(
                "Could not find the Image URL label block. "
                "Your ShopDashboard layout changed, so patch manually around the Image URL field."
            )
        block = block.replace(OLD_LABEL, NEW_LABEL, 1)

    return block


def patch_css():
    css = CSS_PATH.read_text(encoding="utf-8")

    if "Shop image upload" in css:
        print("frontend/src/styles.css already has shop image upload CSS")
        return

    CSS_PATH.with_suffix(".css.image_upload.bak").write_text(css, encoding="utf-8")
    CSS_PATH.write_text(css.rstrip() + "\n\n" + CSS_APPEND.strip() + "\n", encoding="utf-8")
    print("Patched frontend/src/styles.css")


def main():
    text = MAIN_PATH.read_text(encoding="utf-8")
    start, end = find_function_block(text, "ShopDashboard")
    block = text[start:end]
    patched = patch_shop_dashboard(block)

    if patched != block:
        MAIN_PATH.with_suffix(".tsx.image_upload_manual.bak").write_text(text, encoding="utf-8")
        MAIN_PATH.write_text(text[:start] + patched + text[end:], encoding="utf-8")
        print("Patched frontend/src/main.tsx")
        print("Backup saved as frontend/src/main.tsx.image_upload_manual.bak")
    else:
        print("frontend/src/main.tsx already patched")

    patch_css()
    print("")
    print("Done. Now run the Supabase bucket SQL, install requirements, and restart backend/frontend.")


if __name__ == "__main__":
    main()
