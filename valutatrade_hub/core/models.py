import hashlib
from datetime import datetime

from valutatrade_hub.core.exceptions import InsufficientFundsError
from valutatrade_hub.core.utils import find_rate, format_amount, validate_amount

MIN_PASSWORD_LENGTH = 4

EXCHANGE_RATES = {
    "EUR_USD": 1.0786,
    "GBP_USD": 1.2361,
    "RUB_USD": 0.01016,
    "BTC_USD": 59337.21,
    "ETH_USD": 3720.00,
    "SOL_USD": 145.12,
}


def hash_password(password, salt):
    return hashlib.sha256((password + salt).encode("utf-8")).hexdigest()


class User:
    """Пользователь системы."""

    def __init__(self, user_id, username, hashed_password, salt, registration_date):
        self._user_id = user_id
        self.username = username
        self._hashed_password = hashed_password
        self._salt = salt
        self._registration_date = registration_date

    @property
    def user_id(self):
        return self._user_id

    @property
    def username(self):
        return self._username

    @username.setter
    def username(self, value):
        if not isinstance(value, str) or not value.strip():
            raise ValueError("Имя пользователя не может быть пустым")
        self._username = value.strip()

    @property
    def hashed_password(self):
        return self._hashed_password

    @property
    def salt(self):
        return self._salt

    @property
    def registration_date(self):
        return self._registration_date

    def get_user_info(self):
        """Информация о пользователе."""
        date = self._registration_date
        return f"id={self._user_id}, username={self._username}, registered={date}"

    def change_password(self, new_password):
        """Сменить пароль."""
        if len(new_password) < MIN_PASSWORD_LENGTH:
            raise ValueError("Пароль должен быть не короче 4 символов")
        self._hashed_password = hash_password(new_password, self._salt)

    def verify_password(self, password):
        """Проверить, совпадает ли введенный пароль."""
        return hash_password(password, self._salt) == self._hashed_password

    def to_dict(self):
        """Словарь для сохранения в users.json."""
        return {
            "user_id": self._user_id,
            "username": self._username,
            "hashed_password": self._hashed_password,
            "salt": self._salt,
            "registration_date": self._registration_date.isoformat(timespec="seconds"),
        }

    @classmethod
    def from_dict(cls, data):
        """Создать User из словаря users.json."""
        return cls(
            data["user_id"],
            data["username"],
            data["hashed_password"],
            data["salt"],
            datetime.fromisoformat(data["registration_date"]),
        )


class Wallet:
    """Кошелёк пользователя для одной валюты."""

    def __init__(self, currency_code, balance=0.0):
        self.currency_code = currency_code
        self.balance = balance

    @property
    def balance(self):
        return self._balance

    @balance.setter
    def balance(self, value):
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise TypeError("Баланс должен быть числом")
        if value < 0:
            raise ValueError("Баланс не может быть отрицательным")
        self._balance = round(float(value), 8)

    def deposit(self, amount):
        """Пополнить баланс."""
        amount = validate_amount(amount)
        self.balance = self._balance + amount

    def withdraw(self, amount):
        """Снять средства, если хватает баланса."""
        amount = validate_amount(amount)
        if amount > self._balance:
            raise InsufficientFundsError(
                format_amount(self._balance, self.currency_code),
                format_amount(amount, self.currency_code),
                self.currency_code,
            )
        self.balance = self._balance - amount

    def get_balance_info(self):
        return (
            f"{self.currency_code}: {format_amount(self._balance, self.currency_code)}"
        )


class Portfolio:
    """Все кошельки пользователя."""

    def __init__(self, user_id, wallets=None, user=None):
        self._user_id = user_id
        self._wallets = wallets if wallets is not None else {}
        self._user = user

    @property
    def user_id(self):
        return self._user_id

    @property
    def user(self):
        return self._user

    @property
    def wallets(self):
        return dict(self._wallets)

    def add_currency(self, currency_code):
        if currency_code in self._wallets:
            raise ValueError(f"Кошелёк '{currency_code}' уже есть в портфеле")
        self._wallets[currency_code] = Wallet(currency_code)
        return self._wallets[currency_code]

    def get_wallet(self, currency_code):
        return self._wallets.get(currency_code)

    def get_total_value(self, base_currency="USD", exchange_rates=None):
        if exchange_rates is None:
            exchange_rates = EXCHANGE_RATES
        total = 0.0
        for code, wallet in self._wallets.items():
            rate = find_rate(exchange_rates, code, base_currency)
            if rate is not None:
                total += wallet.balance * rate
        return total

    def to_dict(self):
        """Словарь для сохранения в portfolios.json."""
        wallets = {}
        for code, wallet in self._wallets.items():
            wallets[code] = {"currency_code": code, "balance": wallet.balance}
        return {"user_id": self._user_id, "wallets": wallets}

    @classmethod
    def from_dict(cls, data, user=None):
        """Создать Portfolio из словаря portfolios.json."""
        wallets = {}
        for code, wallet_data in data["wallets"].items():
            wallets[code] = Wallet(code, wallet_data["balance"])
        return cls(data["user_id"], wallets, user)
