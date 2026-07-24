# Conector Snowflake (CON-057)

Conector Ruvic de consulta de solo lectura para Snowflake. Permite
ejecutar consultas SQL de solo lectura (SELECT), listar bases de datos y
esquemas visibles, y estimar el alcance de una consulta antes de
ejecutarla (vía `EXPLAIN`).

## Instalación

```bash
pip install git+https://github.com/Dgirto/Snowflake.git#subdirectory=lib
```

Python 3.10+. Dependencia única: `snowflake-connector-python>=3.6,<4.0`.

## Permisos requeridos en Snowflake

Crea un rol y usuario dedicados de solo lectura:

```sql
CREATE ROLE ruvic_reader;
GRANT USAGE ON WAREHOUSE compute_wh TO ROLE ruvic_reader;
GRANT USAGE ON DATABASE ventas TO ROLE ruvic_reader;
GRANT USAGE ON SCHEMA ventas.public TO ROLE ruvic_reader;
GRANT SELECT ON ALL TABLES IN SCHEMA ventas.public TO ROLE ruvic_reader;
GRANT SELECT ON FUTURE TABLES IN SCHEMA ventas.public TO ROLE ruvic_reader;

CREATE USER ruvic_gonector PASSWORD = 'CAMBIA_ESTA_CONTRASEÑA' DEFAULT_ROLE = ruvic_reader;
GRANT ROLE ruvic_reader TO USER ruvic_gonector;
```

- `USAGE` sobre el warehouse: necesario para ejecutar cualquier consulta
  (el cómputo se cobra por tiempo de warehouse activo).
- `SELECT` sobre las tablas a exponer: necesario para `db.execute_query`
  y `db.estimate_query_cost`.
- No se otorgan permisos de escritura (`INSERT`, `UPDATE`, `DELETE`) ni de
  administración (`CREATE`, `DROP`, `GRANT`).

## Variables de entorno (`RUVIC_SNOWFLAKE_*`)

| Variable | Obligatoria | Descripción |
|----------|-------------|-------------|
| `RUVIC_SNOWFLAKE_ACCOUNT` | Sí | Identificador de cuenta (ej. `xy12345.us-east-1`) |
| `RUVIC_SNOWFLAKE_USERNAME` | Sí | Usuario |
| `RUVIC_SNOWFLAKE_PASSWORD` | Sí | Contraseña |
| `RUVIC_SNOWFLAKE_WAREHOUSE` | Sí | Warehouse de cómputo |
| `RUVIC_SNOWFLAKE_DATABASE` | Sí | Base de datos |
| `RUVIC_SNOWFLAKE_SCHEMA` | Sí | Esquema (ej. `PUBLIC`) |
| `RUVIC_SNOWFLAKE_ROLE` | No | Rol a asumir |
| `RUVIC_SNOWFLAKE_CONNECT_TIMEOUT` | No (default `30`) | Timeout de conexión en segundos |

## Pruebas locales

Con una cuenta Snowflake real (Snowflake no es viable en Docker local;
usa el free trial de 30 días o una cuenta de prueba existente):

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ./lib

export RUVIC_SNOWFLAKE_ACCOUNT=xy12345.us-east-1
export RUVIC_SNOWFLAKE_USERNAME=ruvic_gonector
export RUVIC_SNOWFLAKE_PASSWORD=tu-contraseña
export RUVIC_SNOWFLAKE_WAREHOUSE=COMPUTE_WH
export RUVIC_SNOWFLAKE_DATABASE=ventas
export RUVIC_SNOWFLAKE_SCHEMA=public

python test_connection.py
python validate_local.py
```

Prueba también los casos de error (credenciales incorrectas, tabla
inexistente, sentencia no-SELECT rechazada) y verifica que los mensajes
sean claros.

## Notas de integración

- `execute_query` y `estimate_query_cost` validan a nivel de código que
  la sentencia empiece con `SELECT` o `WITH`; cualquier otra cosa
  (`INSERT`, `UPDATE`, `DELETE`, `CREATE`, `DROP`, `MERGE`) se rechaza
  antes de llegar a Snowflake.
- `estimate_query_cost` usa `EXPLAIN USING TEXT`, que no ejecuta la
  consulta ni genera cargos de cómputo, pero tampoco da un costo en
  dólares exacto (a diferencia del dry run de BigQuery) — retorna el
  plan de ejecución como indicador aproximado del alcance.
- Las consultas ejecutadas con `execute_query` sí consumen tiempo de
  cómputo del warehouse configurado (y por lo tanto generan cargos
  reales según el plan de Snowflake).
