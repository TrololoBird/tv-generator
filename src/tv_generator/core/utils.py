from functools import wraps

from loguru import logger


def log_and_catch(default=None):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                logger.error(f"[{func.__name__}] Ошибка: {e}")
                return default

        return wrapper

    return decorator
