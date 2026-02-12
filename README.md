# personal-software

Small tools I built for myself and actually use. Things graduate here from [experiments](https://github.com/sasha-computer/experiments) once they're useful enough to keep around.

## ⭐ [domain-search](https://github.com/sasha-computer/domain-search)

I got tired of cycling through domain registrar search bars that upsell you on premium TLDs. This searches for available domains across basically every TLD right in the terminal — no API keys, no paid services. Uses DNS + RDAP checks with async lookups, finds domain hacks (e.g. `creati.ve`), and exports results to JSON/CSV. Built with `uv` so it runs instantly with zero install.

**Stack:** Python · asyncio · uv

## ⭐ [plain-text-running-tracker](https://github.com/sasha-computer/plain-text-running-tracker)

I wanted my running data in a format I actually own. This parses Apple Health XML exports and Garmin FIT files into a single markdown file — every run with date, distance, duration, pace, and heart rate. No cloud accounts, no subscriptions, just a `.md` file I can read, search, and version control. Plain text is forever.

**Stack:** Python · uv
