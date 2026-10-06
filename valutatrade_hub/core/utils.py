from datetime import datetime, timezone

from valutatrade_hub.core.currencies import CURRENCIES, CryptoCurrency


def validate_currency_code(code):
    if not isinstance(code, str) or not code.strip():
        raise ValueError("Код валюты не может быть пустым")
    return code.strip().upper()


def validate_amount(amount):
    """Проверить, что amount положительное число."""
    try:
        amount = float(amount)
    except (TypeError, ValueError):
        raise ValueError("'amount' должен быть положительным числом") from None
    if amount <= 0:
        raise ValueError("'amount' должен быть положительным числом")
    return amount


def format_amount(amount, code):
    if isinstance(CURRENCIES.get(code), CryptoCurrency):
        return f"{amount:.4f}"
    return f"{amount:.2f}"


def format_rate(rate):
    if rate >= 100:
        return f"{rate:.2f}"
    if rate >= 1:
        return f"{rate:.4f}"
    return f"{rate:.8f}".rstrip("0")


def now_iso():
    """Текущее время UTC."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def format_time(iso_time):
    return iso_time.replace("T", " ").replace("Z", "")


def is_fresh(iso_time, ttl_seconds):
    moment = datetime.fromisoformat(iso_time.replace("Z", "+00:00"))
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=timezone.utc)
    age = (datetime.now(timezone.utc) - moment).total_seconds()
    return age < ttl_seconds


def find_rate(rates, from_code, to_code):
    if from_code == to_code:
        return 1.0
    from_usd = 1.0 if from_code == "USD" else rates.get(f"{from_code}_USD")
    to_usd = 1.0 if to_code == "USD" else rates.get(f"{to_code}_USD")
    if from_usd is None or to_usd is None:
        return None
    return from_usd / to_usd
