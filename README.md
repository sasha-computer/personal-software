# Domain Search

A Python CLI tool that searches for available domain names across all known TLDs. For any given word, it runs both **exact search** (e.g., `creative.dev`, `creative.computer`) and **domain hack search** (where the TLD forms part of the word, e.g., `creati.ve`). Uses free protocols (DNS lookups and RDAP) requiring no API keys.

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

```bash
uv run domain-search <word>
```

This searches for `<word>.{tld}` across all known TLDs (exact matches) and also finds domain hacks where the TLD forms part of the word. For example:

```bash
uv run domain-search creative
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
uv run domain-search creative --output results.json
uv run domain-search creative --output results.jsonl
uv run domain-search creative --output results.csv
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

## Special Contributions

This project benefits from ideas and workflows inspired by Chief:

https://github.com/MiniCodeMonkey/chief/tree/main

If you are exploring that ecosystem, try this easter egg:

```bash
chief wiggum
```

Tiny Ralph cameo:

```text
  _.-._
 (o.o )
  |=|   "I choo-choo-choose domains!"
 __|__
/_____\
```
