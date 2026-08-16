from pathlib import Path
from datetime import datetime, timezone

# ============================================================
# CÁC STREAM URL BẠN CÓ QUYỀN SỬ DỤNG
# ============================================================
#
# Mỗi trận gồm:
#   name   : tên trận
#   league : tên giải
#   date   : ngày thi đấu, YYYY-MM-DD
#   url    : URL .m3u8 của nguồn được phép sử dụng
#
# Ví dụ:
#
# MATCHES = [
#     {
#         "name": "Đội A vs Đội B",
#         "league": "Football",
#         "date": "2026-08-16",
#         "url": "https://example.com/live.m3u8",
#     }
# ]

MATCHES = []


def create_playlist():
    today = datetime.now(timezone.utc).date().isoformat()

    lines = [
        "#EXTM3U",
        "#PLAYLIST:My IPTV",
        f"# Updated: {datetime.now(timezone.utc).isoformat()}",
    ]

    for match in MATCHES:

        if not match.get("url"):
            continue

        # Chỉ đưa trận hôm nay và tương lai vào playlist
        match_date = match.get("date", "")

        if match_date < today:
            continue

        name = match.get("name", "Unknown Match")
        league = match.get("league", "Football")
        url = match["url"]

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
