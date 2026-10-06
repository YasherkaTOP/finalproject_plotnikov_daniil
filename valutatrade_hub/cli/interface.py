"""Командный интерфейс. Здесь только разбор команд и вывод —
вся логика находится в core/usecases.py."""

import logging
import shlex
import sys

from prettytable import PrettyTable

from valutatrade_hub.core import usecases
from valutatrade_hub.core.currencies import CURRENCIES
from valutatrade_hub.core.exceptions import (
    ApiRequestError,
    CurrencyNotFoundError,
    InsufficientFundsError,
)
from valutatrade_hub.core.utils import (
    format_amount,
    format_rate,
    format_time,
    validate_currency_code,
)
from valutatrade_hub.logging_config import setup_logging

COMMANDS_HELP = {
    "register": "register --username <str> --password <str>",
    "login": "login --username <str> --password <str>",
    "show-portfolio": "show-portfolio [--base <str>]",
    "buy": "buy --currency <str> --amount <float>",
    "sell": "sell --currency <str> --amount <float>",
    "get-rate": "get-rate --from <str> --to <str>",
    "update-rates": "update-rates [--source coingecko|exchangerate]",
    "show-rates": "show-rates [--currency <str>] [--top <int>] [--base <str>]",
    "help": "help [команда]",
    "exit": "exit",
}

STALE_WARNING = "Внимание: курс устарел. Выполните 'update-rates' для обновления."


def parse_args(tokens):
    args = {}
    i = 0
    while i < len(tokens):
        key = tokens[i]
        if not key.startswith("--") or i + 1 >= len(tokens):
            raise ValueError(f"Некорректный аргумент: {key}")
        args[key[2:]] = tokens[i + 1]
        i += 2
    return args


def require(args, *names):
    for name in names:
        if name not in args:
            raise ValueError(f"Не указан обязательный аргумент --{name}")


