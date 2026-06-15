#!/usr/bin/env python3
"""Fetch raw wikitext for an Honorverse Wiki page via the MediaWiki API.

Fandom blocks naive HTML scrapers (HTTP 403), but the api.php endpoint works
fine with an ordinary browser User-Agent. Going through the API also means you
get the *source wikitext* (infobox templates, the system body chart, citation
templates) instead of rendered HTML you'd have to re-parse.

Stdlib only -- runs the same on Windows and Linux with no pip installs.

Usage:
    python fetch_wikitext.py "Manticore System"
    python fetch_wikitext.py "Basilisk System" --save _raw/basilisk-system.wiki
    python fetch_wikitext.py "Grayson" --section "Astrography"   # not yet; see notes
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.parse
import urllib.request

API = "https://honorverse.fandom.com/api.php"
UA = "Mozilla/5.0 (compatible; honorverse-system-scribe/0.1; Honorverse-Data tooling)"


def fetch_wikitext(title: str) -> str:
    """Return the raw wikitext of a page, following redirects."""
    params = {
        "action": "parse",
        "page": title,
        "prop": "wikitext",
        "format": "json",
        "formatversion": "2",
        "redirects": "1",
    }
    url = API + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.load(resp)
    if "error" in data:
        info = data["error"].get("info", "unknown error")
        raise SystemExit(f"API error for {title!r}: {info}")
    return data["parse"]["wikitext"]


def main() -> None:
    ap = argparse.ArgumentParser(description="Fetch Honorverse Wiki page source.")
    ap.add_argument("title", help="exact page title, e.g. 'Manticore System'")
    ap.add_argument(
        "--save",
        metavar="PATH",
        help="write wikitext to PATH (UTF-8) instead of stdout",
    )
    args = ap.parse_args()

    text = fetch_wikitext(args.title)
    if args.save:
        with open(args.save, "w", encoding="utf-8") as fh:
            fh.write(text)
        print(f"wrote {len(text):,} chars to {args.save}", file=sys.stderr)
    else:
        # stdout, UTF-8, so it pipes cleanly on Windows too
        sys.stdout.buffer.write(text.encode("utf-8"))


if __name__ == "__main__":
    main()
