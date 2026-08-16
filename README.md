# My IPTV GitHub Actions

Files:
- source_playlist.m3u — source playlist you control/have permission to use
- update_playlist.py — parses M3U and keeps reachable streams
- playlist.m3u — generated output
- .github/workflows/update.yml — runs every 30 minutes and can also be run manually

The workflow does not discover or bypass protected streams. It only processes URLs already present in source_playlist.m3u.
