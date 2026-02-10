# Domain Search

![domain-search CLI demo](assets/domain-search-demo.gif)

- Search for available domains across basically every TLD. 
- No API keys, no paid service required. 
- This tool uses DNS + RDAP checks in a fast CLI.

## Quick Start

Requirements:
- Python 3.12+
- [uv](https://docs.astral.sh/uv/)

First run instantly (no install):

```bash
git clone https://github.com/sasha-computer/domain-search
cd domain-search
uvx domain-search creative
```

Or install once:

```bash
uv tool install domain-search
domain-search creative
```

## Useful Commands

Basic search:

```bash
domain-search creative
```

Search only specific TLDs:

```bash
domain-search creative --tld com io dev ve
```

Skip RDAP for speed (less accurate):

```bash
domain-search creative --skip-rdap
```

Export results:

```bash
domain-search creative --output results.json
domain-search creative --output results.jsonl
domain-search creative --output results.csv
```

Help:

```bash
domain-search --help
```

## How It Searches

For a term like `creative`, the CLI does two passes:

1. **Exact candidates**: `creative.com`, `creative.dev`, etc.
2. **Domain hacks**: `creati.ve` style splits where the TLD completes the word.

Then it checks candidates in stages:

1. Loads the full IANA TLD list (cached locally).
2. Runs async DNS checks to quickly classify candidates.
3. Verifies possibly-available domains with RDAP (unless `--skip-rdap`).
4. Prints a table sorted with available domains first.

## From Source

```bash
git clone <repo-url>
cd domain-search
uv sync
uv run domain-search creative
```
