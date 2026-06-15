#!/usr/bin/env python3
"""List the page members of an Honorverse Wiki category via the MediaWiki API.

The discovery half of the ship-scribe loop: the wiki is poorly organized for
browsing, but its categories are a reliable index. Use this to see what exists
before scraping.

    python list_category.py "Manticoran Ship Classes"
    python list_category.py "Grayson Ship Classes"
    python list_category.py "Havenite Ship Classes"     # note: 'Havenite', not 'Haven'
    python list_category.py "Andermani Ship Classes"

Handles continuation (categories with >500 members). Stdlib only.
"""

from __future__ import annotations

import argparse
import json
import urllib.parse
import urllib.request

API = "https://honorverse.fandom.com/api.php"
UA = "Mozilla/5.0 (compatible; honorverse-ship-scribe/0.1; Honorverse-Data tooling)"


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
