import logging


class AppLogger:
    """Centralised logging configuration for the application."""

    def __init__(self, level: str = "INFO"):
        self._level = getattr(logging, level.upper(), logging.INFO)
        self._logger = self._build()

    def _build(self) -> logging.Logger:
        logging.basicConfig(
            format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
            level=self._level,
        )
        return logging.getLogger("retrieval")

    def get(self) -> logging.Logger:
        """Return the configured logger instance."""
        return self._logger
