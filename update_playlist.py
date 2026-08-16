from pathlib import Path
from datetime import datetime, timezone

# Các stream URL được phép sử dụng của bạn.
# Mỗi mục gồm: tên trận, giải đấu, URL stream.
#
# Ví dụ:
# MATCHES = [
#     {
#         "name": "Demo FC vs Example FC",
#         "league": "Football",
#         "url": "https://example.com/live.m3u8",
#     }
# ]

MATCHES = []


def create_playlist():
    lines = [
        "#EXTM3U",
        f"# Generated: {datetime.now(timezone.utc).isoformat()}",
    ]

    for match in MATCHES:
        name = match["name"]
        league = match.get("league", "Football")
        url = match["url"]

        if not url:
            continue

        lines.append(
            f'#EXTINF:-1 group-title="{league}",{name}'
        )
        lines.append(url)

    Path("playlist.m3u").write_text(
        "\n".join(lines) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    create_playlist()
