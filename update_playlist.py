from pathlib import Path
import re
import urllib.request
from datetime import datetime, timezone

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

        elif (line.startswith("http://") or line.startswith("https://")) and current is not None:
            current["url"] = line

    return [x for x in result if x.get("url")]


def get_referrer(item):
    for meta in item.get("meta", []):
        if meta.lower().startswith("#extvlcopt:http-referrer="):
            return meta.split("=", 1)[1].strip()
    return None


def stream_is_alive(item):
    url = item["url"]
    referrer = get_referrer(item)

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/131 Safari/537.36",
        "Accept": "*/*",
        "Range": "bytes=0-2048",
    }

    if referrer:
        headers["Referer"] = referrer

    request = urllib.request.Request(url, headers=headers, method="GET")

    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
            return 200 <= response.status < 400
    except Exception as exc:
        print(f"FAIL: {item['title']} -> {type(exc).__name__}: {exc}")
        return False


def main():
    if not SOURCE.exists():
        raise SystemExit("source_playlist.m3u not found")

    entries = parse_m3u(
        SOURCE.read_text(encoding="utf-8", errors="replace")
    )

    print(f"Parsed streams: {len(entries)}")

    lines = [
        "#EXTM3U",
        "#PLAYLIST:My IPTV",
        f"# Updated: {datetime.now(timezone.utc).isoformat()}",
    ]

    alive = 0

    for item in entries:
        if stream_is_alive(item):
            extinf = item["extinf"]

            # Remove tvg-logo if it points to tinhlagi.pro
            extinf = re.sub(
                r'\s+tvg-logo="https?://tinhlagi\.pro[^"]*"',
                "",
                extinf,
                flags=re.IGNORECASE,
            )

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
    print(f"Wrote: {OUTPUT}")

    # Do not fail the workflow if every stream is temporarily offline.
    # The next scheduled run can try again.


if __name__ == "__main__":
    main()
