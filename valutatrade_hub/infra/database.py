import json
import os

from valutatrade_hub.infra.settings import SettingsLoader


class DatabaseManager:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def load(self, path, default):
        """Прочитать JSON-файл."""
        if not os.path.exists(path):
            return default
        with open(path, encoding="utf-8") as file:
            text = file.read()
        if not text.strip():
            return default
        return json.loads(text)

    def save(self, path, data):
        """Записать JSON атомарно."""
        folder = os.path.dirname(path)
        if folder:
            os.makedirs(folder, exist_ok=True)
        tmp_path = path + ".tmp"
        with open(tmp_path, "w", encoding="utf-8") as file:
            json.dump(data, file, ensure_ascii=False, indent=2)
        os.replace(tmp_path, path)

    def load_users(self):
        return self.load(SettingsLoader().get("users_file"), [])

    def save_users(self, users):
        self.save(SettingsLoader().get("users_file"), users)

    def load_portfolios(self):
        return self.load(SettingsLoader().get("portfolios_file"), [])

    def save_portfolios(self, portfolios):
        self.save(SettingsLoader().get("portfolios_file"), portfolios)

    def load_rates(self):
        return self.load(SettingsLoader().get("rates_file"), {})

    def save_rates(self, rates):
        self.save(SettingsLoader().get("rates_file"), rates)

    def load_history(self):
        return self.load(SettingsLoader().get("history_file"), [])

    def save_history(self, history):
        self.save(SettingsLoader().get("history_file"), history)
