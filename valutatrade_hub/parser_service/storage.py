from valutatrade_hub.infra.database import DatabaseManager


def save_rates(pairs, last_refresh):
    """Обновить rates.json."""
    db = DatabaseManager()
    data = db.load_rates()
    current = data.get("pairs", {})
    for pair, value in pairs.items():
        old = current.get(pair)
        if old is None or value["updated_at"] >= old["updated_at"]:
            current[pair] = value
    db.save_rates({"pairs": current, "last_refresh": last_refresh})


def append_history(records):
    """Добавить записи в exchange_rates.json."""
    db = DatabaseManager()
    history = db.load_history()
    known_ids = {record["id"] for record in history}
    added = 0
    for record in records:
        if record["id"] not in known_ids:
            history.append(record)
            known_ids.add(record["id"])
            added += 1
    db.save_history(history)
    return added


def make_history_record(pair, rate, timestamp, source, meta):
    """Создать запись истории."""
    from_currency, to_currency = pair.split("_")
    return {
        "id": f"{pair}_{timestamp}",
        "from_currency": from_currency,
        "to_currency": to_currency,
        "rate": rate,
        "timestamp": timestamp,
        "source": source,
        "meta": meta,
    }
