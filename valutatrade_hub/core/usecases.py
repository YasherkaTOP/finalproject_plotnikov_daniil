import secrets
from datetime import datetime

from valutatrade_hub.core.currencies import CryptoCurrency, get_currency
from valutatrade_hub.core.exceptions import ApiRequestError, CurrencyNotFoundError
from valutatrade_hub.core.models import (
    MIN_PASSWORD_LENGTH,
    Portfolio,
    User,
    hash_password,
)
from valutatrade_hub.core.utils import (
    find_rate,
    is_fresh,
    now_iso,
    validate_amount,
    validate_currency_code,
)
from valutatrade_hub.decorators import log_action
from valutatrade_hub.infra.database import DatabaseManager
from valutatrade_hub.infra.settings import SettingsLoader
from valutatrade_hub.parser_service.updater import RatesUpdater

db = DatabaseManager()
settings = SettingsLoader()


@log_action("REGISTER")
def register(username, password):
    """Зарегистрировать пользователя и создать ему пустой портфель."""
    users = db.load_users()
    username = username.strip()
    if not username:
        raise ValueError("Имя пользователя не может быть пустым")
    for user in users:
        if user["username"] == username:
            raise ValueError(f"Имя пользователя '{username}' уже занято")
    if len(password) < MIN_PASSWORD_LENGTH:
        raise ValueError("Пароль должен быть не короче 4 символов")

    user_id = max([user["user_id"] for user in users], default=0) + 1
    salt = secrets.token_hex(4)
    new_user = User(
        user_id,
        username,
        hash_password(password, salt),
        salt,
        datetime.now().replace(microsecond=0),
    )
    users.append(new_user.to_dict())
    db.save_users(users)

    portfolios = db.load_portfolios()
    portfolios.append({"user_id": user_id, "wallets": {}})
    db.save_portfolios(portfolios)
    return {"user_id": user_id, "username": username}


@log_action("LOGIN")
def login(username, password):
    for data in db.load_users():
        if data["username"] == username:
            user = User.from_dict(data)
            if not user.verify_password(password):
                raise ValueError("Неверный пароль")
            return user
    raise ValueError(f"Пользователь '{username}' не найден")


def _get_username(user_id):
    for data in db.load_users():
        if data["user_id"] == user_id:
            return data["username"]
    return str(user_id)

def _load_portfolio(user_id):
    for data in db.load_portfolios():
        if data["user_id"] == user_id:
            return Portfolio.from_dict(data)
    return Portfolio(user_id)


def _save_portfolio(portfolio):
    portfolios = db.load_portfolios()
    for index, data in enumerate(portfolios):
        if data["user_id"] == portfolio.user_id:
            portfolios[index] = portfolio.to_dict()
            break
    else:
        portfolios.append(portfolio.to_dict())
    db.save_portfolios(portfolios)


def show_portfolio(user_id, base=None):
    """Кошельки пользователя и их стоимость в базовой валюте."""
    base = validate_currency_code(base or settings.get("default_base_currency"))
    try:
        get_currency(base)
    except CurrencyNotFoundError:
        raise ValueError(f"Неизвестная базовая валюта '{base}'") from None

    portfolio = _load_portfolio(user_id)
    wallets = []
    for code, wallet in portfolio.wallets.items():
        try:
            rate = get_rate(code, base)["rate"]
            value = wallet.balance * rate
        except ApiRequestError:
            value = None
        wallets.append({"code": code, "balance": wallet.balance, "value": value})

    pairs = db.load_rates().get("pairs", {})
    rates = {pair: data["rate"] for pair, data in pairs.items()}
    return {
        "username": _get_username(user_id),
        "base": base,
        "wallets": wallets,
        "total": portfolio.get_total_value(base, rates),
    }


@log_action("BUY", verbose=True)
def buy(user_id, currency_code, amount):
    amount = validate_amount(amount)
    code = validate_currency_code(currency_code)
    get_currency(code)
    rate = get_rate(code, "USD")["rate"]

    portfolio = _load_portfolio(user_id)
    wallet = portfolio.get_wallet(code)
    if wallet is None:
        wallet = portfolio.add_currency(code)
    before = wallet.balance
    wallet.deposit(amount)
    _save_portfolio(portfolio)

    return {
        "username": _get_username(user_id),
        "code": code,
        "amount": amount,
        "rate": rate,
        "base": "USD",
        "before": before,
        "after": wallet.balance,
        "value": amount * rate,
    }


