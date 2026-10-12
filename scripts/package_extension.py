"""Zip the Afterparty Connector for an instance.

    uv run python scripts/package_extension.py out.zip --url https://afterparty.example.com
    uv run python scripts/package_extension.py out.zip --url https://afterparty.example.com --store

A running instance serves the same build at /afterparty-extension.zip, so you
need this only to publish the connector in the Chrome Web Store (--store drops
the manifest key and puts the files at the zip root).
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from afterparty.connector import build_zip, origins_for  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("out", type=Path)
    ap.add_argument("--url", default="http://localhost:8080", help="the instance's public URL")
    ap.add_argument("--store", action="store_true", help="build for the Chrome Web Store")
    args = ap.parse_args()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_bytes(build_zip(args.url, store=args.store))
    print(f"connector for {', '.join(origins_for(args.url))} -> {args.out}")


if __name__ == "__main__":
    main()
