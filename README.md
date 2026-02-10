# personal-software

Small tools I built for myself and actually use. Things graduate here from [experiments](https://github.com/sasha-computer/experiments) once they're useful enough to keep around.

## ⭐ domain-search

Search for available domains across every TLD, right in the terminal. No API keys, no paid services. Uses DNS + RDAP checks with async lookups, domain hack detection (e.g. `creati.ve`), and result export to JSON/CSV. Built with `uv` so it runs instantly with no install.

![domain-search CLI demo](./domain-search/assets/domain-search-demo.gif)

**Stack:** Python · asyncio · uv

→ [browse code](./domain-search)

## ⭐ plain-text-running-tracker

Parses Apple Health XML exports and Garmin FIT files into a simple markdown running log. Extracts every run with date, distance, duration, pace, and heart rate, then writes it all to a single `.md` file. No cloud, no accounts, just your data in plain text.

**Stack:** Python

→ [browse code](./plain-text-running-tracker)

## ⭐ immich-backup

Automated backup system for [Immich](https://immich.app/) photos. Pulls photos from a NAS over SSH (local or Tailscale), stages them locally, then archives to a LUKS-encrypted USB drive as compressed tarballs. Runs on a systemd timer. Includes install/uninstall scripts.

**Stack:** Bash · systemd · LUKS · rsync

→ [browse code](./immich-backup)
