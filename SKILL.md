---
name: snowflake
description: >
  Usa la librería ruvic_snowflake_connector para consultar y analizar
  datos en Snowflake en modo solo lectura - ejecutar una consulta SQL
  (execute_query), listar bases de datos y esquemas visibles
  (list_databases_and_schemas), y estimar el alcance de una consulta
  antes de ejecutarla (estimate_query_cost). Úsala cuando el usuario
  pida consultar, explorar o analizar datos en Snowflake.
triggers:
- snowflake
- data warehouse
- consulta sql en snowflake
---

# Conector Snowflake (ruvic_snowflake_connector)

Librería Python de solo lectura para Snowflake. Está **preinstalada en el runtime** cuando el conector está configurado (si no, instálala con `pip install git+https://github.com/Dgirto/Snowflake.git#subdirectory=lib`).

## Regla crítica de credenciales

El código generado **NUNCA hardcodea credenciales**. Siempre se leen de variables de entorno, disponibles cuando el conector `snowflake` está configurado:

| Variable | Contenido |
|----------|-----------|
| `RUVIC_SNOWFLAKE_ACCOUNT` | Identificador de cuenta |
| `RUVIC_SNOWFLAKE_USERNAME` | Usuario |
| `RUVIC_SNOWFLAKE_PASSWORD` | Contraseña |
| `RUVIC_SNOWFLAKE_WAREHOUSE` | Warehouse de cómputo |
| `RUVIC_SNOWFLAKE_DATABASE` | Base de datos |
| `RUVIC_SNOWFLAKE_SCHEMA` | Esquema |
| `RUVIC_SNOWFLAKE_ROLE` | (opcional) rol a asumir |
| `RUVIC_SNOWFLAKE_CONNECT_TIMEOUT` | (opcional) timeout en segundos |

Si estas variables NO existen, el conector no está configurado: no generes código que lo use; indica al usuario que lo configure en **Settings → Conectores**.

## Solo se permiten sentencias SELECT

`execute_query` y `estimate_query_cost` rechazan cualquier sentencia que no empiece con `SELECT` o `WITH` (INSERT, UPDATE, DELETE, CREATE, DROP, MERGE, etc.), sin importar el rol otorgado.

## Conexión (siempre igual)

```python
from ruvic_snowflake_connector import SnowflakeClient

client = SnowflakeClient()  # lee RUVIC_SNOWFLAKE_* del entorno automáticamente
```

## Capacidad 1 — Ejecutar una consulta SQL

```python
rows = client.execute_query(
    "SELECT cliente, SUM(total) AS total FROM pedidos GROUP BY cliente LIMIT 100"
)
for row in rows:
    print(row)
```

Usa nombres completamente calificados (`BASE.ESQUEMA.TABLA`) si consultas fuera del esquema por defecto configurado. Incluye siempre un `LIMIT` razonable en consultas exploratorias.

## Capacidad 2 — Listar bases de datos y esquemas

```python
catalogo = client.list_databases_and_schemas()
for base, esquemas in catalogo.items():
    print(f"{base}: {esquemas}")
```

## Capacidad 3 — Estimar el alcance de una consulta (sin ejecutarla)

```python
estimado = client.estimate_query_cost("SELECT * FROM pedidos WHERE fecha > '2026-01-01'")
print(estimado["plan"])
```

Usa `EXPLAIN` internamente: no ejecuta la consulta ni genera cargos de cómputo. A diferencia de BigQuery, Snowflake no da un costo exacto en dólares vía API estándar — el plan retornado indica qué tablas/particiones tocaría la consulta, útil como señal de alcance antes de ejecutarla sobre datasets grandes.

## Manejo de errores

```python
from ruvic_snowflake_connector import (
    SnowflakeAuthError, SnowflakeDataError, SnowflakeNetworkError,
)

try:
    rows = client.execute_query("SELECT * FROM pedidos LIMIT 10")
except SnowflakeAuthError:
    print("Credenciales inválidas o sin permiso IAM suficiente")
except SnowflakeNetworkError:
    print("No se pudo alcanzar Snowflake — reintenta en unos segundos")
except SnowflakeDataError as e:
    print(f"Error de datos: {e}")  # ej. la consulta es inválida o no es SELECT
```

## Buenas prácticas al generar código

1. Lee credenciales SOLO de las variables `RUVIC_SNOWFLAKE_*` (el constructor de `SnowflakeClient` ya lo hace).
2. Nunca imprimas `RUVIC_SNOWFLAKE_PASSWORD` en logs ni en la salida.
3. La librería es de SOLO LECTURA: no intentes construir SQL con INSERT/UPDATE/DELETE, el conector los rechaza igual.
4. Antes de ejecutar una consulta sobre una tabla grande o sin `WHERE`/`LIMIT`, usa `estimate_query_cost` primero para ver el plan.
5. Usa `max_rows` razonable en `execute_query` (default 1000, máximo 10000) para no traer resultados masivos a memoria.
