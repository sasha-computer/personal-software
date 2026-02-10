# Domain Search

A Python CLI tool that searches for available domain names across all known TLDs. For any given word, it runs both **exact search** (e.g., `creative.dev`, `creative.computer`) and **domain hack search** (where the TLD forms part of the word, e.g., `creati.ve`). Uses free protocols (DNS lookups and RDAP) requiring no API keys.

## Requirements

- Python 3.12+
- [uv](https://docs.astral.sh/uv/) package manager

## Installation

### Option 1: Run without installing (recommended for quick use)

```bash
uvx domain-search <word>
```

### Option 2: Install globally with uv tool

```bash
uv tool install domain-search
domain-search <word>
```

### From source (development)

```bash
git clone <repo-url>
cd domain-search
uv sync
uv run domain-search <word>
```

The CLI is exposed via `project.scripts` (`domain_search.cli:main`).  
Use the `domain-search` command; direct `python main.py` invocation is not supported.

## Usage

This searches for `<word>.{tld}` across all known TLDs (exact matches) and also finds domain hacks where the TLD forms part of the word. For example:

```bash
uvx domain-search creative
# or, if installed globally:
domain-search creative
```

Returns exact matches like `creative.com`, `creative.dev` as well as hacks like `creati.ve` (reads as "creative").

### Options

| Flag | Description |
|------|-------------|
| `--concurrency N` | Max concurrent DNS lookups (default: 50) |
| `--skip-rdap` | Skip RDAP verification (faster but less accurate) |
| `--output FILE` | Export results to `.json`, `.jsonl`, or `.csv` file |
| `--tld TLD [TLD ...]` | Filter to specific TLDs (e.g., `--tld com io ve`) |

### Export Results

Export to JSON, JSONL, or CSV (format auto-detected from file extension):

```bash
uvx domain-search creative --output results.json
uvx domain-search creative --output results.jsonl
uvx domain-search creative --output results.csv
```

### Show Help

```bash
uvx domain-search --help
# or, if installed globally:
domain-search --help
```

## How It Works

1. **TLD List**: Fetches the complete TLD list from IANA (~1,500 TLDs), cached locally for 24 hours
2. **DNS Check**: Performs async DNS lookups (NS/SOA records) to classify domains as registered, possibly available, or unknown
3. **RDAP Verification**: For "possibly available" domains, queries RDAP servers for confirmation (skippable with `--skip-rdap`)
4. **Results**: Displays a color-coded table with availability status, sorted with available domains first

## Running Tests

```bash
uv run pytest tests/ -v
```

## Code Quality

Run linting, formatting, and type checking locally:

```bash
uv run ruff check .
uv run ruff format .
uv run ty check --error-on-warning
```

Install and run pre-commit hooks:

```bash
uv run pre-commit install
uv run pre-commit run --all-files
```

This project uses strict lint and type-check settings. Expect checks to require
clear type annotations and clean imports.

## Special Contributions

- [Chief](https://github.com/MiniCodeMonkey/chief/tree/main)