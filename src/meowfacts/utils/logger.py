"""Class-based logger client.

Pattern: each module that needs logging holds a `Logger` instance on `self`
(e.g. `self.logger = Logger(__name__)`) and logs through it — no module-level
globals, no direct use of the stdlib `logging` module in feature code.

Process-wide setup (format, level, stream) happens once via `Logger.configure()`
at app startup — typically from `main.py`. Every `Logger` instance shares that
configuration because they all wrap `logging.getLogger`, which is itself a
name-keyed singleton under the hood.
"""

import logging
import sys


class Logger:
    _DEFAULT_FORMAT = "%(asctime)s %(levelname)s %(name)s: %(message)s"
    _configured = False

    def __init__(self, name: str) -> None:
        self._logger = logging.getLogger(name)

    @classmethod
    def configure(cls, verbose: bool = False) -> None:
        """Install the root handler. Idempotent — a second call is a no-op.

        Call once from the app entry point. Feature code must never call this;
        it just constructs `Logger(__name__)` and assumes setup is done.
        """
        if cls._configured:
            return
        logging.basicConfig(
            stream=sys.stderr,
            level=logging.DEBUG if verbose else logging.INFO,
            format=cls._DEFAULT_FORMAT,
        )
        cls._configured = True

    def debug(self, msg: str, *args, **kwargs) -> None:
        self._logger.debug(msg, *args, **kwargs)

    def info(self, msg: str, *args, **kwargs) -> None:
        self._logger.info(msg, *args, **kwargs)

    def warning(self, msg: str, *args, **kwargs) -> None:
        self._logger.warning(msg, *args, **kwargs)

    def error(self, msg: str, *args, **kwargs) -> None:
        self._logger.error(msg, *args, **kwargs)

    def critical(self, msg: str, *args, **kwargs) -> None:
        self._logger.critical(msg, *args, **kwargs)
