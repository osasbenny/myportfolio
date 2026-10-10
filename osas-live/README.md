# OSAS LIVE — one playlist on all your devices

**Main playlist URL (paste into VLC):**

```text
https://raw.githubusercontent.com/osasbenny/myportfolio/main/osas-live/playlist.m3u
```

This is a public, read-only M3U file listing English-language IPTV channels and internet radio.
It contains selected favorites and additional publicly indexed streams across news, movies, action, documentaries, science, music, sports, and more.
It **does not host, decrypt, or retransmit** television or radio content.
Availability, authorization, codec compatibility, and regional licensing vary by broadcaster.
Not every listed URL has been playback-tested.

## Windows / Android

Use VLC **Open Network Stream**, paste the raw GitHub URL, and open the playlist.
On Windows, press **Ctrl+L** to reveal the list of channels.

## iPhone / iPad (VLC)

VLC on iOS has had inconsistent handling of *remote* M3U playlists as channel lists.
If pasting the URL in **Network > Open Network Stream** plays only one channel or fails to show the list:

1. Open the raw playlist URL in **Safari** and save the file to **Files**.
2. In Files, move `playlist.m3u` to **On My iPhone > VLC** (the VLC app folder).
3. Open VLC, navigate to **Network > Local Files** or its local file browser, and select the playlist.
4. The channels remain **internet streams**; only the small M3U text file is saved locally.

If even a direct channel fails on iOS, try another channel. HLS compatibility, geo-blocks, app support, and server-side access can differ between Android and iPhone.
Keep VLC updated. Some broadcasters may not support third-party playback.

## Refreshes / changes

- `favorites.m3u` preserves the starter favorites.
- `build_playlist.py` assembles current English public channel listings from [IPTV-org](https://github.com/iptv-org/iptv) and selected internet radio from [Radio Browser](https://www.radio-browser.info/).
- `status.json` reports the latest generated totals.
- GitHub Actions checks for updates every Sunday and also whenever the builder or favorites list changes.
- The live URL remains the same. Reload the playlist to get updates; iOS local imports need a fresh download.

To add a favorite channel, only use a stream provided for public playback by the rightsholder where possible, and update `favorites.m3u`.
No premium TV subscriptions, DRM, or regional access restrictions are bypassed.

*This project is a personal directory, not affiliated with IPTV-org, broadcasters, or VLC.*
