"""Validación local del conector snowflake: ejercita las 3 capacidades.

Uso:
    python validate_local.py

Requiere las variables RUVIC_SNOWFLAKE_* exportadas en el entorno, y una
tabla "pedidos" accesible en el esquema configurado.
"""

from ruvic_snowflake_connector import SnowflakeClient, setup_logging

setup_logging("INFO")
client = SnowflakeClient()

print("== 1. Ejecutar consulta SQL ==")
rows = client.execute_query("SELECT * FROM pedidos LIMIT 10")
for row in rows:
    print(f"  {row}")

print("== 2. Listar bases de datos y esquemas ==")
for database, schemas in client.list_databases_and_schemas().items():
    print(f"  {database}: {schemas}")

print("== 3. Estimar alcance de una consulta ==")
estimate = client.estimate_query_cost("SELECT * FROM pedidos")
print(f"  warehouse={estimate['warehouse']}")
print(f"  plan:\n{estimate['plan']}")

print("\nTodo OK: execute_query, list_databases_and_schemas y estimate_query_cost funcionan.")
