#!/usr/bin/env python3
"""
Automatic RSS feed builder for game news
=======================================

This script attempts to fetch the latest posts from a handful of game‑related
news pages and rebuilds the corresponding RSS feeds.  It supports the
following sources:

  * League of Legends developer updates
    (https://www.leagueoflegends.com/en-gb/news/dev/)
  * VALORANT developer updates
    (https://playvalorant.com/en-us/news/dev/)
  * 游民星空游戏评测
    (https://www.gamersky.com/review/)

The script writes to three XML files in the current directory:
```
league_dev_feed.xml
valorant_dev_feed.xml
gamersky_review_feed.xml
```

If a particular source cannot be fetched or parsed (for example due to
network restrictions or site changes), the script will fall back to
updating the ``lastBuildDate`` in the existing feed rather than
discarding it.  This ensures your GitHub Action will still complete
successfully.

The fetching logic below is intentionally conservative: HTML
structures change frequently, so this script uses very simple
selectors and heuristic extraction rules.  Feel free to refine the
parsers to better suit the target sites.  You can also replace the
fetch functions entirely if you have access to more reliable APIs.

Dependencies: ``requests``, ``beautifulsoup4``.  These are installed
automatically in the accompanying GitHub Action.
"""

import datetime
import html
import os
import re
import xml.etree.ElementTree as ET
from typing import Dict, Iterable, List

import requests
from bs4 import BeautifulSoup

# Global HTTP headers for polite scraping.  Many sites return 403 to
# default Python user agents; using a common browser UA helps avoid
# that.  Adjust as necessary.
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36"
    )
}


def fetch_league_dev() -> List[Dict[str, str]]:
    """Fetch recent League of Legends dev posts.

    Returns a list of dictionaries with keys: title, description,
    pubDate (RFC 2822), link, guid and optionally enclosure_url.

    This implementation scrapes the dev news listing page and looks
    for anchor tags whose href contains ``/news/dev``.  The
    description is pulled from the link's title attribute or the link
    text.  Only the first few posts (up to 10) are returned.
    """
    url = "https://www.leagueoflegends.com/en-gb/news/dev/"
    items: List[Dict[str, str]] = []
    try:
        resp = requests.get(url, headers=HEADERS, timeout=20)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        # Find all anchor tags linking to dev content.
        candidates = soup.find_all("a", href=True)
        for a in candidates:
            href = a["href"]
            # Accept YouTube and internal blog posts.
            if not (
                "/news/dev" in href
                or href.startswith("https://www.youtube.com")
            ):
                continue
            title = a.get_text(strip=True)
            if not title:
                title = a.get("title", "League dev update")
            # Try to extract date from text like "Dev 13/07/2025".
            date_match = re.search(r"(\d{2}/\d{2}/\d{4})", title)
            if date_match:
                dt = datetime.datetime.strptime(
                    date_match.group(1), "%d/%m/%Y"
                )
            else:
                dt = datetime.datetime.utcnow()
            pub = dt.strftime("%a, %d %b %Y %H:%M:%S +0000")
            items.append(
                {
                    "title": html.unescape(title),
                    "description": html.unescape(title),
                    "pubDate": pub,
                    "link": href,
                    "guid": href,
                    "enclosure_url": "",
                }
            )
            if len(items) >= 10:
                break
    except Exception as e:
        print(f"[league] failed to fetch: {e}")
    return items


def fetch_valorant_dev() -> List[Dict[str, str]]:
    """Fetch recent VALORANT dev posts.

    Similar to ``fetch_league_dev`` but targets the VALORANT dev news
    page.  Because the VALORANT site often uses dynamic content,
    scraping may occasionally fail; fallback behaviour is handled
    elsewhere.
    """
    url = "https://playvalorant.com/en-us/news/dev/"
    items: List[Dict[str, str]] = []
    try:
        resp = requests.get(url, headers=HEADERS, timeout=20)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        for a in soup.find_all("a", href=True):
            href = a["href"]
            if "/news/dev" not in href and not href.startswith(
                "https://www.youtube.com"
            ):
                continue
            title = a.get_text(strip=True)
            if not title:
                title = a.get("title", "VALORANT dev update")
            # Attempt to parse a date from the anchor's sibling elements
            dt = datetime.datetime.utcnow()
            pub = dt.strftime("%a, %d %b %Y %H:%M:%S +0000")
            items.append(
                {
                    "title": html.unescape(title),
                    "description": html.unescape(title),
                    "pubDate": pub,
                    "link": href,
                    "guid": href,
                    "enclosure_url": "",
                }
            )
            if len(items) >= 10:
                break
    except Exception as e:
        print(f"[valorant] failed to fetch: {e}")
    return items



