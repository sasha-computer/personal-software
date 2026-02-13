# personal-software

Small tools I built for myself and actually use. Things graduate here from [experiments](https://github.com/sasha-computer/experiments) once they're useful enough to keep around.

## ⭐ [ccusage](https://github.com/sasha-computer/ccusage)

Minimal macOS menu bar app that shows real-time Claude Code usage — tokens, cost, and session stats at a glance. Lives in the menu bar, stays out of the way.

**Stack:** Swift · macOS 14+

## ⭐ [domain-search](https://github.com/sasha-computer/domain-search)

I got tired of cycling through domain registrar search bars that upsell you on premium TLDs. This searches for available domains across basically every TLD right in the terminal — no API keys, no paid services. Uses DNS + RDAP checks with async lookups, finds domain hacks (e.g. `creati.ve`), and exports results to JSON/CSV. Built with `uv` so it runs instantly with zero install.

**Stack:** Python · asyncio · uv

## ⭐ [Handy](https://github.com/sasha-computer/Handy)

Free, open source speech-to-text that works completely offline. No cloud, no API keys, no data leaving your machine.

**Stack:** TypeScript

## ⭐ [pi-daily](https://github.com/sasha-computer/pi-daily)

AI RescueTime for Obsidian daily notes. Scans Pi coding agent sessions and generates a summary of what you worked on, dropped straight into your daily note.

**Stack:** Go

## ⭐ [pi-fzf](https://github.com/sasha-computer/pi-fzf)

Fuzzy find and resume Pi coding agent sessions. Indexes every message you've sent across every session so you can find that thing you worked on three days ago by typing a few words you remember saying.

**Stack:** Go

## ⭐ [pif](https://github.com/sasha-computer/pif)

Run a command. If it fails, send the output to Pi for help. That's it.

**Stack:** Python · uv

## ⭐ [plain-text-running-tracker](https://github.com/sasha-computer/plain-text-running-tracker)

I wanted my running data in a format I actually own. This parses Apple Health XML exports and Garmin FIT files into a single markdown file — every run with date, distance, duration, pace, and heart rate. No cloud accounts, no subscriptions, just a `.md` file I can read, search, and version control. Plain text is forever.

**Stack:** Python · uv

## ⭐ [polymarket-copytrade](https://github.com/sasha-computer/polymarket-copytrade)

Automated bot that copy-trades top Polymarket bettors with risk management. Watches the leaderboard, mirrors their positions, and handles sizing.

**Stack:** Python · uv

## ⭐ [runelite-firemaking](https://github.com/sasha-computer/runelite-firemaking)

RuneLite plugin that tracks firemaking session stats. XP, logs burned, time elapsed — the important things in life.

**Stack:** Java · RuneLite

## ⭐ [tinyclaw](https://github.com/sasha-computer/tinyclaw)

Tiny wrapper around Claude Code that turns it into a 24/7 personal AI agent. Uses a file-based queue so other services (WhatsApp, Telegram, etc.) can send messages and get responses back.

**Stack:** Shell · Claude Code

## ⭐ [x-likes](https://github.com/sasha-computer/x-likes)

Search your X/Twitter likes with fzf. Indexes your liked tweets in SQLite with full-text search so you can actually find that tweet you liked six months ago.

**Stack:** Python · SQLite · fzf
