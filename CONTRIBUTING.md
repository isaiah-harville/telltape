# Contributing to telltape

## Prerequisites

- [uv](https://docs.astral.sh/uv/) (manages Python, the virtualenv, and deps)
- Git
- Python 3.12+ — uv will install a matching interpreter if you don't have one

## Setup

```bash
git clone https://github.com/isaiah-harville/telltape.git
cd telltape
uv sync            # create the venv and install runtime + dev dependencies
uv run telltape    # launch the app
```

`uv sync` installs the `dev` dependency group (ruff, ty). To build a standalone
binary the way releases do, also install the `build` group:

```bash
uv sync --group build
```

## Project layout

```
src/telltape/
├── cli.py         # Click entry point — launches the TUI
├── engine.py      # Orchestrates pollers → dedup → the headline sink
├── poller.py      # Per-source polling with conditional GET
├── feeds.py       # Built-in feed sources and feeds.toml read/write
├── dedup.py       # Fuzzy de-duplication of cross-posted stories
├── models.py      # Core types: FeedSource, Headline
├── render.py      # Headline → Rich Text for the tape
├── watchlist.py   # Ticker / company-name matching
├── companies.py   # SEC company-ticker table
├── config.py      # User settings and config.toml
├── paths.py       # Locations under ~/.telltape
├── tomlio.py      # Small TOML-writing helper
└── tui/           # Textual UI: app, settings, contact, quit screens

packaging/         # Nuitka entry point + macOS .app/notarization assets
.github/workflows/ # python.yml (lint + typecheck), release.yml (build/sign/publish)
```

## Before you open a PR

Run the same checks CI runs:

```bash
uv run ruff check .      # lint
uv run ruff format .     # format (or `--check` to verify only)
uv run ty check          # type check
```

There is no automated test suite yet. If you change behavior, please add tests
(pytest is the intended runner) and describe how you verified the change.

## Code style

Match the surrounding code:

- Google-style docstrings on public modules, classes, and functions.
- Comments explain **why**, not what — keep them where the intent isn't obvious.
- Keep network and other blocking work off the UI thread.

## Commits & pull requests

- Keep PRs focused; one logical change per PR.
- Write clear commit messages (imperative mood, e.g. "Add EDGAR S-1 feed").
- Reference any related issue, and note how you tested.

## Contributor license

telltape is currently **source-available** under the PolyForm Noncommercial
1.0.0 license, and the maintainer may release future versions under different
terms, including a commercial or proprietary license. So that this stays
possible, by submitting a contribution you agree that:

1. You are the original author of the contribution, or you otherwise have the
   right to submit it.
2. You license your contribution under the project's current license
   (PolyForm Noncommercial 1.0.0).
3. You additionally grant Isaiah Harville a perpetual, worldwide,
   non-exclusive, royalty-free, irrevocable license to use, reproduce, modify,
   sublicense, and **relicense** your contribution under any terms — including
   commercial or proprietary terms — as part of telltape or derivative works.

If you're contributing on behalf of an employer, make sure you have permission
to grant these rights. This section is not legal advice.