@log_action("SELL", verbose=True)
def sell(user_id, currency_code, amount):
    amount = validate_amount(amount)
    code = validate_currency_code(currency_code)
    get_currency(code)

    portfolio = _load_portfolio(user_id)
    wallet = portfolio.get_wallet(code)
    if wallet is None:
        raise ValueError(
            f"У вас нет кошелька '{code}'. Добавьте валюту: "
            "она создаётся автоматически при первой покупке."
        )
    before = wallet.balance
    wallet.withdraw(amount)
    rate = get_rate(code, "USD")["rate"]
    _save_portfolio(portfolio)

    return {
        "username": _get_username(user_id),
        "code": code,
        "amount": amount,
        "rate": rate,
        "base": "USD",
        "before": before,
        "after": wallet.balance,
        "value": amount * rate,
    }


def _rate_from_cache(from_code, to_code):
    """Найти курс в rates.json."""
    pairs = db.load_rates().get("pairs", {})
    simple_rates = {pair: data["rate"] for pair, data in pairs.items()}
    rate = find_rate(simple_rates, from_code, to_code)
    if rate is None:
        return None
    times = [
        pairs[f"{code}_USD"]["updated_at"]
        for code in (from_code, to_code)
        if code != "USD"
    ]
    updated_at = min(times) if times else now_iso()
    return rate, updated_at


def update_rates(source=None):
    """Обновить курсы через Parser Service."""
    if source:
        updater = RatesUpdater.for_source(source)
    else:
        updater = RatesUpdater()
    return updater.run_update()


def get_rate(from_code, to_code):
    from_code = validate_currency_code(from_code)
    to_code = validate_currency_code(to_code)
    get_currency(from_code)
    get_currency(to_code)

    ttl = settings.get("rates_ttl_seconds")
    cached = _rate_from_cache(from_code, to_code)
    if cached is None or not is_fresh(cached[1], ttl):
        try:
            update_rates()
            cached = _rate_from_cache(from_code, to_code)
        except ApiRequestError:
            if cached is None:
                raise

    if cached is None:
        raise ApiRequestError(f"курс {from_code}→{to_code} не найден")
    rate, updated_at = cached
    return {
        "rate": rate,
        "updated_at": updated_at,
        "stale": not is_fresh(updated_at, ttl),
    }


def show_rates(currency=None, top=None, base=None):
    data = db.load_rates()
    pairs = data.get("pairs", {})
    if not pairs:
        raise ValueError(
            "Локальный кеш курсов пуст. "
            "Выполните 'update-rates', чтобы загрузить данные."
        )

    rows = []
    for pair, value in pairs.items():
        rows.append({"pair": pair, "rate": value["rate"], "time": value["updated_at"]})

    if base:
        base = validate_currency_code(base)
        get_currency(base)
        base_rate = 1.0 if base == "USD" else pairs.get(f"{base}_USD", {}).get("rate")
        if base_rate is None:
            raise ValueError(f"Курс для '{base}' не найден в кеше.")
        converted = []
        for row in rows:
            code = row["pair"].split("_")[0]
            if code != base:
                new_pair = f"{code}_{base}"
                converted.append(
                    {**row, "pair": new_pair, "rate": row["rate"] / base_rate}
                )
        if base != "USD":
            converted.append(
                {
                    "pair": f"USD_{base}",
                    "rate": 1 / base_rate,
                    "time": data["last_refresh"],
                }
            )
        rows = converted

    if currency:
        currency = validate_currency_code(currency)
        rows = [row for row in rows if currency in row["pair"].split("_")]
        if not rows:
            raise ValueError(f"Курс для '{currency}' не найден в кеше.")

    if top:
        if not str(top).isdigit() or int(top) <= 0:
            raise ValueError("'top' должен быть целым положительным числом")
        top = int(top)
        crypto_rows = []
        for row in rows:
            code = row["pair"].split("_")[0]
            try:
                if isinstance(get_currency(code), CryptoCurrency):
                    crypto_rows.append(row)
            except CurrencyNotFoundError:
                continue
        rows = sorted(crypto_rows, key=lambda row: row["rate"], reverse=True)[:top]
    else:
        rows = sorted(rows, key=lambda row: row["pair"])

    return {"last_refresh": data.get("last_refresh"), "rows": rows}
