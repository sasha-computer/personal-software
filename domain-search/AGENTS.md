# AGENTS.md

This file is for coding agents and maintainers. The public-facing quickstart lives in `README.md`.

## Project Snapshot

- Package: `domain-search`
- Python: `>=3.12`
- Entry point: `domain-search` -> `domain_search.cli:main`
- Build backend: `hatchling`
- Runtime deps: `dnspython`, `httpx`, `rich`

## Architecture

- `domain_search/cli.py`
  - Parses CLI args.
  - Loads TLD list.
  - Generates exact domains and domain hacks.
  - Runs DNS checks, optional RDAP verification, and rendering/export.
- `domain_search/tld_list.py`
  - Fetches and caches IANA TLD list.
- `domain_search/hack_generator.py`
  - Produces domain-hack candidates and display metadata.
- `domain_search/dns_checker.py`
  - Async DNS classification (registered/available/unknown).
- `domain_search/rdap_checker.py`
  - RDAP verification for possibly available domains.
- `domain_search/exporter.py`
  - Writes `.json`, `.jsonl`, `.csv` output.
- `domain_search/types.py`
  - Shared typing models.

## Search Pipeline Behavior

1. Build candidates from both exact and hack generation.
2. De-duplicate candidates while preserving per-domain metadata.
3. DNS check all candidates with configurable concurrency (`--concurrency`, default `50`).
4. If `--skip-rdap` is not set, verify only `AVAILABLE` DNS results via RDAP.
5. Render rich table and optional export file.

## CLI Contract

Primary command:

```bash
domain-search <term> [flags]
```

Current flags:

- `--concurrency N`
- `--skip-rdap`
- `--output FILE` (`.json`, `.jsonl`, `.csv`)
- `--tld TLD [TLD ...]`

Notes:

- `--tld` values are normalized to lowercase.
- Invalid TLDs are warned and skipped.
- If all provided TLDs are invalid, command exits early with an error message.

## Local Development

Install dependencies:

```bash
uv sync
```

Run from source:

```bash
uv run domain-search creative
```

Run tests:

```bash
uv run pytest tests/ -v
```

## Quality Gates

Run all checks locally:

```bash
uv run ruff check .
uv run ruff format .
uv run ty check --error-on-warning
uv run pytest tests/ -v
```

Pre-commit:

```bash
uv run pre-commit install
uv run pre-commit run --all-files
```

This repo uses strict lint/type settings. Keep annotations explicit and imports clean.

## Agent Editing Guidance

- Keep user-facing docs concise in `README.md`; place deeper implementation notes here.
- Preserve status semantics (`AVAILABLE`, `UNKNOWN`, `REGISTERED`) unless intentionally changing behavior.
- If changing export schema or table columns, update tests in `tests/test_exporter.py` and `tests/test_rich_output.py`.
- Favor additive changes and avoid breaking CLI flags without migration notes.

## Contributing

- Use the PR template at `.github/PULL_REQUEST_TEMPLATE.md`.
- Keep PRs focused and include a short test plan.

## Agent File Sync

- `AGENTS.md` and `CLAUDE.md` must remain identical.
- When updating one, copy the same content to the other in the same change.

## Security Disclaimer

This is a small CLI utility focused on domain discovery and is not designed as a security-critical system. No dedicated security policy is maintained for this repository at this time.
