#!/usr/bin/env python3
"""
update_feeds.py
~~~~~~~~~~~~~~~~

This script demonstrates how you might automatically update the RSS feed
XML files in your repository.  It fetches fresh content from your
preferred news sources and rebuilds the RSS files accordingly.  The
example functions below are placeholders – they simply read the
existing local XML files and bump the ``lastBuildDate`` to the current
timestamp.  To achieve real‐time updates, you should replace the
placeholder functions with logic that fetches and parses the latest
articles from the relevant websites (e.g. using the ``requests`` and
``BeautifulSoup`` libraries).

When run on GitHub Actions, the script will update the XML files and
write them back to disk.  A subsequent git commit will then push the
changes back into your repository.

To run locally you need Python 3.8+ and the dependencies listed in
``requirements.txt`` (currently only ``beautifulsoup4`` is optional).
You can invoke the script from the command line:

    python update_feeds.py

"""

import datetime
import os
import xml.etree.ElementTree as ET

HERE = os.path.abspath(os.path.dirname(__file__))


def update_last_build_date(tree: ET.ElementTree) -> None:
    """Update the ``lastBuildDate`` element in the given RSS tree.

    The RSS specification uses RFC 2822 timestamps.  We convert the
    current UTC time into that format.  If no ``lastBuildDate`` exists
    in the feed, the function silently does nothing.

    Args:
        tree: An ``xml.etree.ElementTree`` representing the RSS feed.
    """
    channel = tree.find("channel")
    if channel is None:
        return
    last_build = channel.find("lastBuildDate")
    if last_build is None:
        return
    # Format: Wed, 23 Jul 2025 17:22:05 +0000
    now = datetime.datetime.utcnow().strftime("%a, %d %b %Y %H:%M:%S +0000")
    last_build.text = now


def refresh_existing_feed(file_path: str) -> None:
    """Load an existing RSS feed file and update its lastBuildDate.

    Args:
        file_path: Path to the RSS XML file.
    """
    print(f"Updating {file_path}…")
    tree = ET.parse(file_path)
    update_last_build_date(tree)
    tree.write(file_path, encoding="utf-8", xml_declaration=True)


def main() -> None:
    """Entry point for the update script.

    For each of your feed files, call a refresh/update function.  The
    ``refresh_existing_feed`` function only updates the timestamp but
    leaves the items untouched.  Replace the calls below with your own
    scraping/parsing logic to fetch the latest articles and rebuild
    the ``ElementTree`` accordingly.
    """
    feeds = [
        "league_dev_feed.xml",
        "valorant_dev_feed.xml",
        "ign_combined_feed.xml",
        "gamersky_review_feed.xml",
    ]
    for feed_name in feeds:
        feed_path = os.path.join(HERE, feed_name)
        if not os.path.exists(feed_path):
            print(f"Skipping missing feed file: {feed_name}")
            continue
        refresh_existing_feed(feed_path)


if __name__ == "__main__":
    main()