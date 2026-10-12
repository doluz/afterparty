"""The Afterparty Connector zip that this instance hands out.

The folder `extension/` lists only localhost, for local work. Users of a deployed
instance download `/afterparty-extension.zip`, built here on request with this
instance's PUBLIC_URL as the only origin allowed to ask for the Partiful session.
Run `scripts/package_extension.py` for the same build from the command line.
"""

from __future__ import annotations

import base64
import hashlib
import io
import json
import os
import zipfile
from functools import cache
from pathlib import Path
from urllib.parse import urlparse

LOCAL_ORIGINS = ["http://localhost/*", "http://127.0.0.1/*"]
POPUP_DEFAULT = "http://localhost:8080"


def source_dir() -> Path:
    """`extension/` at the repo root (or CONNECTOR_DIR, e.g. in a container)."""
    env = os.environ.get("CONNECTOR_DIR")
    return Path(env) if env else Path(__file__).resolve().parents[2] / "extension"


def manifest() -> dict:
    return json.loads((source_dir() / "manifest.json").read_text())


def extension_id(public_key_b64: str) -> str:
    """Chrome's id for an extension with this manifest `key`."""
    digest = hashlib.sha256(base64.b64decode(public_key_b64)).hexdigest()[:32]
    return "".join(chr(ord("a") + int(c, 16)) for c in digest)


@cache
def unpacked_id() -> str:
    """The id of the connector loaded from extension/ (fixed by its manifest key)."""
    try:
        key = manifest().get("key")
    except OSError:
        return ""
    return extension_id(key) if key else ""


def origins_for(public_url: str) -> list[str]:
    host = urlparse(public_url).hostname or ""
    if host in ("localhost", "127.0.0.1"):
        return list(LOCAL_ORIGINS)
    u = urlparse(public_url)
    return [f"{u.scheme}://{u.netloc}/*"]


def build_zip(public_url: str, *, store: bool = False) -> bytes:
    """A zip with this instance's origin. `store` drops the manifest key (the Chrome
    Web Store refuses it) and puts the files at the root, as the store wants."""
    src = source_dir()
    man = manifest()
    man["externally_connectable"]["matches"] = origins_for(public_url)
    if store:
        man.pop("key", None)
    root = Path("") if store else Path("afterparty-extension")
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr(str(root / "manifest.json"), json.dumps(man, indent=2))
        for f in sorted(src.rglob("*")):
            if not f.is_file() or f.name in ("manifest.json", ".DS_Store"):
                continue
            arc = str(root / f.relative_to(src))
            if f.name == "popup.html":
                z.writestr(arc, f.read_text().replace(POPUP_DEFAULT, public_url.rstrip("/")))
            else:
                z.write(f, arc)
    return buf.getvalue()


@cache
def instance_zip(public_url: str) -> bytes:
    return build_zip(public_url)
