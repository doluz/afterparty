#!/usr/bin/env python3
"""Command-line client for the Afterparty API. Python 3.9+, standard library only.

Configuration (flags win over environment variables):

    AFTERPARTY_URL    the instance, default http://localhost:8080
    AFTERPARTY_AUTH   the Authorization header value: "Bearer <token>" from
                      Settings > API access for agents, or "Dev <email>" in local mode
    AFTERPARTY_EMAIL  local mode shortcut: same as AFTERPARTY_AUTH="Dev <email>"

Examples:

    afterparty.py stats
    afterparty.py people --cluster founder --repeat --all
    afterparty.py export founders.csv --cluster founder --social linkedin
    afterparty.py sync --wait
    afterparty.py follow-up <person_id> contacted --note "Coffee on Friday"

Every command prints JSON on stdout, except `export`, which writes a CSV file.
Errors go to stderr with a non-zero exit code.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

CLUSTERS = (
    "founder",
    "investor",
    "engineering",
    "product",
    "design",
    "gtm_growth",
    "other",
    "unknown",
)
SOCIALS = ("any", "linkedin", "twitter", "instagram")
FOLLOW_UPS = ("none", "todo", "contacted", "skip")


class Client:
    def __init__(self, url: str, auth: str | None) -> None:
        self.url = url.rstrip("/")
        self.auth = auth

    def request(self, method: str, path: str, body: dict | None = None, raw: bool = False):
        data = json.dumps(body).encode() if body is not None else None
        req = urllib.request.Request(self.url + path, data=data, method=method)
        if self.auth:
            req.add_header("Authorization", self.auth)
        if data is not None:
            req.add_header("Content-Type", "application/json")
        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                payload = resp.read()
                headers = {k.lower(): v for k, v in resp.headers.items()}
        except urllib.error.HTTPError as err:
            detail = err.read().decode(errors="replace")
            try:
                detail = json.loads(detail).get("detail", detail)
            except ValueError:
                pass
            sys.exit(f"error: HTTP {err.code} on {method} {path}: {detail}")
        except urllib.error.URLError as err:
            sys.exit(f"error: cannot reach {self.url}: {err.reason}")
        if raw:
            return payload, headers
        return json.loads(payload) if payload else None

    def get(self, path: str, params: dict | None = None):
        if params:
            clean = {k: v for k, v in params.items() if v not in (None, "", False)}
            if clean:
                path += "?" + urllib.parse.urlencode(clean)
        return self.request("GET", path)


def filters(args) -> dict:
    return {
        "q": args.q or "",
        "cluster": args.cluster or "",
        "social": args.social,
        "follow_up": args.follow_up,
        "repeat": bool(args.repeat),
        "event_id": args.event_id,
    }


def add_filter_flags(p: argparse.ArgumentParser) -> None:
    p.add_argument("--q", help="text search on name and bio")
    p.add_argument("--cluster", choices=CLUSTERS, help="designation")
    p.add_argument("--social", choices=SOCIALS, help="has this social link")
    p.add_argument("--follow-up", dest="follow_up", choices=FOLLOW_UPS, help="follow-up status")
    p.add_argument("--repeat", action="store_true", help="met at more than one event")
    p.add_argument("--event-id", dest="event_id", help="only people on this event's guest list")


def main() -> None:
    ap = argparse.ArgumentParser(
        description="Afterparty API client",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    ap.add_argument("--url", default=os.environ.get("AFTERPARTY_URL", "http://localhost:8080"))
    ap.add_argument(
        "--auth",
        default=os.environ.get("AFTERPARTY_AUTH"),
        help='Authorization header value, e.g. "Bearer <token>"',
    )
    ap.add_argument(
        "--email",
        default=os.environ.get("AFTERPARTY_EMAIL"),
        help="local mode: sign in as this email",
    )
    sub = ap.add_subparsers(dest="cmd", required=True)

    sub.add_parser("health", help="is the instance up")
    sub.add_parser("me", help="current user, Partiful connection, last sync")
    sub.add_parser("stats", help="counts: events, people, repeats, designations")
    sub.add_parser("events", help="all events with guest counts")
    p = sub.add_parser("event", help="one event with its guest list")
    p.add_argument("event_id")

    p = sub.add_parser("people", help="people with filters")
    add_filter_flags(p)
    p.add_argument("--limit", type=int, default=60, help="page size, max 200")
    p.add_argument("--offset", type=int, default=0)
    p.add_argument("--all", action="store_true", help="fetch every page")

    p = sub.add_parser("person", help="one person with shared events")
    p.add_argument("person_id")

    p = sub.add_parser("map", help="people grouped by designation")
    add_filter_flags(p)

    p = sub.add_parser("export", help="write a CSV of a filter or a selection")
    p.add_argument("out", help="output .csv path")
    add_filter_flags(p)
    p.add_argument("--ids", help="comma-separated person ids (a selection)")

    p = sub.add_parser("sync", help="start a sync")
    p.add_argument("--full", action="store_true", help="read every guest list again")
    p.add_argument("--wait", action="store_true", help="wait until it finishes")

    sub.add_parser("sync-status", help="progress of the last sync")

    p = sub.add_parser("follow-up", help="set the follow-up status and note of a person")
    p.add_argument("person_id")
    p.add_argument("status", choices=FOLLOW_UPS)
    p.add_argument("--note", default="")

    args = ap.parse_args()
    auth = args.auth or (f"Dev {args.email}" if args.email else None)
    if args.cmd != "health" and not auth:
        sys.exit(
            "error: set AFTERPARTY_AUTH (Settings > API access for agents) or, in local mode, AFTERPARTY_EMAIL"
        )
    c = Client(args.url, auth)

    if args.cmd == "health":
        out = c.get("/api/health")
    elif args.cmd == "me":
        out = c.get("/api/me")
    elif args.cmd == "stats":
        out = c.get("/api/stats")
    elif args.cmd == "events":
        out = c.get("/api/events")
    elif args.cmd == "event":
        out = c.get(f"/api/events/{urllib.parse.quote(args.event_id, safe='')}")
    elif args.cmd == "people":
        params = filters(args)
        if not args.all:
            out = c.get("/api/people", {**params, "limit": args.limit, "offset": args.offset})
        else:
            people, offset, total = [], 0, None
            while total is None or offset < total:
                page = c.get("/api/people", {**params, "limit": 200, "offset": offset})
                total = page["total"]
                people += page["people"]
                offset += 200
                if not page["people"]:
                    break
            out = {"total": total, "people": people}
    elif args.cmd == "person":
        out = c.get(f"/api/people/{urllib.parse.quote(args.person_id, safe='')}")
    elif args.cmd == "map":
        out = c.get("/api/people/map", filters(args))
    elif args.cmd == "export":
        body = filters(args)
        if args.ids:
            body["ids"] = [i.strip() for i in args.ids.split(",") if i.strip()]
        data, headers = c.request("POST", "/api/people/export", body, raw=True)
        with open(args.out, "wb") as f:
            f.write(data)
        out = {"file": args.out, "rows": int(headers.get("x-afterparty-rows", "0"))}
    elif args.cmd == "sync":
        out = c.request("POST", "/api/sync", {"full": bool(args.full)})
        while args.wait and out and out.get("status") == "running":
            time.sleep(3)
            out = c.get("/api/sync")
            print(
                f"sync: {out.get('phase')} {out.get('events_done')}/{out.get('events_total')}",
                file=sys.stderr,
            )
    elif args.cmd == "sync-status":
        out = c.get("/api/sync")
    elif args.cmd == "follow-up":
        path = f"/api/people/{urllib.parse.quote(args.person_id, safe='')}/follow-up"
        out = c.request("PUT", path, {"status": args.status, "note": args.note})
    else:  # pragma: no cover
        ap.error(f"unknown command {args.cmd}")
    json.dump(out, sys.stdout, indent=2, default=str)
    print()


if __name__ == "__main__":
    main()
