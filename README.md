# telltape

Live, low-latency financial and world news headlines in your terminal, built for
traders who react to news fast.

It polls free financial wires (CNBC, MarketWatch, Yahoo Finance, Investing.com,
Seeking Alpha, and press-release wires), general world news that moves markets
(BBC, Al Jazeera, Guardian, NYT, NPR), and **SEC EDGAR real-time filings** —
concurrently and with conditional GET — then shows deduped headlines with their
publication age so you can see how fresh each item is.

## Install

Each `v*` tag builds these assets via [release.yml](.github/workflows/release.yml):

| Platform | Asset |
| --- | --- |
| macOS (Apple Silicon) | `telltape-macos-arm64.dmg` (drag-to-Applications installer) or `telltape-macos-arm64` (raw binary) |
| Linux (x86_64) | `telltape-linux-x86_64` |
| Linux (arm64) | `telltape-linux-arm64` |
| Windows (x86_64) | `telltape-windows-x86_64.exe` |

The raw binaries run from a terminal — `chmod +x telltape-macos-arm64 && ./telltape-macos-arm64`.
The macOS `.dmg` installs an app into `/Applications`; because a TUI needs a
terminal, the app opens Terminal.app running telltape. With the Apple Developer
ID secrets configured the app and DMG are signed and notarized, so they launch
without Gatekeeper warnings.

The binaries are compiled with [Nuitka](https://nuitka.net) (Python → C → native
machine code), so the shipped executable contains no recoverable Python source.

## Run

From source:

```bash
uv run telltape
```

On first launch you are asked for a contact email (see below); it is stored so
you are not asked again.

In the app:

- **Sources** (left): click a source or press its number key (1-9) to toggle it.
  Assign which source each number key controls in **Settings**; by default they
  map to the first nine sources in order. `a` enables all, `x` disables all.
- **Settings** (`s`): set your contact email, the theme, an age filter, a
  watchlist, and a highlight keyword. The theme previews live as you pick it.
- `t` pauses the tape, `c` clears it, `q` quits.

## Contact email

Data providers (the SEC in particular) expect a contact in the request
User-Agent and may throttle a contact shared across many clients. Set your own
email in **Settings**; it is stored locally and used only for attribution. SEC
filings and the company watchlist require it.

## Files

Everything telltape stores lives in `~/.telltape`:

- `config.toml` — settings (contact email, theme, alert sound). App-managed, but
  human-readable.
- `feeds.toml` — the source list (see below).
- `company_tickers.json` — cached SEC company list.

If a config file exists but cannot be parsed, telltape notifies you and falls
back to the defaults without overwriting your file.

## Feeds

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

## Watchlist filters

The watchlist accepts tickers or company names (e.g. `AAPL, Tesla, oil`). Names
and tickers are resolved against the SEC company list, so a headline matches when
it mentions the company by name or cashtag. Terms that do not resolve to a
company are matched as plain text.
