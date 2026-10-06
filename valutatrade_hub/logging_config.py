import logging
import os
from logging.handlers import RotatingFileHandler

from valutatrade_hub.infra.settings import SettingsLoader


def _make_handler(file_name):
    settings = SettingsLoader()
    log_dir = settings.get("log_dir")
    os.makedirs(log_dir, exist_ok=True)
    handler = RotatingFileHandler(
        os.path.join(log_dir, file_name),
        maxBytes=settings.get("log_max_bytes"),
        backupCount=settings.get("log_backup_count"),
        encoding="utf-8",
    )
    formatter = logging.Formatter(
        settings.get("log_format"), datefmt="%Y-%m-%dT%H:%M:%S"
    )
    handler.setFormatter(formatter)
    return handler


def setup_logging():
    level = SettingsLoader().get("log_level")
    for name, file_name in (("actions", "actions.log"), ("parser", "parser.log")):
        logger = logging.getLogger(name)
        if logger.handlers:
            continue
        logger.setLevel(level)
        logger.addHandler(_make_handler(file_name))
