import logging

from valutatrade_hub.core.exceptions import ApiRequestError
from valutatrade_hub.core.utils import now_iso
from valutatrade_hub.parser_service import storage
from valutatrade_hub.parser_service.api_clients import (
    CoinGeckoClient,
    ExchangeRateApiClient,
)
from valutatrade_hub.parser_service.config import ParserConfig

logger = logging.getLogger("parser")


class RatesUpdater:
    """Опрашивает сервисы и сохраняет курсы."""

    def __init__(self, clients=None):
        if clients is None:
            clients = [CoinGeckoClient(), ExchangeRateApiClient()]
        self.clients = clients

    @classmethod
    def for_source(cls, source):
        if source == "coingecko":
            return cls([CoinGeckoClient()])
        if source == "exchangerate":
            return cls([ExchangeRateApiClient()])
        raise ValueError(
            f"Неизвестный источник '{source}'. Доступно: coingecko, exchangerate"
        )

    def run_update(self):
        logger.info("Starting rates update...")
        pairs = {}
        history = []
        errors = []

        for client in self.clients:
            try:
                rates = client.fetch_rates()
            except ApiRequestError as error:
                logger.error(f"Failed to fetch from {client.name}: {error.reason}")
                errors.append(f"{client.name}: {error.reason}")
                continue

            logger.info(f"Fetching from {client.name}... OK ({len(rates)} rates)")
            timestamp = now_iso()
            for pair, rate in rates.items():
                pairs[pair] = {
                    "rate": rate,
                    "updated_at": timestamp,
                    "source": client.name,
                }
                history.append(
                    storage.make_history_record(
                        pair, rate, timestamp, client.name, client.meta
                    )
                )

        if not pairs:
            raise ApiRequestError("; ".join(errors))

        last_refresh = now_iso()
        logger.info(
            f"Writing {len(pairs)} rates to {ParserConfig().RATES_FILE_PATH}..."
        )
        storage.save_rates(pairs, last_refresh)
        storage.append_history(history)
        logger.info("Update finished")
        return {"updated": len(pairs), "errors": errors, "last_refresh": last_refresh}
