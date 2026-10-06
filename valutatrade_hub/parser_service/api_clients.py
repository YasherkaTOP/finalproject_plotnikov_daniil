import time
from abc import ABC, abstractmethod

import requests

from valutatrade_hub.core.exceptions import ApiRequestError
from valutatrade_hub.parser_service.config import ParserConfig


class BaseApiClient(ABC):
    name = "base"

    def __init__(self, config=None):
        self.config = config or ParserConfig()
        self.meta = {}

    @abstractmethod
    def fetch_rates(self):
        """Получить курсы от API."""

    def _get_json(self, url, params=None):
        """Сделать GET-запрос."""
        start = time.time()
        try:
            response = requests.get(
                url, params=params, timeout=self.config.REQUEST_TIMEOUT
            )
        except requests.exceptions.Timeout:
            raise ApiRequestError("превышено время ожидания") from None
        except requests.exceptions.RequestException:
            raise ApiRequestError("сетевая ошибка") from None

        self.meta = {
            "request_ms": int((time.time() - start) * 1000),
            "status_code": response.status_code,
            "etag": response.headers.get("ETag"),
        }

        if response.status_code in (401, 403):
            raise ApiRequestError("неверный API-ключ или нет доступа")
        if response.status_code == 429:
            raise ApiRequestError("превышен лимит запросов (429)")
        if response.status_code != 200:
            raise ApiRequestError(f"ошибка HTTP {response.status_code}")

        try:
            return response.json()
        except ValueError:
            raise ApiRequestError("некорректный JSON в ответе") from None


class CoinGeckoClient(BaseApiClient):
    """Курсы криптовалют."""

    name = "CoinGecko"

    def fetch_rates(self):
        base = self.config.BASE_CURRENCY
        ids = [
            self.config.CRYPTO_ID_MAP[code] for code in self.config.CRYPTO_CURRENCIES
        ]
        params = {"ids": ",".join(ids), "vs_currencies": base.lower()}
        data = self._get_json(self.config.COINGECKO_URL, params)

        rates = {}
        for code in self.config.CRYPTO_CURRENCIES:
            coin_id = self.config.CRYPTO_ID_MAP[code]
            value = data.get(coin_id, {}).get(base.lower())
            if isinstance(value, (int, float)) and value > 0:
                rates[f"{code}_{base}"] = float(value)
        if not rates:
            raise ApiRequestError("в ответе нет курсов")
        return rates


class ExchangeRateApiClient(BaseApiClient):
    """Курсы фиатных валют."""

    name = "ExchangeRate-API"

    def fetch_rates(self):
        if not self.config.EXCHANGERATE_API_KEY:
            raise ApiRequestError("не задана переменная окружения EXCHANGERATE_API_KEY")
        base = self.config.BASE_CURRENCY
        url = (
            f"{self.config.EXCHANGERATE_API_URL}/"
            f"{self.config.EXCHANGERATE_API_KEY}/latest/{base}"
        )
        data = self._get_json(url)
        if data.get("result") != "success":
            raise ApiRequestError(f"API вернул ошибку {data.get('error-type')}")

        rates = {}
        for code in self.config.FIAT_CURRENCIES:
            value = data.get("rates", {}).get(code)
            if isinstance(value, (int, float)) and value > 0:
                rates[f"{code}_{base}"] = round(1 / value, 6)
        if not rates:
            raise ApiRequestError("в ответе нет курсов")
        return rates
