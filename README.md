# telltape

Live, low-latency financial and world news headlines in your terminal, built for
traders who react to news fast.

It polls free financial wires (CNBC, MarketWatch, Yahoo Finance, Investing.com,
Seeking Alpha, and press-release wires), general world news that moves markets
(BBC, Al Jazeera, Guardian, NYT, NPR), and **SEC EDGAR real-time filings** —
concurrently and with conditional GET — then shows deduped headlines with their
publication age so you can see how fresh each item is.

## Run

```bash
uv run telltape
```

On first launch you are asked for a contact email (see below); it is stored so
you are not asked again.

In the app:

- **Sources** (left): click a source or press its number key (1-9) to toggle it.
  `a` enables all, `x` disables all.
- **Settings** (`s`): set your contact email, the theme, an age filter, a
  watchlist, and a highlight keyword. The theme previews live as you pick it.
- `p` pauses the tape, `c` clears it, `q` quits.

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
