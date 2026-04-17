import json
import os
from datetime import datetime, timedelta

LOG_FILE = os.environ.get("LOG_FILE", "log.json")


def _load() -> dict:
    if not os.path.exists(LOG_FILE):
        return {}
    with open(LOG_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def _save(data: dict):
    with open(LOG_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def today_key() -> str:
    return datetime.now().strftime("%d.%m.%Y")


def add_entry(parsed: dict):
    data = _load()
    key = today_key()
    if key not in data:
        data[key] = {"kcal": 0, "protein": 0, "fat": 0, "carbs": 0, "foods": []}
    entry = data[key]
    entry["kcal"] += parsed.get("kcal", 0)
    entry["protein"] += parsed.get("protein", 0)
    entry["fat"] += parsed.get("fat", 0)
    entry["carbs"] += parsed.get("carbs", 0)
    entry["foods"].extend(parsed.get("foods", []))
    _save(data)
    return entry


def get_day(date_key: str) -> dict | None:
    data = _load()
    # support both dd.mm and dd.mm.yyyy
    if date_key in data:
        return data[date_key]
    year = datetime.now().strftime("%Y")
    return data.get(f"{date_key}.{year}")


def reset_today():
    data = _load()
    key = today_key()
    if key in data:
        del data[key]
        _save(data)


def get_week() -> list[tuple[str, dict]]:
    data = _load()
    result = []
    for i in range(6, -1, -1):
        day = (datetime.now() - timedelta(days=i)).strftime("%d.%m.%Y")
        if day in data:
            result.append((day, data[day]))
    return result


def get_month(month_str: str | None = None) -> list[tuple[str, dict]]:
    """month_str format: 'mm.yyyy' or None for current month"""
    data = _load()
    if month_str is None:
        month_str = datetime.now().strftime("%m.%Y")
    result = []
    for key, entry in sorted(data.items()):
        # key is dd.mm.yyyy
        parts = key.split(".")
        if len(parts) == 3 and f"{parts[1]}.{parts[2]}" == month_str:
            result.append((key, entry))
    return result


def get_year(year_str: str | None = None) -> list[tuple[str, dict]]:
    """year_str format: 'yyyy' or None for current year"""
    data = _load()
    if year_str is None:
        year_str = datetime.now().strftime("%Y")
    result = []
    for key, entry in sorted(data.items()):
        parts = key.split(".")
        if len(parts) == 3 and parts[2] == year_str:
            result.append((key, entry))
    return result


def _aggregate(entries: list[tuple[str, dict]]) -> dict:
    total = {"kcal": 0, "protein": 0, "fat": 0, "carbs": 0}
    for _, e in entries:
        for field in total:
            total[field] += e.get(field, 0)
    return total


def format_entry(date_key: str, entry: dict) -> str:
    # show only dd.mm in display
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
