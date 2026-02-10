# Domain Search

A Python CLI tool that searches for available domain names across all known TLDs. It supports two modes: **exact search** (e.g., `sasha.computer`, `sasha.dev`) and **domain hack search** (where the TLD forms part of a word, e.g., `kosti.ck`). Uses free protocols (DNS lookups and RDAP) requiring no API keys.

## Requirements

- Python 3.12+
- [uv](https://docs.astral.sh/uv/) package manager

## Installation

```bash
git clone <repo-url>
cd domain-search
uv sync
```

## Usage

### Exact Search

Search for `sasha.{tld}` across all known TLDs:

```bash
uv run python main.py sasha
```

### Domain Hack Search

Find creative domain hacks where the TLD forms part of a word:

```bash
uv run python main.py --hack kostick
```

This finds domains like `kosti.ck` (reads as "kostick").

### Combined Search

Run both exact and hack search together:

```bash
uv run python main.py sasha --hack kostick
```

### Options

| Flag | Description |
|------|-------------|
| `--hack WORD` | Find domain hacks for the given word |
| `--concurrency N` | Max concurrent DNS lookups (default: 50) |
| `--skip-rdap` | Skip RDAP verification (faster but less accurate) |
| `--output FILE` | Export results to `.json` or `.csv` file |

### Export Results

Export to JSON or CSV (format auto-detected from file extension):

```bash
uv run python main.py sasha --output results.json
uv run python main.py sasha --output results.csv
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
