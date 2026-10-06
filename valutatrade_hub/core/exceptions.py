class InsufficientFundsError(Exception):
    """Недостаточно средств на кошельке."""

    def __init__(self, available, required, code):
        self.available = available
        self.required = required
        self.code = code
        super().__init__(
            f"Недостаточно средств: доступно {available} {code}, "
            f"требуется {required} {code}"
        )


class CurrencyNotFoundError(Exception):
    """Неизвестная валюта."""

    def __init__(self, code):
        self.code = code
        super().__init__(f"Неизвестная валюта '{code}'")


class ApiRequestError(Exception):
    """Ошибка API."""

    def __init__(self, reason):
        self.reason = reason
        super().__init__(f"Ошибка при обращении к API: {reason}")
