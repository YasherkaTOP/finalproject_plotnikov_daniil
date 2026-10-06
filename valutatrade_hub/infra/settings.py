import tomllib
from pathlib import Path

PYPROJECT_PATH = Path("pyproject.toml")

DEFAULT_SETTINGS = {
    "users_file": "data/users.json",
    "portfolios_file": "data/portfolios.json",
    "rates_file": "data/rates.json",
    "history_file": "data/exchange_rates.json",
    "rates_ttl_seconds": 300,
    "default_base_currency": "USD",
    "log_dir": "logs",
    "log_level": "INFO",
    "log_format": "%(levelname)s %(asctime)s %(message)s",
    "log_max_bytes": 1000000,
    "log_backup_count": 3,
}


class SettingsLoader:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._settings = {}
            cls._instance.reload()
        return cls._instance

    def reload(self):
        """Обновить настройки из pyproject.toml."""
        settings = dict(DEFAULT_SETTINGS)
        if PYPROJECT_PATH.exists():
            with open(PYPROJECT_PATH, "rb") as file:
                data = tomllib.load(file)
            settings.update(data.get("tool", {}).get("valutatrade", {}))
        self._settings = settings

    def get(self, key, default=None):
        return self._settings.get(key, default)
