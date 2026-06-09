# Changelog

## v1.0.0 — 2026-06-09

Initial release of FAANG-Robotrader.

### Features

- **Automated trading engine** — `trading_logic.py` fetches daily OHLCV prices and trend predictions from the FAANG Pulse AI API and executes BUY / SELL / HOLD decisions for each investor × stock pair.
- **Four investor personas** — each with a distinct risk profile and fixed share quantities:
  - *Safe Sam* — conservative (threshold −0.135, BUY 50 / SELL 100)
  - *Optimal Owen* — balanced (threshold 0.0, BUY 20 / SELL 20)
  - *Brave Beth* — aggressive (threshold 0.045, BUY 10 / SELL 10)
  - *Random Randy* — deterministic random baseline for benchmarking ML model value
- **Gradio dashboard** — `app.py` serves three views: Trade Actions Summary, Cash Status (portfolio value and ROI), and Per Stock Returns.
- **Persistent trade logs** — one CSV file per investor under `data/`, appended after every trading session.
- **GitHub Actions automation**:
  - `daily_cron.yml` — triggers at 22:00 UTC on weekdays, runs the trading engine, and commits updated CSVs.
  - `sync_to_hf.yml` — mirrors the repository to the Hugging Face Space on every push to `main`.
- **Multi-layer retry for transient timeouts** — `_with_retry()` in Python (3 attempts, 30 s gap) combined with a bash retry loop in CI (3 attempts, 60 s gap) to handle HF Space cold-start latency.
- **Log upload after each live run** — `TradingEngine.upload_logfile()` pushes the session log to the HF Space `/upload_logfile` endpoint for remote observability.
- **Duplicate-prevention guard** — strategies skip insertion if a row already exists for the same date + ticker combination.
- **HOLD fallback** — any BUY or SELL that would exceed available cash or shares automatically falls back to HOLD.
