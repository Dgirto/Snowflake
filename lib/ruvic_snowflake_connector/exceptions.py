"""Excepciones propias del conector Snowflake.

Separan los tres tipos de fallo que el usuario debe distinguir:
autenticación, red/servidor y datos. Nunca exponemos excepciones
crípticas del driver subyacente.
"""


class SnowflakeConnectorError(Exception):
    """Error base del conector."""


class SnowflakeAuthError(SnowflakeConnectorError):
    """Credenciales inválidas o permisos insuficientes."""


class SnowflakeNetworkError(SnowflakeConnectorError):
    """No se pudo alcanzar la cuenta de Snowflake (red/timeout)."""


class SnowflakeDataError(SnowflakeConnectorError):
    """La operación es válida pero la consulta/objeto es inválido."""
