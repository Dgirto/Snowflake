"""Conector Ruvic de solo lectura para Snowflake."""

from .client import SnowflakeClient
from .config import ENV_PREFIX, SnowflakeConfig
from .exceptions import (
    SnowflakeAuthError,
    SnowflakeConnectorError,
    SnowflakeDataError,
    SnowflakeNetworkError,
)
from .logging_utils import setup_logging

__all__ = [
    "ENV_PREFIX",
    "SnowflakeAuthError",
    "SnowflakeClient",
    "SnowflakeConfig",
    "SnowflakeConnectorError",
    "SnowflakeDataError",
    "SnowflakeNetworkError",
    "setup_logging",
]

__version__ = "1.0.0"
