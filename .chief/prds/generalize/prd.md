# Domain Search: Generalize & Package

## Overview

Enhance the existing domain-search CLI tool with three improvements: (1) add JSONL export format alongside JSON and CSV, (2) add a `--tld` filter flag so users can narrow domain hack searches to specific TLDs, and (3) package the tool with a proper CLI entry point so it can be installed via `uv tool install` and invoked as `domain-search` directly.

## User Stories

### US-001: JSONL Export Support
**Priority:** 1
**Description:** As a user, I want to export results as JSONL (JSON Lines) so that I can stream-process large result sets or append results to existing files.

**Acceptance Criteria:**
- [ ] `--output results.jsonl` exports results in JSON Lines format (one JSON object per line)
- [ ] Each line is a valid JSON object with the same fields as the JSON export (domain, status, check_method, type, timestamp)
- [ ] File extension `.jsonl` is auto-detected like `.json` and `.csv`
- [ ] Error message for unsupported formats is updated to mention `.jsonl`

### US-002: TLD Filter for Domain Hacks
**Priority:** 1
**Description:** As a user, I want to filter domain hack searches to specific TLDs so that I can quickly check availability for a known creative TLD without scanning all 1,500+.

**Acceptance Criteria:**
- [ ] `--tld` flag accepts one or more TLD values: `domain-search --hack aldrick --tld ck` or `domain-search --hack aldrick --tld ck sh io`
- [ ] When `--tld` is provided with `--hack`, only the specified TLDs are used for hack generation (not the full IANA list)
- [ ] When `--tld` is provided with an exact search term, only the specified TLDs are searched: `domain-search sasha --tld com dev io`
- [ ] TLD values are case-insensitive (user can type `CK` or `ck`)
- [ ] If a specified TLD doesn't exist in the IANA list, a warning is printed but the search continues with valid TLDs
- [ ] Can be combined: `domain-search sasha --hack aldrick --tld ck sh`

### US-003: Remove Hardcoded "sasha" References
**Priority:** 1
**Description:** As a user, I want the tool to present itself as a general-purpose domain search tool so that examples and help text aren't specific to one name.

**Acceptance Criteria:**
- [ ] Argparse help text uses generic examples (e.g., `<word>`) instead of "sasha"
- [ ] README examples use generic placeholders or varied example names instead of always "sasha"
- [ ] README export examples mention `.jsonl` alongside `.json` and `.csv`
- [ ] The `--output` flag help text mentions `.jsonl` as a supported format
- [ ] No functional code changes needed (the code already accepts any term)

### US-004: CLI Entry Point & Packaging
**Priority:** 1
**Description:** As a user, I want to install domain-search as a CLI tool via `uv tool install` so that I can invoke it as `domain-search` from anywhere without `uv run python main.py`.

**Acceptance Criteria:**
- [ ] `pyproject.toml` defines a `[project.scripts]` entry point: `domain-search = "domain_search.cli:main"`
- [ ] The `main()` function is moved from `main.py` to `domain_search/cli.py` (with `main.py` kept as a thin wrapper for backwards compatibility)
- [ ] After `uv tool install .`, the command `domain-search myname` works identically to `uv run python main.py myname`
- [ ] All existing CLI flags work: `--hack`, `--concurrency`, `--skip-rdap`, `--output`, and the new `--tld`
- [ ] `domain-search --help` shows usage information
