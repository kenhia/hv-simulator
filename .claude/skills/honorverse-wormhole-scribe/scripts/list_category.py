#!/usr/bin/env python3
"""List the page members of an Honorverse Wiki category via the MediaWiki API.

Useful for cross-checking the wormhole index against the category, e.g.:
    python list_category.py "Wormhole Junctions"

But note: the best wormhole index is the two concept pages, not a category —
'Wormhole junction' lists every junction/bridge/quasi-junction, and
'Wormhole terminus' lists the termini grouped by their junction/bridge. Fetch
those with fetch_wikitext.py first.

Handles continuation (>500 members). Stdlib only.
"""

from __future__ import annotations

import argparse
import json
import urllib.parse
import urllib.request

API = "https://honorverse.fandom.com/api.php"
UA = "Mozilla/5.0 (compatible; honorverse-wormhole-scribe/0.1; Honorverse-Data tooling)"


def list_category(cat: str) -> list[str]:
    """Return ns0 (article) page titles in a category, following continuation."""
    title = cat if cat.lower().startswith("category:") else "Category:" + cat
    members: list[str] = []
    cont = None
    while True:
        params = {
            "action": "query",
            "list": "categorymembers",
            "cmtitle": title,
            "cmlimit": "500",
            "format": "json",
            "formatversion": "2",
        }
        if cont:
            params["cmcontinue"] = cont
        url = API + "?" + urllib.parse.urlencode(params)
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.load(resp)
        if "error" in data:
            raise SystemExit(f"API error: {data['error'].get('info', 'unknown')}")
        members += [m["title"] for m in data["query"]["categorymembers"] if m["ns"] == 0]
        cont = data.get("continue", {}).get("cmcontinue")
        if not cont:
            break
    return members


def main() -> None:
    ap = argparse.ArgumentParser(description="List Honorverse Wiki category members.")
    ap.add_argument("category", help="category name, with or without 'Category:' prefix")
    args = ap.parse_args()
    for t in list_category(args.category):
        print(t)


if __name__ == "__main__":
    main()
