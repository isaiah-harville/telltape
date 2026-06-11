# telltape

**Live, low-latency financial and world news headlines in your terminal — built for traders who react to news fast.**

[![License: PolyForm Noncommercial 1.0.0](https://img.shields.io/badge/license-PolyForm%20Noncommercial%201.0.0-blue)](LICENSE)
[![Latest release](https://img.shields.io/github/v/release/isaiah-harville/telltape?label=release)](https://github.com/isaiah-harville/telltape/releases/latest)
[![Python 3.12+](https://img.shields.io/badge/python-3.12%2B-blue)](https://www.python.org/)
[![CI](https://github.com/isaiah-harville/telltape/actions/workflows/python.yml/badge.svg)](https://github.com/isaiah-harville/telltape/actions/workflows/python.yml)

telltape polls free financial wires, market-moving world news, and **SEC EDGAR
real-time filings** concurrently, deduplicates the cross-posted noise, and
streams what's left as a single live tape — each line tagged with how fresh it
is, so you can see at a glance whether a story is seconds or hours old.

```text
┌─ Live tape ───────────────────────────────────────────────────────────────┐
│ 14:32:07   12s  CNBC Markets         Fed holds rates steady, signals one …  │
│ 14:32:05    3s  EDGAR 8-K            TESLA INC files Form 8-K                │
│ 14:31:58   40s  Reuters              Oil slips as supply concerns ease       │
│ ● 14:31:50  1m  MarketWatch          Apple recalls some units  $AAPL         │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Features

- **One fast tape.** Financial wires (CNBC, MarketWatch, Yahoo Finance,
  Investing.com, Seeking Alpha, PR/GlobeNewswire), world news that moves markets
  (BBC, Al Jazeera, Guardian, NYT, NPR), and **SEC EDGAR 8-K / all filings** in
  real time.
- **Low latency.** Sources are polled concurrently with conditional GET, on
  per-source intervals, off the UI thread.
- **Deduplicated.** The same story across multiple wires collapses to one line
  via fuzzy title matching.
- **Freshness at a glance.** Every headline shows its age (seconds → hours).
- **Watchlist & alerts.** Filter to the tickers and companies you care about
  (resolved against the SEC company list), highlight a keyword, and get a
  bell + notification on alert matches.
- **Yours to shape.** Toggle sources by click or number key, rebind those number
  keys, pick a theme, and edit the feed list directly.
- **Open a source.** Double-click a headline to open the article in your browser.

## Install

### Prebuilt binaries

Grab the asset for your platform from the [latest release](https://github.com/isaiah-harville/telltape/releases):

| Platform | Asset |
| --- | --- |
| macOS (Apple Silicon) | `telltape-macos-arm64.dmg` (drag-to-Applications installer) or `telltape-macos-arm64` (raw binary) |
| Linux (x86_64) | `telltape-linux-x86_64` |
| Linux (arm64) | `telltape-linux-arm64` |
| Windows (x86_64) | `telltape-windows-x86_64.exe` |

The macOS `.dmg` installs an app into `/Applications` that opens telltape in
Terminal (a TUI needs a terminal); the signed/notarized build launches without
Gatekeeper prompts. The raw binaries run straight from a terminal:

```bash
chmod +x telltape-linux-x86_64
./telltape-linux-x86_64
```

### From source

telltape uses [uv](https://docs.astral.sh/uv/). With it installed:

```bash
git clone https://github.com/isaiah-harville/telltape.git
cd telltape
uv run telltape
```

`uv run` creates the virtual environment, installs dependencies, and launches the
app. Python 3.12+ is required (uv will fetch it if needed).

## Usage

On first launch you're asked for a **contact email** (see below); it's stored so
you're only asked once. Then:

| Key | Action |
| --- | --- |
| `1`–`9` | Toggle a source on/off (assignable in Settings) |
| click | Toggle a source, or double-click a headline to open it |
| `a` / `x` | Enable all / disable all sources |
| `s` | Settings (contact email, theme, filters, alerts, key bindings) |
| `t` | Pause / resume the tape |
| `c` | Clear the tape |
| `q` | Quit (with confirmation) |

## Configuration

### Contact email

Data providers — the SEC in particular — expect a contact in the request
User-Agent and may throttle a contact shared across many clients. Set your own
email in **Settings**; it's stored locally and used only for attribution. SEC
filings and the company watchlist require it.

### Watchlist & alerts

The **watchlist** accepts tickers or company names (e.g. `AAPL, Tesla, oil`).
Names and tickers are resolved against the SEC company list, so a headline
matches when it mentions the company by name or cashtag; unresolved terms match
as plain text. **Alerts** work the same way but additionally ring the bell and
raise a notification, and alert matches always show even if the watchlist would
hide them.

### Feeds

The source list lives in `~/.telltape/feeds.toml`, created on first run. Edit it
to add, remove, or reorder sources, then restart. Each source looks like:

```toml
[[feed]]
name = "CNBC Top News"
url = "https://www.cnbc.com/id/100003114/device/rss/rss.html"
category = "news"      # news | world | filing
interval = 15.0        # seconds between polls
default_on = true      # whether it starts enabled
```

If the file is missing or invalid, the built-in defaults are used.

### Files

Everything telltape stores lives in `~/.telltape`:

- `config.toml` — settings (contact email, theme, alert sound, key bindings).
  App-managed but human-readable.
- `feeds.toml` — the source list above.
- `company_tickers.json` — cached SEC company list.

If a config file exists but can't be parsed, telltape notifies you and falls back
to defaults without overwriting your file.

## How it works

A pool of pollers fetches each feed on its own interval (conditional GET to avoid
re-downloading unchanged feeds), normalizes entries into headlines, and pushes
them through a deduplicator into the live tape. The UI is a [Textual](https://textual.textualize.io)
app; everything network-bound runs off the render thread so the tape stays
responsive. Released binaries are compiled with [Nuitka](https://nuitka.net).

## Contributing

Contributions are welcome — see [CONTRIBUTING.md](CONTRIBUTING.md) for setup,
project layout, and the checks to run before opening a PR.

## License

telltape is **source-available** under the [PolyForm Noncommercial 1.0.0](LICENSE)
license: you may use, modify, and share it for **noncommercial** purposes.
Commercial use requires a separate license — open an issue or contact the
maintainer to arrange one.
