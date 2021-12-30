import logging
import time

log = logging.getLogger("android-parser")


def init_logging(quiet: bool, verbose: bool) -> None:
    if verbose:
        log.setLevel(logging.DEBUG)
    elif quiet:
        log.setLevel(logging.WARNING)
    else:
        log.setLevel(logging.INFO)
    handler = logging.StreamHandler()
    handler.setLevel(log.getEffectiveLevel())
    formatter = logging.Formatter(
        fmt="{asctime} - {name} - {levelname} - {message}",
        datefmt="%Y-%m-%dT%H:%M:%SZ",
        style="{",
    )
    formatter.converter = time.gmtime  # type: ignore
    handler.setFormatter(formatter)
    log.addHandler(handler)
