import os
import json
from datetime import datetime, timedelta

import gspread
from google.oauth2.service_account import Credentials

SPREADSHEET_ID = os.environ["SPREADSHEET_ID"]
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
HEADERS = ["user_id", "date", "kcal", "protein", "fat", "carbs", "foods"]


def _get_sheet():
    raw = os.environ["GOOGLE_CREDENTIALS"]
    info = json.loads(raw)
    creds = Credentials.from_service_account_info(info, scopes=SCOPES)
    client = gspread.authorize(creds)
    sh = client.open_by_key(SPREADSHEET_ID)
    try:
        return sh.worksheet("log")
    except gspread.WorksheetNotFound:
        ws = sh.add_worksheet(title="log", rows=5000, cols=7)
        ws.append_row(HEADERS)
        return ws


def today_key() -> str:
    return datetime.now().strftime("%d.%m.%Y")


def _find_row(ws, user_id: int, date_key: str) -> int | None:
    rows = ws.get_all_values()
    for i, row in enumerate(rows):
        if row and str(row[0]) == str(user_id) and row[1] == date_key:
            return i + 1  # 1-indexed
    return None


def add_entry(user_id: int, parsed: dict) -> dict:
    ws = _get_sheet()
    key = today_key()
    row_idx = _find_row(ws, user_id, key)
    if row_idx:
        row = ws.row_values(row_idx)
        kcal    = int(row[2] or 0) + parsed.get("kcal", 0)
        protein = int(row[3] or 0) + parsed.get("protein", 0)
        fat     = int(row[4] or 0) + parsed.get("fat", 0)
        carbs   = int(row[5] or 0) + parsed.get("carbs", 0)
        foods   = (row[6] + ", " if len(row) > 6 and row[6] else "") + ", ".join(parsed.get("foods", []))
        ws.update([[str(user_id), key, kcal, protein, fat, carbs, foods]], f"A{row_idx}:G{row_idx}")
    else:
        kcal    = parsed.get("kcal", 0)
        protein = parsed.get("protein", 0)
        fat     = parsed.get("fat", 0)
        carbs   = parsed.get("carbs", 0)
        foods   = ", ".join(parsed.get("foods", []))
        ws.append_row([str(user_id), key, kcal, protein, fat, carbs, foods])
    return {"kcal": kcal, "protein": protein, "fat": fat, "carbs": carbs, "foods": foods.split(", ")}


def get_day(user_id: int, date_key: str) -> dict | None:
    if date_key.count(".") == 1:
        date_key += "." + datetime.now().strftime("%Y")
    ws = _get_sheet()
    row_idx = _find_row(ws, user_id, date_key)
    if not row_idx:
        return None
    row = ws.row_values(row_idx)
    return {
        "kcal": int(row[2] or 0), "protein": int(row[3] or 0),
        "fat": int(row[4] or 0), "carbs": int(row[5] or 0),
        "foods": [f for f in row[6].split(", ") if f] if len(row) > 6 else [],
    }


def reset_today(user_id: int):
    ws = _get_sheet()
    row_idx = _find_row(ws, user_id, today_key())
    if row_idx:
        ws.delete_rows(row_idx)


def _all_rows_for(user_id: int, filter_fn) -> list[tuple[str, dict]]:
    ws = _get_sheet()
    rows = ws.get_all_values()
    result = []
    for row in rows[1:]:
        if not row or str(row[0]) != str(user_id) or not row[1] or not filter_fn(row[1]):
            continue
        result.append((row[1], {
            "kcal": int(row[2] or 0), "protein": int(row[3] or 0),
            "fat": int(row[4] or 0), "carbs": int(row[5] or 0),
            "foods": [f for f in row[6].split(", ") if f] if len(row) > 6 else [],
        }))
    return sorted(result, key=lambda x: datetime.strptime(x[0], "%d.%m.%Y"))


def get_week(user_id: int) -> list[tuple[str, dict]]:
    keys = {(datetime.now() - timedelta(days=i)).strftime("%d.%m.%Y") for i in range(7)}
    return _all_rows_for(user_id, lambda d: d in keys)


def get_month(user_id: int, month_str: str | None = None) -> list[tuple[str, dict]]:
    if not month_str:
        month_str = datetime.now().strftime("%m.%Y")
    mm, yyyy = month_str.split(".")
    return _all_rows_for(user_id, lambda d: len(d.split(".")) == 3 and d.split(".")[1] == mm and d.split(".")[2] == yyyy)


def get_year(user_id: int, year_str: str | None = None) -> list[tuple[str, dict]]:
    if not year_str:
        year_str = datetime.now().strftime("%Y")
    return _all_rows_for(user_id, lambda d: len(d.split(".")) == 3 and d.split(".")[2] == year_str)


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
