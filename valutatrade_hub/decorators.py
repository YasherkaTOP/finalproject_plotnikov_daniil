import functools
import inspect
import logging

from valutatrade_hub.core.utils import format_rate

logger = logging.getLogger("actions")


def _build_message(action, params, result):
    if isinstance(result, dict) and "username" in result:
        message = f"{action} user='{result['username']}'"
    elif "username" in params:
        message = f"{action} user='{params['username']}'"
    else:
        message = f"{action} user_id={params.get('user_id')}"
    if "currency_code" in params:
        message += f" currency='{str(params['currency_code']).upper()}'"
    if "amount" in params:
        message += f" amount={params['amount']}"
    if isinstance(result, dict) and "rate" in result:
        message += f" rate={format_rate(result['rate'])} base='{result['base']}'"
    return message


def log_action(action, verbose=False):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            params = inspect.signature(func).bind(*args, **kwargs).arguments
            try:
                result = func(*args, **kwargs)
            except Exception as error:
                message = _build_message(action, params, None)
                logger.info(
                    f"{message} result=ERROR error_type={type(error).__name__} "
                    f"error_message='{error}'"
                )
                raise

            message = _build_message(action, params, result)
            message += " result=OK"
            if verbose and isinstance(result, dict) and "before" in result:
                message += f" balance={result['before']}→{result['after']}"
            logger.info(message)
            return result

        return wrapper

    return decorator
