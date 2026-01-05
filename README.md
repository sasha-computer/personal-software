# Plain Text Running Tracker

Parse Apple Health exports and Garmin FIT files into a simple markdown running log.

## Setup

```bash
uv sync
```

## Usage

```bash
uv run python running_tracker.py
```

This parses `apple/export.xml` and `garmin/*.fit` files, then outputs to `runs.md`.

## Tests

```bash
uv run pytest
```
