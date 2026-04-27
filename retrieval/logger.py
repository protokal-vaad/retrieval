import logging


class AppLogger:
    """Centralised logging configuration for the application."""

    def __init__(self, level: str = "INFO"):
        self._level = getattr(logging, level.upper(), logging.INFO)
        self._logger: logging.Logger | None = None

    def setup(self) -> None:
        """Configure the root logger and build the application logger."""
        logging.basicConfig(
            format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
            level=self._level,
        )
        self._logger = logging.getLogger("retrieval")

    def get(self) -> logging.Logger:
        """Return the configured logger instance."""
        return self._logger
