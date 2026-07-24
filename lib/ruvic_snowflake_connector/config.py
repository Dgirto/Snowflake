"""Configuración del conector leída desde variables de entorno.

Convención de la plataforma: cada campo del formulario de configuración
llega como variable de entorno {ENV_PREFIX}{CAMPO} en mayúsculas.
Para este conector el prefijo es RUVIC_SNOWFLAKE_.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

ENV_PREFIX = "RUVIC_SNOWFLAKE_"


@dataclass(frozen=True)
class SnowflakeConfig:
    """Parámetros de conexión a Snowflake."""

    account: str
    username: str
    password: str
    warehouse: str
    database: str
    schema: str
    role: str | None = None
    connect_timeout: int = 30

    @classmethod
    def from_env(cls) -> "SnowflakeConfig":
        """Construye la configuración desde las variables RUVIC_SNOWFLAKE_*.

        Raises:
            ValueError: si falta alguna variable obligatoria.

        Ejemplo:
            >>> config = SnowflakeConfig.from_env()
            >>> config.account
            'xy12345.us-east-1'
        """
        missing = [
            f"{ENV_PREFIX}{name}"
            for name in ("ACCOUNT", "USERNAME", "PASSWORD", "WAREHOUSE", "DATABASE", "SCHEMA")
            if not os.environ.get(f"{ENV_PREFIX}{name}")
        ]
        if missing:
            raise ValueError(
                "Faltan variables de entorno del conector snowflake: "
                + ", ".join(missing)
                + ". Configura el conector en Settings → Conectores."
            )
        return cls(
            account=os.environ[f"{ENV_PREFIX}ACCOUNT"],
            username=os.environ[f"{ENV_PREFIX}USERNAME"],
            password=os.environ[f"{ENV_PREFIX}PASSWORD"],
            warehouse=os.environ[f"{ENV_PREFIX}WAREHOUSE"],
            database=os.environ[f"{ENV_PREFIX}DATABASE"],
            schema=os.environ[f"{ENV_PREFIX}SCHEMA"],
            role=os.environ.get(f"{ENV_PREFIX}ROLE") or None,
            connect_timeout=int(os.environ.get(f"{ENV_PREFIX}CONNECT_TIMEOUT", "30")),
        )
