import functools
import random
import time

from ytauto.core.log import get_logger

log = get_logger(__name__)


def retry(attempts: int = 3, base_delay: float = 1.0, exceptions: tuple = (Exception,)):
    """Retry with exponential backoff and jitter."""
    def deco(fn):
        @functools.wraps(fn)
        def wrapper(*a, **kw):
            for i in range(attempts):
                try:
                    return fn(*a, **kw)
                except exceptions as e:
                    if i == attempts - 1:
                        raise
                    delay = base_delay * (2 ** i) * (0.8 + 0.4 * random.random())
                    log.warning("%s failed (%s); retry %d/%d in %.1fs",
                                fn.__name__, e, i + 1, attempts - 1, delay)
                    time.sleep(delay)
        return wrapper
    return deco