class CLI:
    """Консольный интерфейс с сессией пользователя."""

    def __init__(self):
        self.current_user = None
        self.commands = {
            "register": self.register,
            "login": self.login,
            "show-portfolio": self.show_portfolio,
            "buy": self.buy,
            "sell": self.sell,
            "get-rate": self.get_rate,
            "update-rates": self.update_rates,
            "show-rates": self.show_rates,
        }

    def run(self):
        print("ValutaTrade Hub. Введите 'help' для списка команд.")
        while True:
            try:
                line = input("> ")
            except (EOFError, KeyboardInterrupt):
                print()
                break
            try:
                tokens = shlex.split(line)
            except ValueError as error:
                print(f"Ошибка в команде: {error}")
                continue
            if not tokens:
                continue

            command, rest = tokens[0], tokens[1:]
            if command == "exit":
                break
            if command == "help":
                self.help(rest)
                continue
            if command not in self.commands:
                print(f"Неизвестная команда '{command}'. Введите 'help'.")
                continue

            try:
                self.commands[command](parse_args(rest))
            except InsufficientFundsError as error:
                print(error)
            except CurrencyNotFoundError as error:
                print(error)
                print(f"Поддерживаемые валюты: {', '.join(CURRENCIES)}")
                print("Подробнее: help get-rate")
            except ApiRequestError as error:
                print(error)
                print("Повторите попытку позже или проверьте подключение к сети.")
            except (ValueError, TypeError) as error:
                print(error)

    def check_login(self):
        if self.current_user is None:
            print("Сначала выполните login")
            return False
        return True

    def help(self, rest):
        if rest and rest[0] in COMMANDS_HELP:
            print(f"Использование: {COMMANDS_HELP[rest[0]]}")
            if rest[0] == "get-rate":
                print(f"Поддерживаемые валюты: {', '.join(CURRENCIES)}")
            return
        table = PrettyTable(["Команда"])
        table.align = "l"
        for usage in COMMANDS_HELP.values():
            table.add_row([usage])
        print(table)

    def register(self, args):
        require(args, "username", "password")
        user = usecases.register(args["username"], args["password"])
        print(
            f"Пользователь '{user['username']}' зарегистрирован "
            f"(id={user['user_id']}). "
            f"Войдите: login --username {user['username']} --password ****"
        )

    def login(self, args):
        require(args, "username", "password")
        self.current_user = usecases.login(args["username"], args["password"])
        print(f"Вы вошли как '{self.current_user.username}'")

    def show_portfolio(self, args):
        if not self.check_login():
            return
        data = usecases.show_portfolio(self.current_user.user_id, args.get("base"))
        if not data["wallets"]:
            print("У вас пока нет кошельков. Купите валюту командой buy.")
            return
        base = data["base"]
        print(f"Портфель пользователя '{data['username']}' (база: {base}):")
        for wallet in data["wallets"]:
            balance = format_amount(wallet["balance"], wallet["code"])
            if wallet["value"] is None:
                value = "нет курса"
            else:
                value = f"{wallet['value']:.2f} {base}"
            print(f"- {wallet['code']}: {balance}  → {value}")
        print(f"ИТОГО: {data['total']:,.2f} {base}")

    def buy(self, args):
        if not self.check_login():
            return
        require(args, "currency", "amount")
        code = validate_currency_code(args["currency"])
        try:
            result = usecases.buy(self.current_user.user_id, code, args["amount"])
        except ApiRequestError:
            print(f"Не удалось получить курс для {code}→USD")
            return
        self.print_trade(result, "Покупка", "Оценочная стоимость покупки")

    def sell(self, args):
        if not self.check_login():
            return
        require(args, "currency", "amount")
        code = validate_currency_code(args["currency"])
        try:
            result = usecases.sell(self.current_user.user_id, code, args["amount"])
        except ApiRequestError:
            print(f"Не удалось получить курс для {code}→USD")
            return
        self.print_trade(result, "Продажа", "Оценочная выручка")

    def print_trade(self, result, title, value_title):
        code = result["code"]
        print(
            f"{title} выполнена: {format_amount(result['amount'], code)} {code} "
            f"по курсу {format_rate(result['rate'])} USD/{code}"
        )
        print("Изменения в портфеле:")
        print(
            f"- {code}: было {format_amount(result['before'], code)} "
            f"→ стало {format_amount(result['after'], code)}"
        )
        print(f"{value_title}: {result['value']:,.2f} USD")

    def get_rate(self, args):
        require(args, "from", "to")
        from_code = validate_currency_code(args["from"])
        to_code = validate_currency_code(args["to"])
        try:
            data = usecases.get_rate(from_code, to_code)
        except ApiRequestError:
            print(f"Курс {from_code}→{to_code} недоступен. Повторите попытку позже.")
            return
        print(
            f"Курс {from_code}→{to_code}: {format_rate(data['rate'])} "
            f"(обновлено: {format_time(data['updated_at'])})"
        )
        print(f"Обратный курс {to_code}→{from_code}: {format_rate(1 / data['rate'])}")
        if data["stale"]:
            print(STALE_WARNING)

    def update_rates(self, args):
        parser_logger = logging.getLogger("parser")
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(logging.Formatter("%(levelname)s: %(message)s"))
        parser_logger.addHandler(handler)
        try:
            result = usecases.update_rates(args.get("source"))
        except ApiRequestError:
            print("Update failed. Check logs/parser.log for details.")
            return
        finally:
            parser_logger.removeHandler(handler)

        if result["errors"]:
            print("Update completed with errors. Check logs/parser.log for details.")
        else:
            print(
                f"Update successful. Total rates updated: {result['updated']}. "
                f"Last refresh: {result['last_refresh']}"
            )

    def show_rates(self, args):
        data = usecases.show_rates(
            args.get("currency"), args.get("top"), args.get("base")
        )
        print(f"Rates from cache (updated at {data['last_refresh']}):")
        table = PrettyTable(["Pair", "Rate", "Updated at"])
        for row in data["rows"]:
            table.add_row(
                [row["pair"], format_rate(row["rate"]), format_time(row["time"])]
            )
        print(table)


def main():
    setup_logging()
    CLI().run()
