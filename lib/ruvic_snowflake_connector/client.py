"""Cliente de consulta de solo lectura para Snowflake.

Capacidades:
- list_databases_and_schemas(): listar bases de datos y esquemas visibles.
- execute_query():               ejecutar una consulta SQL de solo lectura.
- estimate_query_cost():         estimar el costo de una consulta (EXPLAIN,
                                  sin ejecutarla).

Las credenciales SIEMPRE provienen de variables de entorno RUVIC_SNOWFLAKE_*
(ver config.SnowflakeConfig.from_env). Prohibido hardcodearlas.
"""

from __future__ import annotations

from typing import Any

import snowflake.connector
from snowflake.connector.errors import DatabaseError, OperationalError, ProgrammingError

from .config import SnowflakeConfig
from .exceptions import (
    SnowflakeAuthError,
    SnowflakeConnectorError,
    SnowflakeDataError,
    SnowflakeNetworkError,
)
from .logging_utils import get_logger

_MAX_ROWS = 10_000


def _validate_select(query: str) -> str:
    query = (query or "").strip()
    if not query:
        raise SnowflakeDataError("La consulta SQL no puede estar vacía.")
    if not query.rstrip(";").strip().upper().startswith(("SELECT", "WITH")):
        raise SnowflakeDataError(
            "Solo se permiten sentencias SELECT (o WITH ... SELECT). La "
            "operación solicitada fue rechazada por seguridad."
        )
    return query


