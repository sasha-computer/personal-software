## Codebase Patterns
- Project uses `uv` for Python package management; run with `uv run python main.py`
- Package structure: `domain_search/` for source, `tests/` for tests
- TLD cache stored at `~/.cache/domain-search/tlds.txt` with 1-day expiry
- Tests use `unittest.mock.patch` to mock external calls (httpx, filesystem)
- Async tests use `@pytest.mark.asyncio` with `AsyncMock` for async resolver mocking
- DNS checker uses `dns.asyncresolver.Resolver` with `asyncio.Semaphore` for concurrency control
- Run tests with `uv run pytest tests/ -v`
- CLI accepts positional `term` arg and optional `--concurrency` flag via argparse
- `check_domains` supports `on_result` callback for progress tracking
- `generate_domains()` in `main.py` creates `{term}.{tld}` for all TLDs
- `sort_results()` sorts by status (available > unknown > registered), then alphabetically
- `domain_search/hack_generator.py` provides `generate_domain_hacks(word, tlds)` → list of `DomainHack(domain, visual)`
- Domain hacks split into suffix hacks (TLD at end of word) and interior hacks (TLD anywhere else within word)
- CLI `--hack WORD` flag can be combined with positional `term` for both exact + hack search
- `domain_meta` dict in `main.py` maps domain → `{"type": "exact"|"hack", "visual": str}` for enriched display
- `display_results` auto-detects hack mode and adds Type/Visual Reading columns when hacks are present
- RDAP bootstrap cached at `~/.cache/domain-search/rdap_bootstrap.json` with 1-day expiry
- `verify_available_domains()` takes DNS results and re-checks "possibly available" domains via RDAP
- RDAP rate limiting via `_RateLimiter` token-bucket (default 10/sec)
- `--skip-rdap` flag bypasses RDAP verification for faster results
- When adding new pipeline steps (like RDAP), existing CLI tests that call `main()` must mock the new step too
- Rich library used for terminal output: `Console`, `Table`, `Text`, `Progress` from `rich`
- `display_results` accepts `output_console` parameter for test injection; defaults to module-level `console`
- CLI tests that call `main()` must patch `main.console` with a test Console writing to `io.StringIO`
- `STATUS_STYLES` dict maps `DomainStatus` → rich style strings (green/red/yellow)
- `_capture_console()` helper in tests creates `Console(file=buf, force_terminal=True, width=120)` for capturing rich output
- `export_results(results, path, domain_meta)` in `domain_search/exporter.py` — auto-detects .json/.csv from extension
- `domain_meta` dict carries `check_method` key ("DNS" or "RDAP") for export; set by main() after RDAP verification

---

