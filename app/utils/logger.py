"""
Structured logging module with sensitive information masking.
Ensures Telegram Bot Tokens and Gemini API Keys are never printed in logs.
"""
import logging
import re
import sys
from typing import Optional
from app.config import settings

SENSITIVE_PATTERNS = [
    re.compile(r"bot\d+:[A-Za-z0-9_-]+"),  # Telegram Bot Token
    re.compile(r"AIzaSy[A-Za-z0-9_-]{33}"),  # Google API Key
    re.compile(r"(password|secret|token)=([^&\s]+)", re.IGNORECASE),
]


class SensitiveDataFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, str):
            record.msg = self.mask_sensitive_data(record.msg)
        if record.args:
            if isinstance(record.args, tuple):
                record.args = tuple(
                    self.mask_sensitive_data(str(arg)) if isinstance(arg, str) else arg
                    for arg in record.args
                )
            elif isinstance(record.args, dict):
                record.args = {
                    k: self.mask_sensitive_data(str(v)) if isinstance(v, str) else v
                    for k, v in record.args.items()
                }
        return True

    @staticmethod
    def mask_sensitive_data(text: str) -> str:
        for pattern in SENSITIVE_PATTERNS:
            text = pattern.sub("[REDACTED_SECRET]", text)
        return text


def setup_logger(name: str = "unicon_ai", level: Optional[str] = None) -> logging.Logger:
    """Configures and returns a masked application logger."""
    log_level_str = level or settings.log_level
    log_level = getattr(logging, log_level_str.upper(), logging.INFO)

    logger = logging.getLogger(name)
    logger.setLevel(log_level)

    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(log_level)
        formatter = logging.Formatter(
            fmt="%(asctime)s | %(levelname)-7s | %(name)s:%(funcName)s:%(lineno)d - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        handler.setFormatter(formatter)
        handler.addFilter(SensitiveDataFilter())
        logger.addHandler(handler)

    return logger


logger = setup_logger()
