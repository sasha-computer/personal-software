# Domain Search: Find the Perfect "Sasha" Domain

## Overview

A Python CLI tool (managed with `uv`) that searches for available domain names across all known TLDs. The tool has two modes: **exact search** (e.g., `sasha.computer`, `sasha.dev`) and **domain hack search** (where the TLD forms part of a word, e.g., a surname ending in `.ck`). It uses free protocols (DNS lookups and RDAP) requiring no API keys.

## User Stories

### US-001: Fetch Complete TLD List
**Priority:** 1
**Description:** As a user, I want the tool to know about every public TLD so that no potential domain is missed.

**Acceptance Criteria:**
- [ ] Fetches the current TLD list from IANA (`https://data.iana.org/TLD/tlds-alpha-by-domain.txt`)
- [ ] Caches the TLD list locally so repeated runs don't re-download
- [ ] Parses the list correctly (skips comment lines, handles IDN/punycode TLDs)
- [ ] Reports the total number of TLDs found (should be ~1,500+)

### US-002: Check Domain Availability via DNS
**Priority:** 1
**Description:** As a user, I want to check if a domain is available by querying DNS so that I get fast results without needing an API key.

**Acceptance Criteria:**
- [ ] For a given domain (e.g., `sasha.io`), performs a DNS lookup for NS and SOA records
- [ ] Classifies domains as "registered" (has records) or "possibly available" (NXDOMAIN / no records)
- [ ] Handles DNS timeouts gracefully (marks as "unknown" rather than crashing)
- [ ] Uses async DNS resolution for concurrent lookups (not one-at-a-time)
- [ ] Respects a configurable concurrency limit to avoid flooding DNS servers (default: 50 concurrent)

### US-003: Search "sasha.{tld}" Across All TLDs
**Priority:** 1
**Description:** As a user, I want to search for `sasha` combined with every known TLD so that I can see all my options.

**Acceptance Criteria:**
- [ ] Accepts a search term via CLI argument (e.g., `python main.py sasha`)
- [ ] Generates `{term}.{tld}` for every TLD in the list
- [ ] Checks availability for each generated domain
- [ ] Shows a progress indicator (e.g., `Checking 1,524 domains...` with a progress bar)
- [ ] Displays results sorted by availability status, then alphabetically
- [ ] Full run completes in under 2 minutes for all TLDs

### US-004: Domain Hack Generator
**Priority:** 2
**Description:** As a user, I want the tool to find "domain hacks" where the TLD forms part of a word so that I can discover creative domain options.

**Acceptance Criteria:**
- [ ] Given a word (e.g., a full name or surname), finds all TLDs that match the end of the word
- [ ] For example, if the word is "kostick" and `.ck` is a TLD, suggests `kosti.ck`
- [ ] Also finds TLDs that appear anywhere within the word for more creative splits (e.g., `sa.sh` if `.sh` existed in context of "sasha")
- [ ] Activated via a `--hack` flag with the target word: `python main.py --hack kostick`
- [ ] Can combine with exact search: `python main.py sasha --hack lastname`
- [ ] Shows the "visual" reading of the domain (e.g., `kosti.ck` reads as "kostick")

### US-005: RDAP Availability Verification
**Priority:** 2
**Description:** As a user, I want to verify "possibly available" domains using RDAP so that I get more confident results.

**Acceptance Criteria:**
- [ ] For domains flagged as "possibly available" by DNS, performs an RDAP query for confirmation
- [ ] Uses the IANA RDAP bootstrap to find the correct RDAP server for each TLD
- [ ] Handles TLDs that don't have RDAP servers (falls back to DNS-only result)
- [ ] Reports registration status from RDAP when available (registered, available, reserved)
- [ ] Enabled by default but can be skipped with `--skip-rdap` for faster results
- [ ] Rate-limits RDAP queries to avoid being blocked (max 10/second)

### US-006: Rich Terminal Output
**Priority:** 2
**Description:** As a user, I want clear, well-formatted terminal output so that results are easy to scan and act on.

**Acceptance Criteria:**
- [ ] Uses `rich` library for formatted terminal output
- [ ] Shows a live progress bar during scanning
- [ ] Results displayed in a table with columns: Domain, Status, Type (exact/hack), Visual Reading (for hacks)
- [ ] Color-coded status: green for available, red for taken, yellow for unknown
- [ ] Summary at the end: total checked, available count, taken count, unknown count
- [ ] Available domains are highlighted/grouped at the top for easy scanning

### US-007: Export Results
**Priority:** 3
**Description:** As a user, I want to export results to a file so that I can review them later or share them.

**Acceptance Criteria:**
- [ ] `--output results.json` flag exports results as JSON
- [ ] `--output results.csv` flag exports results as CSV
- [ ] Format is auto-detected from file extension
- [ ] Exported data includes: domain, status, check method (DNS/RDAP), type (exact/hack), timestamp

### US-008: Project Setup with UV
**Priority:** 1
**Description:** As a developer, I want the project properly set up with `uv` so that dependencies are managed and the tool is easy to run.

**Acceptance Criteria:**
- [ ] Project initialized with `uv init`
- [ ] `pyproject.toml` with all dependencies declared (`dnspython`, `httpx`, `rich`)
- [ ] Can be run with `uv run python main.py sasha`
- [ ] Python 3.12+ required
- [ ] README with usage instructions
