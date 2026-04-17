import os
import json
from datetime import datetime, timedelta

import gspread
from google.oauth2.service_account import Credentials

SPREADSHEET_ID = os.environ["SPREADSHEET_ID"]
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
HEADERS = ["date", "kcal", "protein", "fat", "carbs", "foods"]


def _get_sheet():
    raw = os.environ["GOOGLE_CREDENTIALS"]
    info = json.loads(raw)
    creds = Credentials.from_service_account_info(info, scopes=SCOPES)
    client = gspread.authorize(creds)
    sh = client.open_by_key(SPREADSHEET_ID)
    try:
        return sh.worksheet("log")
    except gspread.WorksheetNotFound:
        ws = sh.add_worksheet(title="log", rows=1000, cols=6)
        ws.append_row(HEADERS)
        return ws


def today_key() -> str:
    return datetime.now().strftime("%d.%m.%Y")


def _find_row(ws, date_key: str):
    col = ws.col_values(1)
    for i, val in enumerate(col):
        if val == date_key:
            return i + 1  # 1-indexed
    return None


def add_entry(parsed: dict):
    ws = _get_sheet()
    key = today_key()
    row_idx = _find_row(ws, key)
    if row_idx:
        row = ws.row_values(row_idx)
        kcal    = int(row[1] or 0) + parsed.get("kcal", 0)
        protein = int(row[2] or 0) + parsed.get("protein", 0)
        fat     = int(row[3] or 0) + parsed.get("fat", 0)
        carbs   = int(row[4] or 0) + parsed.get("carbs", 0)
        foods   = (row[5] + ", " if row[5] else "") + ", ".join(parsed.get("foods", []))
        ws.update(f"A{row_idx}:F{row_idx}", [[key, kcal, protein, fat, carbs, foods]])
    else:
        kcal    = parsed.get("kcal", 0)
        protein = parsed.get("protein", 0)
        fat     = parsed.get("fat", 0)
        carbs   = parsed.get("carbs", 0)
        foods   = ", ".join(parsed.get("foods", []))
        ws.append_row([key, kcal, protein, fat, carbs, foods])
    return {"kcal": kcal, "protein": protein, "fat": fat, "carbs": carbs, "foods": foods.split(", ")}


def get_day(date_key: str) -> dict | None:
    ws = _get_sheet()
    # support dd.mm → add current year
    if date_key.count(".") == 1:
        date_key += "." + datetime.now().strftime("%Y")
    row_idx = _find_row(ws, date_key)
    if not row_idx:
        return None
    row = ws.row_values(row_idx)
    return {
        "kcal": int(row[1] or 0), "protein": int(row[2] or 0),
        "fat": int(row[3] or 0), "carbs": int(row[4] or 0),
        "foods": [f for f in row[5].split(", ") if f] if len(row) > 5 else [],
    }


def reset_today():
    ws = _get_sheet()
    row_idx = _find_row(ws, today_key())
    if row_idx:
        ws.delete_rows(row_idx)


def _all_rows_for(filter_fn) -> list[tuple[str, dict]]:
    ws = _get_sheet()
    rows = ws.get_all_values()
    result = []
    for row in rows[1:]:  # skip header
        if not row or not row[0] or not filter_fn(row[0]):
            continue
        result.append((row[0], {
            "kcal": int(row[1] or 0), "protein": int(row[2] or 0),
            "fat": int(row[3] or 0), "carbs": int(row[4] or 0),
            "foods": [f for f in row[5].split(", ") if f] if len(row) > 5 else [],
        }))
    return sorted(result, key=lambda x: datetime.strptime(x[0], "%d.%m.%Y"))


def get_week() -> list[tuple[str, dict]]:
    keys = {(datetime.now() - timedelta(days=i)).strftime("%d.%m.%Y") for i in range(7)}
    return _all_rows_for(lambda d: d in keys)


def get_month(month_str: str | None = None) -> list[tuple[str, dict]]:
    if not month_str:
        month_str = datetime.now().strftime("%m.%Y")
    mm, yyyy = month_str.split(".")
    return _all_rows_for(lambda d: len(d.split(".")) == 3 and d.split(".")[1] == mm and d.split(".")[2] == yyyy)


def get_year(year_str: str | None = None) -> list[tuple[str, dict]]:
    if not year_str:
        year_str = datetime.now().strftime("%Y")
    return _all_rows_for(lambda d: len(d.split(".")) == 3 and d.split(".")[2] == year_str)


def _aggregate(entries):
    total = {"kcal": 0, "protein": 0, "fat": 0, "carbs": 0}
    for _, e in entries:
        for f in total:
            total[f] += e.get(f, 0)
    return total


def format_entry(date_key: str, entry: dict) -> str:
    display = ".".join(date_key.split(".")[:2])
    foods = ", ".join(entry["foods"]) if entry["foods"] else "—"
    return (
        f"📅 {display}\n"
        f"🔥 {entry['kcal']} ккал\n"
        f"Б: {entry['protein']}г | Ж: {entry['fat']}г | В: {entry['carbs']}г\n"
        f"🍽 {foods}"
    )


def format_period_summary(label: str, entries: list[tuple[str, dict]]) -> str:
    if not entries:
        return f"Нема записів за {label}."
    days = len(entries)
    total = _aggregate(entries)
    avg_kcal = total["kcal"] // days
    lines = [
        f"📊 {label} — {days} дн.",
        f"Всього: {total['kcal']} ккал | В середньому: {avg_kcal} ккал/день",
        f"Б: {total['protein']}г | Ж: {total['fat']}г | В: {total['carbs']}г",
        "",
    ]
    for key, entry in entries:
        display = ".".join(key.split(".")[:2])
        lines.append(f"  {display}: {entry['kcal']} ккал")
    return "\n".join(lines)
