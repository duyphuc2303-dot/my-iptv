from pathlib import Path
import re
import urllib.request
from datetime import datetime, timezone

SOURCE = Path("source_playlist.m3u")
OUTPUT = Path("playlist.m3u")
TIMEOUT = 10

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
                "meta": []
            }
            result.append(current)

        elif line.startswith("#EXTVLCOPT:") and current is not None:
            current["meta"].append(line)

        elif (line.startswith("http://") or line.startswith("https://")) and current is not None:
            current["url"] = line

    return [x for x in result if x.get("url")]


def stream_is_alive(url):
    request = urllib.request.Request(
        url,
        method="GET",
        headers={
            "User-Agent": "Mozilla/5.0",
            "Range": "bytes=0-2048",
            "Accept": "*/*",
        },
    )

    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
            return 200 <= response.status < 400
    except Exception:
        return False


def main():
    if not SOURCE.exists():
        raise SystemExit("source_playlist.m3u not found")

    entries = parse_m3u(SOURCE.read_text(encoding="utf-8", errors="replace"))

    lines = [
        "#EXTM3U",
        "#PLAYLIST:My IPTV",
        f"# Updated: {datetime.now(timezone.utc).isoformat()}",
    ]

    alive = 0

    for item in entries:
        url = item["url"]

        # Only retain streams that respond successfully.
        if not stream_is_alive(url):
            continue

        lines.append(item["extinf"])

        for meta in item["meta"]:
            lines.append(meta)

        lines.append(url)
        alive += 1

    OUTPUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Parsed streams: {len(entries)}")
    print(f"Working streams: {alive}")
    print(f"Wrote: {OUTPUT}")


if __name__ == "__main__":
    main()