## 2026-02-10 - US-001
- Implemented TLD list fetching from IANA (https://data.iana.org/TLD/tlds-alpha-by-domain.txt)
- Local file caching in `~/.cache/domain-search/tlds.txt` with 1-day max age
- Parses correctly: skips comments, lowercases, handles IDN/punycode TLDs
- Reports 1,437 TLDs found
- Files changed: `domain_search/__init__.py`, `domain_search/tld_list.py`, `main.py`, `tests/test_tld_list.py`, `pyproject.toml`
- **Learnings for future iterations:**
  - `uv init` creates a `main.py` with a hello-world stub - overwrite it
  - IANA TLD list has ~1,437 entries (comment line at top starting with `#`)
  - `httpx` is used for HTTP (async-capable for later stories)
  - `pytest-asyncio` added as dev dep for future async tests (US-002)
---

## 2026-02-10 - US-002
- Implemented async DNS availability checker in `domain_search/dns_checker.py`
- Checks NS and SOA records to classify domains as registered/available/unknown
- Uses `asyncio.Semaphore` for configurable concurrency (default 50)
- Handles timeouts gracefully (marks as "unknown")
- Files changed: `domain_search/dns_checker.py`, `tests/test_dns_checker.py`, `pyproject.toml`, `progress.md`, `prd.json`
- **Learnings for future iterations:**
  - When patching async functions in the same module, mock at the `dns.asyncresolver.Resolver` class level rather than patching `check_domain` directly (closure captures the function reference)
  - `dns.resolver.LifetimeTimeout` is a separate exception from `dns.exception.Timeout` — catch both for robust timeout handling
  - `dnspython` async resolver: use `resolver.resolve(domain, rdtype)` with await
  - `DomainStatus` enum and `DomainResult` dataclass provide clean typed results for downstream consumers (US-003, US-005, US-006)
---

## 2026-02-10 - US-003
- Implemented CLI argument parsing via `argparse` (positional `term`, optional `--concurrency`)
- Added `generate_domains(term, tlds)` to create `{term}.{tld}` for every TLD
- Added `sort_results()` to sort by status (available first, then unknown, then registered) then alphabetically
- Added `on_result` callback parameter to `check_domains()` for live progress updates
- Progress indicator shows `Checking N domains... [X/N]` with carriage-return updates
- Results displayed with summary: total, available, registered, unknown counts
- Files changed: `main.py`, `domain_search/dns_checker.py`, `tests/test_search.py`, `progress.md`, `prd.json`
- **Learnings for future iterations:**
  - `check_domains` `on_result` callback enables progress tracking without coupling display to DNS logic
  - For CLI tests, mock both `fetch_tld_list` and `check_domains` at the `main` module level (not at `domain_search.*`)
  - `sys.stdout.write` with `\r` provides simple progress indicator without needing `rich` (US-006 will upgrade)
  - `argparse` positional arg for `term` means `--hack` flag can be added later (US-004) without breaking existing interface
---

## 2026-02-10 - US-004
- Implemented domain hack generator in `domain_search/hack_generator.py`
- `find_suffix_hacks(word, tlds)` finds TLDs matching end of word (e.g., "kostick" → `kosti.ck`)
- `find_interior_hacks(word, tlds)` finds TLDs appearing within word, excluding suffix (e.g., "sasha" + "sh" → `sa.sh`)
- `generate_domain_hacks(word, tlds)` combines both, deduplicates, and sorts by domain name
- Updated CLI: `--hack WORD` flag activates domain hack mode; can combine with positional `term`
- `term` arg changed to `nargs="?"` (optional) so `--hack` can be used standalone
- Added `domain_meta` dict pattern in `main.py` for enriching display with type/visual info
- `display_results` auto-switches to wide format (Type + Visual Reading columns) when hacks present
- Files changed: `domain_search/hack_generator.py`, `main.py`, `tests/test_hack_generator.py`, `progress.md`, `prd.json`
- **Learnings for future iterations:**
  - Domain hack logic is pure string matching — no network calls, easy to test
  - Suffix hacks: check `word.endswith(tld)` with guard that prefix is non-empty
  - Interior hacks: use `str.find()` in a loop for multiple occurrences, exclude suffix position and position 0
  - `domain_meta` dict enriches DNS results without modifying `DomainResult` dataclass — keeps dns_checker independent
  - Changed `term` from required positional to `nargs="?"` optional, with custom validation `parser.error()` if neither term nor --hack provided
  - The `DomainHack` dataclass carries both `domain` (e.g., "kosti.ck") and `visual` (e.g., "kostick")
---

## 2026-02-10 - US-005
- Implemented RDAP availability verification in `domain_search/rdap_checker.py`
- Fetches IANA RDAP bootstrap (`https://data.iana.org/rdap/dns.json`) to map TLDs → RDAP server URLs
- Caches bootstrap locally at `~/.cache/domain-search/rdap_bootstrap.json` with 1-day expiry
- For "possibly available" domains, queries RDAP: HTTP 200 = registered, HTTP 404 = available, error = unknown
- Classifies RDAP responses by status array: "active"/locks → registered, "reserved" → registered, no data → registered
- Handles TLDs without RDAP servers gracefully (keeps DNS-only result)
- Token-bucket rate limiter (`_RateLimiter`) limits to 10 RDAP queries/second
- `--skip-rdap` CLI flag skips RDAP verification for faster results
- RDAP enabled by default with progress indicator during verification
- Updated existing CLI tests in `test_search.py` and `test_hack_generator.py` to mock `verify_available_domains`
- Files changed: `domain_search/rdap_checker.py`, `main.py`, `tests/test_rdap_checker.py`, `tests/test_search.py`, `tests/test_hack_generator.py`, `progress.md`, `prd.json`
- **Learnings for future iterations:**
  - Use `Callable` from `collections.abc`, not `callable` (builtin) for type hints with `|` union syntax
  - IANA RDAP bootstrap format: `{"services": [[tld_list, url_list], ...]}` — prefer HTTPS URLs, ensure trailing slash
  - RDAP domain query: GET `{rdap_url}domain/{domain}` — 200 = exists, 404 = not found
  - When adding new pipeline steps to `main()`, all existing CLI tests calling `main()` need to mock the new function
  - `httpx.AsyncClient` context manager mocking requires both `__aenter__` and `__aexit__` AsyncMock
  - Token-bucket rate limiter pattern: track tokens + last refill time, refill based on elapsed time, sleep when empty
---

## 2026-02-10 - US-006
- Replaced plain `print()` output with `rich` library for formatted terminal output
- Added `rich` dependency (>=13.0.0) to `pyproject.toml`
- `display_results()` now renders a `rich.Table` with "Domain Search Results" title
- Color-coded statuses: green (bold) for available, red for registered, yellow for unknown
- Available domains highlighted with bold green domain text for easy scanning
- Rich `Progress` bar with `BarColumn`, `MofNCompleteColumn`, `TimeRemainingColumn` for both DNS and RDAP stages
- `display_results` accepts optional `output_console` parameter for test output capturing
- Summary line uses `rich.Text` with styled segments for counts
- Updated all CLI integration tests across `test_search.py`, `test_hack_generator.py`, `test_rdap_checker.py` to patch `main.console`
- Added new `tests/test_rich_output.py` with 12 tests covering table structure, color coding, summary, sorting, and progress bar
- All 86 tests pass (12 new for US-006)
- Files changed: `main.py`, `pyproject.toml`, `tests/test_search.py`, `tests/test_hack_generator.py`, `tests/test_rdap_checker.py`, `tests/test_rich_output.py`, `progress.md`, `prd.json`
- **Learnings for future iterations:**
  - Rich `Console` output is not captured by `capsys` — must inject a `Console(file=StringIO, force_terminal=True)` for test capture
  - Use `force_terminal=True` in test Console to get ANSI codes and rich formatting in StringIO buffer
  - Patching `main.console` is needed for CLI integration tests since `main()` uses module-level `console` and `Progress(console=console)`
  - `display_results` DI pattern: `output_console` parameter for unit tests, `main.console` patching for integration tests
  - Removed `sys` import from `main.py` since `sys.stdout.write` progress was replaced by rich `Progress`
  - `STATUS_STYLES` dict centralizes color mapping, making it easy to test and modify
---

## 2026-02-10 - US-007
- Implemented export functionality in `domain_search/exporter.py`
- `export_results()` auto-detects format from file extension (.json or .csv)
- JSON export: array of objects with indent=2 formatting
- CSV export: DictWriter with header row
- Each row includes: domain, status, check_method (DNS/RDAP), type (exact/hack), timestamp (ISO 8601 UTC)
- Added `--output FILE` CLI flag to `main.py`
- RDAP-verified domains tracked via `check_method` key in `domain_meta` dict
- Default check_method is "DNS" when no meta provided
- Raises `ValueError` for unsupported file extensions
- 22 new tests in `tests/test_exporter.py` covering JSON export, CSV export, format detection, and CLI integration
- All 108 tests pass (22 new for US-007)
- Files changed: `domain_search/exporter.py`, `main.py`, `tests/test_exporter.py`, `progress.md`, `prd.json`
- **Learnings for future iterations:**
  - `_build_row()` helper centralizes row construction for both JSON and CSV exporters
  - `domain_meta` dict serves dual purpose: display enrichment (type/visual) and export metadata (check_method)
  - `rdap_checked` set in `main()` tracks which domains went through RDAP verification for accurate check_method reporting
  - `tmp_path` pytest fixture is ideal for file export tests — auto-cleaned, isolated per test
  - Case-insensitive extension matching via `.suffix.lower()` handles `.JSON`, `.CSV` etc.
---
