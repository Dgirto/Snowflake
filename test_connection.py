"""Prueba de conexión estándar del conector snowflake.

Firma estándar Ruvic: def test_connection() -> tuple[bool, str]
- Lee la configuración EXCLUSIVAMENTE de las env vars RUVIC_SNOWFLAKE_*.
- Nunca lanza excepciones; retorna (ok, mensaje).

Ejecutable también como script para pruebas locales:
    python test_connection.py
"""

from __future__ import annotations


def test_connection() -> tuple[bool, str]:
    """Conecta a Snowflake y ejecuta SELECT 1 usando las env vars
    RUVIC_SNOWFLAKE_*."""
    try:
        from ruvic_snowflake_connector import (
            SnowflakeAuthError,
            SnowflakeClient,
            SnowflakeDataError,
            SnowflakeNetworkError,
        )
    except ImportError:
        return (
            False,
            "La librería ruvic-snowflake-connector no está instalada. "
            "Instala con: pip install git+https://github.com/Dgirto/"
            "Snowflake.git#subdirectory=lib",
        )

    try:
        client = SnowflakeClient()  # valida que existan las env vars
    except ValueError as exc:
        return False, str(exc)

    try:
        client.ping()
    except SnowflakeAuthError as exc:
        return False, f"Autenticación fallida: {exc}"
    except SnowflakeNetworkError as exc:
        return False, f"Error de red: {exc}"
    except SnowflakeDataError as exc:
        return False, f"Error de datos: {exc}"
    except Exception as exc:  # red de seguridad: jamás propagar
        return False, f"Error inesperado: {exc}"

    return (
        True,
        f"Conexión exitosa a Snowflake ({client.config.account})",
    )


if __name__ == "__main__":
    ok, message = test_connection()
    print(f"{'OK' if ok else 'FALLO'}: {message}")
    raise SystemExit(0 if ok else 1)