def fetch_gamersky_reviews() -> List[Dict[str, str]]:
    """Fetch recent 游民星空游戏评测文章.

    This function attempts to scrape the gamersky review listing page,
    selecting anchors that link to ``news/`` and end with ``.shtml``.
    Gamersky tends to block non‑browser user agents, so this may fail
    without additional proxy or headers.
    """
    url = "https://www.gamersky.com/review/"
    items: List[Dict[str, str]] = []
    try:
        resp = requests.get(url, headers=HEADERS, timeout=20)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        for a in soup.find_all("a", href=True):
            href = a["href"]
            if not ("/news/" in href and href.endswith(".shtml")):
                continue
            title = a.get_text(strip=True)
            if not title:
                continue
            dt = datetime.datetime.utcnow()
            pub = dt.strftime("%a, %d %b %Y %H:%M:%S +0000")
            items.append(
                {
                    "title": html.unescape(title),
                    "description": html.unescape(title),
                    "pubDate": pub,
                    "link": href,
                    "guid": href,
                    "enclosure_url": "",
                }
            )
            if len(items) >= 10:
                break
    except Exception as e:
        print(f"[gamersky] failed to fetch: {e}")
    return items


def build_rss(channel: Dict[str, str], items: Iterable[Dict[str, str]]) -> ET.ElementTree:
    """Build an RSS feed from channel metadata and a list of items.

    Args:
        channel: A mapping containing at least ``title``, ``link``
            and ``description``.  Optionally ``language``.
        items: An iterable of dictionaries representing feed items.

    Returns:
        An ``ElementTree`` instance ready to be written to disk.
    """
    rss = ET.Element("rss", version="2.0")
    chan = ET.SubElement(rss, "channel")
    for key in ["title", "link", "description", "language"]:
        if key in channel and channel[key]:
            elem = ET.SubElement(chan, key)
            elem.text = channel[key]
    # Set lastBuildDate
    now = datetime.datetime.utcnow().strftime("%a, %d %b %Y %H:%M:%S +0000")
    ET.SubElement(chan, "lastBuildDate").text = now
    # Add items
    for item in items:
        it_elem = ET.SubElement(chan, "item")
        for tag in ["title", "description", "pubDate", "link", "guid"]:
            if tag in item and item[tag]:
                sub = ET.SubElement(it_elem, tag)
                sub.text = item[tag]
        # Add enclosure if provided
        if item.get("enclosure_url"):
            enc = ET.SubElement(
                it_elem,
                "enclosure",
                url=item["enclosure_url"],
                length="0",
                type="image/*",
            )
    return ET.ElementTree(rss)


def update_lastbuild_only(file_path: str) -> None:
    """Fallback updater: refresh only the lastBuildDate of an existing RSS file."""
    try:
        tree = ET.parse(file_path)
        chan = tree.find("channel")
        if chan is not None:
            lb = chan.find("lastBuildDate")
            if lb is not None:
                now = datetime.datetime.utcnow().strftime("%a, %d %b %Y %H:%M:%S +0000")
                lb.text = now
                tree.write(file_path, encoding="utf-8", xml_declaration=True)
    except Exception as e:
        print(f"[fallback] failed to update {file_path}: {e}")


def main() -> None:
    """Entry point.  Fetch feeds and write XML files."""
    # Define each feed's metadata and fetcher
    feeds = [
        {
            "file": "league_dev_feed.xml",
            "channel": {
                "title": "League of Legends Dev News",
                "link": "https://www.leagueoflegends.com/en-gb/news/dev/",
                "description": "Latest developer updates and diaries from the League of Legends team.",
                "language": "en",
            },
            "fetcher": fetch_league_dev,
        },
        {
            "file": "valorant_dev_feed.xml",
            "channel": {
                "title": "Valorant Dev News",
                "link": "https://playvalorant.com/en-us/news/dev/",
                "description": "Latest development updates and diaries from the VALORANT dev team.",
                "language": "en",
            },
            "fetcher": fetch_valorant_dev,
        },
        {
            "file": "gamersky_review_feed.xml",
            "channel": {
                "title": "游民星空游戏评测：最新文章",
                "link": "https://www.gamersky.com/review/",
                "description": "游民星空游戏评分评测专题最新文章，包含标题、摘要和图片。",
                "language": "zh-cn",
            },
            "fetcher": fetch_gamersky_reviews,
        },
    ]
    for feed in feeds:
        file_path = os.path.join(os.path.abspath(os.path.dirname(__file__)), feed["file"])
        print(f"Updating {feed['file']}...")
        items = feed["fetcher"]()
        if items:
            tree = build_rss(feed["channel"], items)
            tree.write(file_path, encoding="utf-8", xml_declaration=True)
            print(f"Written {len(items)} items to {feed['file']}")
        else:
            # Fallback to updating lastBuildDate if no items were fetched
            print(f"No items fetched for {feed['file']}; updating timestamp only.")
            update_lastbuild_only(file_path)


if __name__ == "__main__":
    main()