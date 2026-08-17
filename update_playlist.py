from pathlib import Path
import re
import urllib.request
from datetime import datetime, timezone, timedelta

SOURCE = Path("source_playlist.m3u")
OUTPUT = Path("playlist.m3u")
TIMEOUT = 15


def parse_m3u(text):
    result = []
    current = None

    for raw in text.splitlines():
        line = raw.strip()

        if not line:
            continue

        if line.startswith("#EXTINF:"):
            title = line.split(",", 1)[1].strip() if "," in line else "Stream"

            group_match = re.search(r'group-title="([^"]*)"', line)
            group = group_match.group(1) if group_match else "Football"

            current = {
                "extinf": line,
                "title": title,
                "group": group,
                "meta": [],
            }

            result.append(current)

        elif line.startswith("#EXTVLCOPT:") and current is not None:
            current["meta"].append(line)

        elif (
            line.startswith("http://")
            or line.startswith("https://")
        ) and current is not None:
            current["url"] = line

    return [x for x in result if x.get("url")]


def get_referrer(item):
    for meta in item.get("meta", []):
        if meta.lower().startswith("#extvlcopt:http-referrer="):
            return meta.split("=", 1)[1].strip()

    return None


def get_match_datetime(title):
    """
    Extract match date/time from titles such as:
    21:00 16/08 Arsenal vs Manchester City
    01:45 17/08 Lens vs Paris Saint Germain
    """

    match = re.search(
        r'(\d{1,2}):(\d{2})\s+(\d{1,2})/(\d{1,2})',
        title
    )

    if not match:
        return None

    hour = int(match.group(1))
    minute = int(match.group(2))
    day = int(match.group(3))
    month = int(match.group(4))

    now = datetime.now(timezone.utc)

    try:
        match_time = datetime(
            now.year,
            month,
            day,
            hour,
            minute,
            tzinfo=timezone.utc,
        )
    except ValueError:
        return None

    return match_time


def match_is_current_or_future(item):
    """
    Keep matches that have not ended yet.

    We allow a 3-hour grace period after the scheduled
    start time because a football match can still be
    in progress.
    """

    match_time = get_match_datetime(item["title"])

    # If the title does not contain a recognizable date/time,
    # keep it rather than accidentally deleting it.
    if match_time is None:
        return True

    now = datetime.now(timezone.utc)

    # Keep the match for up to 3 hours after kick-off.
    expiry_time = match_time + timedelta(hours=3)

    if expiry_time < now:
        print(f"OLD: {item['title']}")
        return False

    return True


def stream_is_alive(item):
    url = item["url"]
    referrer = get_referrer(item)

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 Chrome/131 Safari/537.36"
        ),
        "Accept": "*/*",
        "Range": "bytes=0-2048",
    }

    if referrer:
        headers["Referer"] = referrer

    request = urllib.request.Request(
        url,
        headers=headers,
        method="GET",
    )

    try:
        with urllib.request.urlopen(
            request,
            timeout=TIMEOUT
        ) as response:
            return 200 <= response.status < 400

    except Exception as exc:
        print(
            f"FAIL: {item['title']} -> "
            f"{type(exc).__name__}: {exc}"
        )
        return False


def clean_extinf(extinf):
    """
    Remove only the tvg-logo attribute when it points
    to tinhlagi.pro.

    Other information in #EXTINF is preserved.
    """

    extinf = re.sub(
        r'\s+tvg-logo="https?://tinhlagi\.pro[^"]*"',
        "",
        extinf,
        flags=re.IGNORECASE,
    )

    return extinf


def main():
    if not SOURCE.exists():
        raise SystemExit(
            "source_playlist.m3u not found"
        )

    entries = parse_m3u(
        SOURCE.read_text(
            encoding="utf-8",
            errors="replace",
        )
    )

    print(f"Parsed streams: {len(entries)}")

    lines = [
        "#EXTM3U",
        "#PLAYLIST:My IPTV",
        f"# Updated: {datetime.now(timezone.utc).isoformat()}",
    ]

    alive = 0
    old = 0
    failed = 0

    for item in entries:

        # Remove matches that ended more than 3 hours ago.
        if not match_is_current_or_future(item):
            old += 1
            continue

        # Check whether the stream server is reachable.
        if not stream_is_alive(item):
            failed += 1
            continue

        # Remove tinhlagi.pro only from tvg-logo.
        extinf = clean_extinf(item["extinf"])

        lines.append(extinf)

        for meta in item["meta"]:
            lines.append(meta)

        lines.append(item["url"])

        alive += 1

    OUTPUT.write_text(
        "\n".join(lines) + "\n",
        encoding="utf-8",
    )

    print(f"Working streams: {alive}")
    print(f"Old matches removed: {old}")
    print(f"Failed streams: {failed}")
    print(f"Wrote: {OUTPUT}")


if __name__ == "__main__":
    main()
