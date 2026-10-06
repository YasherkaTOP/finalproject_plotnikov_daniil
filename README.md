# finalproject_plotnikov_daniil — ValutaTrade Hub

Консольное приложение для симуляции торговли валютами. Пользователь
регистрируется, покупает и продаёт фиатные и криптовалюты в виртуальном
портфеле и смотрит актуальные курсы.

## Структура

```
data/
  users.json            # пользователи
  portfolios.json       # портфели и кошельки
  rates.json            # последние курсы (кеш для Core Service)
  exchange_rates.json   # история всех полученных курсов
valutatrade_hub/
  logging_config.py     # настройка логов
  decorators.py         # @log_action
  core/                 # currencies, exceptions, models, usecases, utils
  infra/                # settings.py (SettingsLoader), database.py (DatabaseManager)
  parser_service/       # config, api_clients, updater, storage, scheduler
  cli/interface.py      # команды
main.py
```

## Установка и запуск

```bash
make install
make project
make lint
make build
```

## Команды

```
register --username <str> --password <str>
login --username <str> --password <str>
show-portfolio [--base <str>]
buy --currency <str> --amount <float>
sell --currency <str> --amount <float>
get-rate --from <str> --to <str>
update-rates [--source coingecko|exchangerate]
show-rates [--currency <str>] [--top <int>] [--base <str>]
help [команда]
exit
```

Поддерживаемые валюты: USD, EUR, GBP, RUB, BTC, ETH, SOL.

## Parser Service и API-ключ

1. Зарегистрируйтесь на https://www.exchangerate-api.com/ и получите ключ.
2. Задайте переменную окружения (ключ не хранится в коде):
   - Linux/macOS: `export EXCHANGERATE_API_KEY=ваш_ключ`
3. CoinGecko работает без ключа.

Обновить курсы: команда `update-rates` в CLI или обновление по расписанию:

```bash
uv run python -m valutatrade_hub.parser_service.scheduler
```

## Логи

- `logs/actions.log` — операции register, login, buy, sell;
- `logs/parser.log` — работа Parser Service.
