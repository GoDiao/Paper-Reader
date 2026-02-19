from __future__ import annotations

import base64
import hashlib
import json
import os
import re
import urllib.parse
import urllib.request
import uuid
from pathlib import Path
from typing import Literal


def _multipart_formdata(fields: dict[str, str]) -> tuple[bytes, str]:
    boundary = f"----imagego{uuid.uuid4().hex}"
    lines: list[bytes] = []
    for k, v in fields.items():
        lines.append(f"--{boundary}".encode("utf-8"))
        lines.append(f'Content-Disposition: form-data; name="{k}"'.encode("utf-8"))
        lines.append(b"")
        lines.append(v.encode("utf-8"))
    lines.append(f"--{boundary}--".encode("utf-8"))
    lines.append(b"")
    body = b"\r\n".join(lines)
    content_type = f"multipart/form-data; boundary={boundary}"
    return body, content_type


def _resolve_imgbb_key(api_key: str | None) -> str:
    resolved = (api_key or "").strip()
    if not resolved:
        resolved = os.environ.get("IMGBB_API_KEY", "").strip()
    if not resolved:
        raise ValueError("IMGBB_API_KEY is required")
    return resolved


def upload_image_to_imgbb(*, api_key: str, image_bytes: bytes, expiration: int = 0) -> str:
    api_key = _resolve_imgbb_key(api_key)

    url = "https://api.imgbb.com/1/upload"
    query = {"key": api_key}
    if expiration:
        query["expiration"] = str(expiration)
    full_url = f"{url}?{urllib.parse.urlencode(query)}"

    image_b64 = base64.b64encode(image_bytes).decode("ascii")
    body, content_type = _multipart_formdata({"image": image_b64})

    req = urllib.request.Request(
        full_url,
        data=body,
        headers={"Content-Type": content_type},
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            payload = resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as e:
        payload = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"ImgBB upload failed: HTTP {e.code}: {payload}")

    data = json.loads(payload)
    if not isinstance(data, dict) or not data.get("success"):
        raise RuntimeError(f"ImgBB upload failed: {payload}")

    d = data.get("data") or {}
    if isinstance(d, dict):
        url = d.get("display_url") or d.get("url")
        if isinstance(url, str) and url.strip():
            return url

    raise RuntimeError(f"ImgBB upload succeeded but no URL returned: {payload}")


def rewrite_markdown_images_via_imgbb(
    *,
    markdown: str,
    md_dir: Path,
    api_key: str,
    expiration: int,
    cache_path: Path,
    on_missing: Literal["placeholder", "error"] = "placeholder",
) -> str:
    api_key = _resolve_imgbb_key(api_key)

    if not markdown:
        return markdown

    cache: dict[str, str] = {}
    if cache_path.exists():
        try:
            cache_obj = json.loads(cache_path.read_text(encoding="utf-8"))
            if isinstance(cache_obj, dict):
                cache = {str(k): str(v) for k, v in cache_obj.items() if isinstance(k, str) and isinstance(v, str)}
        except Exception:
            cache = {}

    pattern = r'!\[([^\]]*)\]\(([^)\s]+)(?:\s+"[^"]*")?\)'

    def repl(match: re.Match) -> str:
        alt = match.group(1) or ""
        url = match.group(2) or ""
        if url.startswith(("http://", "https://", "data:")):
            return match.group(0)

        rel = url.split("#", 1)[0].split("?", 1)[0]
        local_path = (md_dir / rel).resolve()
        if not local_path.exists() or not local_path.is_file():
            if on_missing == "error":
                raise FileNotFoundError(str(local_path))
            label = alt.strip() or "image"
            return f"*Image: {label} ({url})*"

        image_bytes = local_path.read_bytes()
        digest = hashlib.sha256(image_bytes).hexdigest()
        cache_key = f"sha256:{digest}:exp:{expiration}:name:{local_path.name}"

        uploaded = cache.get(cache_key)
        if not uploaded:
            uploaded = upload_image_to_imgbb(api_key=api_key, image_bytes=image_bytes, expiration=expiration)
            cache[cache_key] = uploaded
            try:
                cache_path.write_text(json.dumps(cache, ensure_ascii=False, indent=2), encoding="utf-8")
            except Exception:
                pass

        return f"![{alt}]({uploaded})"

    return re.sub(pattern, repl, markdown)
