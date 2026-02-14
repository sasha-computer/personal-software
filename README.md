# personal-software

Small tools I built for myself and actually use. Things graduate here from [experiments](https://github.com/sasha-computer/experiments) once they're useful enough to keep around.

## ⭐ [claude-code-usage](https://github.com/sasha-computer/claude-code-usage)

See your Claude Code rate limits in the macOS menu bar. Shows 5-hour and weekly usage percentages, color-coded so you know at a glance how close you are. Forked from NewTurn2017/ccusage and actively maintained with English support and a token refresh fix.

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

## ⭐ [pi-themes](https://github.com/sasha-computer/pi-themes)

Matching dark/light themes for pi and Ghostty that follow your system appearance. Three pairs (Catppuccin, Everforest, High Contrast) where the terminal and pi's TUI use the exact same hex values. Polls macOS appearance and switches both automatically.

**Stack:** TypeScript · pi extension

## ⭐ [pi-fzf](https://github.com/sasha-computer/pi-fzf)

Fuzzy find and resume Pi coding agent sessions. Indexes every message — yours and Pi's — across all sessions so you can find that thing you worked on three days ago by typing a few words you remember.

**Stack:** Python · uv · fzf

## ⭐ [pif](https://github.com/sasha-computer/pif)

Run a command. If it fails, send the output to Pi for help. That's it.

**Stack:** Python · uv

## ⭐ [readwise-triage](https://github.com/sasha-computer/readwise-triage)

Tinder for your Readwise Reader inbox. Syncs your library to a local SQLite database, then shows articles one at a time as swipeable cards. Left to archive, right to keep. Down arrow gets an AI summary so you can decide without opening the article. Burns through a backlog of 200+ articles in a few minutes.

**Stack:** TypeScript · Bun · SQLite · OpenRouter

## ⭐ [plain-text-running-tracker](https://github.com/sasha-computer/plain-text-running-tracker)

I wanted my running data in a format I actually own. This parses Apple Health XML exports and Garmin FIT files into a single markdown file — every run with date, distance, duration, pace, and heart rate. No cloud accounts, no subscriptions, just a `.md` file I can read, search, and version control. Plain text is forever.

**Stack:** Python · uv

## ⭐ [polymarket-copytrade](https://github.com/sasha-computer/polymarket-copytrade)

Automated bot that copy-trades top Polymarket bettors with risk management. Watches the leaderboard, mirrors their positions, and handles sizing.

**Stack:** Python · uv

## ⭐ [runelite-firemaking](https://github.com/sasha-computer/runelite-firemaking)

RuneLite plugin that tracks firemaking session stats. XP, logs burned, time elapsed — the important things in life.

**Stack:** Java · RuneLite

## ⭐ [sidebar](https://github.com/sasha-computer/sidebar)

Permanent macOS desktop sidebar pinned to the right edge of a widescreen monitor. Shows calendar, Todoist tasks, Spotify now playing, clipboard history, system stats, downloads, screenshots, and a quick note input. Built as a Svelte + Tailwind app inside a Hammerspoon webview. Auto-hides when undocked.

**Stack:** Svelte 5 · Tailwind v4 · Hammerspoon · Lua · Bun

## ⭐ [tinyclaw](https://github.com/sasha-computer/tinyclaw)

Tiny wrapper around Claude Code that turns it into a 24/7 personal AI agent. Uses a file-based queue so other services (WhatsApp, Telegram, etc.) can send messages and get responses back.

**Stack:** Shell · Claude Code

## ⭐ [x-likes](https://github.com/sasha-computer/x-likes)

Search your X/Twitter likes with fzf. Indexes your liked tweets in SQLite with full-text search so you can actually find that tweet you liked six months ago.

**Stack:** Python · SQLite · fzf
