# Competitor Monitor

Internal tool for automated competitor monitoring across European e-commerce markets.
Tracks prices, promotions, and narrative shifts for selected competitors — replacing manual weekly observation by the e-commerce team.

## Architecture (Phase 0 skeleton)

```
competitor_monitor/
├── config/          # Settings, competitor definitions, market configs
├── crawler/         # Playwright-based web crawler (JS-heavy sites, anti-bot)
├── extractors/      # Claude-powered structured data extraction
│   ├── price_extractor.py   # SKU price + stock status
│   └── promo_extractor.py   # Homepage banners + campaigns
├── detectors/       # Change detection + importance scoring (HIGH/MEDIUM/LOW)
├── reporters/       # HTML email digest
├── scheduler/       # Full monitoring cycle orchestration
└── storage/         # SQLAlchemy models + async SQLite/PostgreSQL
```

## Quick start

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
playwright install chromium

cp .env.example .env
# Edit .env — set ANTHROPIC_API_KEY, email settings, competitors
```

Add your competitors and SKUs in `competitor_monitor/config/settings.py` (COMPETITORS list).

```bash
# Initialise the database
python main.py initdb

# Run one monitoring cycle now (output goes to email or stdout)
python main.py run

# Start the daily scheduler (default: 07:00)
python main.py schedule
```

## Phases

| Phase | Scope |
|-------|-------|
| **0 (current)** | Architecture skeleton, crawler, LLM extractors, change detection, email |
| **1** | 2 German competitors, 10–20 SKUs, validated against bigboxx.de manual reports |
| **2** | New/discontinued products, blog monitoring, web dashboard, noise scoring |
| **3** | Narrative analysis, AI executive summaries, Google/Meta ad monitoring |
| **4** | Multi-market (PL, NL, AT, BE), cross-country comparisons |

## Key design decisions

- **LLM extraction over CSS selectors** — Claude reads page text semantically, so layout changes on competitor sites don't break the extractor.
- **Importance scoring** — every detected change is rated HIGH / MEDIUM / LOW to filter noise before delivery.
- **Reliability over features** — each phase is independently useful; new features are added only after previous ones are stable.
