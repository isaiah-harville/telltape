# TODO

## LLM integration (design options)

Traders increasingly run model-assisted workflows. Possible hooks, roughly in
order of effort:

1. **On-demand summarize / classify (simplest).** A keybinding on a selected
   headline that calls a model to summarize, label sentiment, or extract the
   affected tickers. Synchronous, one call per request.
2. **Streaming triage.** Each new headline is scored by a model for
   market-relevance and sentiment, used to highlight or filter the tape. Needs
   batching and rate-limiting to control cost and latency; only viable for
   filtered subsets, not the full firehose.
3. **Watchlist agent.** A background agent watches the tape for a user's thesis
   ("anything that affects semiconductor supply") and posts alerts. Highest
   value, highest complexity.

Implementation notes:
- Keep it provider-agnostic behind a small `llm` interface; let users pick a
  provider and supply their own API key via config (same pattern as the contact
  email). Never ship a default key.
- Latency matters here: model calls are far slower than feed polling, so they
  must run off the ingestion path (background workers) and never block the tape.
- Cost control: cap concurrent calls, dedup before calling, and make any
  always-on scoring opt-in.

## Deferred data sources

- **SearXNG search** as a secondary "broader chatter" lookup (not the live tape;
  search indexes lag publication). Self-host, hit the JSON API, restrict to news
  engines, sort by date.
- **Paid streaming / WebSocket news** (Benzinga, Polygon, Alpaca) for
  millisecond-class delivery. A persistent connection feeding the same engine
  queue; dedup across sources via the existing title matching. Requires API keys
  and a paid subscription, kept behind config.
- **Reuters / AP**: public RSS was retired; needs a proxy or licensed feed.
