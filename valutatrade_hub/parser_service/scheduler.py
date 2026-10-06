import logging
import time

from valutatrade_hub.core.exceptions import ApiRequestError
from valutatrade_hub.logging_config import setup_logging
from valutatrade_hub.parser_service.config import ParserConfig
from valutatrade_hub.parser_service.updater import RatesUpdater

logger = logging.getLogger("parser")


def run_scheduler(interval_seconds=None):
    """Обновлять курсы каждые interval_seconds секунд."""
    if interval_seconds is None:
        interval_seconds = ParserConfig().UPDATE_INTERVAL_SECONDS
    updater = RatesUpdater()
    while True:
        try:
            updater.run_update()
        except ApiRequestError as error:
            logger.error(f"Scheduled update failed: {error.reason}")
        time.sleep(interval_seconds)


if __name__ == "__main__":
    setup_logging()
    print("Обновление курсов по расписанию запущено.")
    try:
        run_scheduler()
    except KeyboardInterrupt:
        print("Остановлено.")
