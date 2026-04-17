# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Running the bot

```bash
pip install -r requirements.txt
python bot.py
```

## Architecture

Single-file-per-concern structure:

- **bot.py** — Telegram handlers and command routing. All user-facing logic lives here.
- **claude_api.py** — Calls Anthropic claude-haiku to parse free-text food descriptions into `{kcal, protein, fat, carbs, foods}` JSON.
- **storage.py** — Google Sheets backend via `gspread`. Each row = one day (`dd.mm.yyyy`). Sheet name: `log`. Functions: `add_entry`, `get_day`, `get_week`, `get_month`, `get_year`, `reset_today`, `format_entry`, `format_period_summary`.

## Environment variables

| Variable | Description |
|---|---|
| `TELEGRAM_TOKEN` | BotFather token |
| `ANTHROPIC_API_KEY` | Anthropic API key |
| `GOOGLE_CREDENTIALS` | Full JSON content of Google service account key file |
| `SPREADSHEET_ID` | Google Sheets document ID |

## Deployment

Deployed as a Railway **worker** (not web service). `Procfile` defines `worker: python bot.py`. Auto-deploys on push to `master` via GitHub integration.

## Google Sheets structure

Worksheet `log` columns: `date | kcal | protein | fat | carbs | foods`

Date format stored as `dd.mm.yyyy`. Display format (in bot messages) is `dd.mm`.