class SnowflakeClient:
    """Cliente de consulta de solo lectura sobre una cuenta de Snowflake.

    Args:
        config: configuración de conexión. Si se omite, se lee de las
            variables de entorno RUVIC_SNOWFLAKE_* (comportamiento
            estándar en el runtime de la plataforma).

    Ejemplo:
        >>> client = SnowflakeClient()  # lee RUVIC_SNOWFLAKE_* del entorno
        >>> client.execute_query("SELECT 1")
        [{'1': 1}]
    """

    def __init__(self, config: SnowflakeConfig | None = None) -> None:
        self.config = config or SnowflakeConfig.from_env()
        self._logger = get_logger()
        self._conn: snowflake.connector.SnowflakeConnection | None = None

    # ------------------------------------------------------------------ #
    # Conexión
    # ------------------------------------------------------------------ #

    def _get_connection(self) -> snowflake.connector.SnowflakeConnection:
        if self._conn is not None:
            return self._conn
        try:
            self._conn = snowflake.connector.connect(
                account=self.config.account,
                user=self.config.username,
                password=self.config.password,
                warehouse=self.config.warehouse,
                database=self.config.database,
                schema=self.config.schema,
                role=self.config.role,
                login_timeout=self.config.connect_timeout,
                network_timeout=self.config.connect_timeout,
            )
        except DatabaseError as exc:
            if getattr(exc, "errno", None) in (250001, 251005) or "password" in str(exc).lower():
                raise SnowflakeAuthError(
                    "Credenciales inválidas o sin permiso suficiente sobre "
                    "esta cuenta de Snowflake."
                ) from exc
            raise SnowflakeNetworkError(f"No se pudo conectar a Snowflake: {exc}") from exc
        except OperationalError as exc:
            raise SnowflakeNetworkError(
                f"No se pudo alcanzar la cuenta {self.config.account!r}: {exc}"
            ) from exc
        return self._conn

    def ping(self) -> bool:
        """Verifica la conexión ejecutando `SELECT 1`.

        Returns:
            True si la conexión funciona.

        Raises:
            SnowflakeAuthError / SnowflakeNetworkError / SnowflakeDataError
            según el fallo.
        """
        try:
            cursor = self._get_connection().cursor()
            cursor.execute("SELECT 1")
            cursor.fetchall()
            cursor.close()
        except SnowflakeConnectorError:
            raise
        except Exception as exc:
            raise SnowflakeNetworkError(f"No se pudo conectar: {exc}") from exc
        self._logger.info("Ping exitoso a Snowflake %s", self.config.account)
        return True

    # ------------------------------------------------------------------ #
    # Capacidad 1: listar bases de datos y esquemas
    # ------------------------------------------------------------------ #

    def list_databases_and_schemas(self) -> dict[str, list[str]]:
        """Lista las bases de datos visibles y los esquemas de cada una.

        Returns:
            Dict {database: [schema, ...]}.

        Ejemplo:
            >>> client.list_databases_and_schemas()
            {'VENTAS': ['PUBLIC', 'STAGING']}
        """
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SHOW DATABASES")
            databases = [row[1] for row in cursor.fetchall()]
            result: dict[str, list[str]] = {}
            for database in databases:
                cursor.execute(f'SHOW SCHEMAS IN DATABASE "{database}"')
                result[database] = [row[1] for row in cursor.fetchall()]
            cursor.close()
        except ProgrammingError as exc:
            raise SnowflakeDataError(f"Error al listar bases/esquemas: {exc}") from exc
        except Exception as exc:
            raise SnowflakeDataError(f"Error al listar bases/esquemas: {exc}") from exc

        self._logger.info("Se listaron %d bases de datos", len(result))
        return result

    # ------------------------------------------------------------------ #
    # Capacidad 2: ejecutar consulta SQL de solo lectura
    # ------------------------------------------------------------------ #

    def execute_query(self, query: str, max_rows: int = 1000) -> list[dict[str, Any]]:
        """Ejecuta una consulta SQL de solo lectura (SELECT).

        Args:
            query: sentencia SQL. Debe empezar con SELECT o WITH; cualquier
                otra cosa (INSERT, UPDATE, DELETE, CREATE, DROP, MERGE) se
                rechaza a nivel de código.
            max_rows: máximo de filas a retornar (default 1000, máximo
                10000).

        Returns:
            Lista de dicts, una por fila.

        Ejemplo:
            >>> client.execute_query("SELECT cliente, total FROM pedidos LIMIT 10")
            [{'CLIENTE': 'ACME', 'TOTAL': 1200}]
        """
        query = _validate_select(query)
        max_rows = max(1, min(int(max_rows), _MAX_ROWS))
        conn = self._get_connection()
        try:
            cursor = conn.cursor(snowflake.connector.DictCursor)
            cursor.execute(query)
            rows = cursor.fetchmany(max_rows)
            cursor.close()
        except ProgrammingError as exc:
            raise SnowflakeDataError(f"Consulta SQL inválida: {exc}") from exc
        except Exception as exc:
            raise SnowflakeDataError(f"Error al ejecutar la consulta: {exc}") from exc

        self._logger.info("execute_query devolvió %d filas", len(rows))
        return list(rows)

    # ------------------------------------------------------------------ #
    # Capacidad 3: estimar el costo de una consulta
    # ------------------------------------------------------------------ #

    def estimate_query_cost(self, query: str) -> dict[str, Any]:
        """Estima el alcance de una consulta antes de ejecutarla, usando
        `EXPLAIN` (no ejecuta la consulta ni genera cargos de cómputo).

        Args:
            query: sentencia SQL a estimar. Debe empezar con SELECT o WITH.

        Returns:
            Dict con: plan (texto del plan de ejecución), warehouse
            (almacén de cómputo que se usaría).

        Ejemplo:
            >>> client.estimate_query_cost("SELECT * FROM pedidos")
            {'plan': '...', 'warehouse': 'COMPUTE_WH'}

        Nota:
            A diferencia de BigQuery, Snowflake no expone un dry-run con
            bytes exactos a procesar vía API estándar; `EXPLAIN` retorna
            el plan de ejecución (tablas/particiones involucradas), que
            sirve como indicador aproximado del alcance de la consulta.
            El costo real depende del tamaño del warehouse y el tiempo de
            ejecución, no solo de los datos escaneados.
        """
        query = _validate_select(query)
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(f"EXPLAIN USING TEXT {query}")
            plan_rows = cursor.fetchall()
            cursor.close()
        except ProgrammingError as exc:
            raise SnowflakeDataError(f"No se pudo generar el plan de la consulta: {exc}") from exc
        except Exception as exc:
            raise SnowflakeDataError(f"Error al estimar la consulta: {exc}") from exc

        plan_text = "\n".join(str(row[0]) for row in plan_rows)
        self._logger.info("Plan de ejecución generado (%d líneas)", len(plan_rows))
        return {"plan": plan_text, "warehouse": self.config.warehouse}
