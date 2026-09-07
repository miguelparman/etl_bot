#!/usr/bin/env bash
# Levanta el ambiente de pruebas local: SQL Server en Docker + esquema + datos
# sintéticos de cartera. Requiere Docker y Docker Compose instalados.
set -euo pipefail

cd "$(dirname "$0")/.."

SA_PASSWORD="${SA_PASSWORD:-Termometro_Test_2026!}"
PORT="14330"

echo ">> Levantando contenedor de SQL Server (puede tardar ~30-60s la primera vez)..."
SA_PASSWORD="$SA_PASSWORD" docker compose -f infra/docker-compose.yml up -d

echo ">> Esperando a que SQL Server esté listo..."
for i in $(seq 1 30); do
    if docker exec termometro_sqlserver_test /opt/mssql-tools18/bin/sqlcmd -C -S localhost -U sa -P "$SA_PASSWORD" -Q "SELECT 1" > /dev/null 2>&1; then
        echo "   Listo."
        break
    fi
    sleep 3
    if [ "$i" -eq 30 ]; then
        echo "   ERROR: SQL Server no respondió a tiempo. Revisa 'docker logs termometro_sqlserver_test'."
        exit 1
    fi
done

echo ">> Creando bases de datos y tablas..."
docker exec -i termometro_sqlserver_test /opt/mssql-tools18/bin/sqlcmd -C -S localhost -U sa -P "$SA_PASSWORD" < infra/sql/01_create_databases.sql
docker exec -i termometro_sqlserver_test /opt/mssql-tools18/bin/sqlcmd -C -S localhost -U sa -P "$SA_PASSWORD" < infra/sql/02_create_tables.sql

echo ">> Generando datos sintéticos de prueba (Excel, CSV, seed de cartera)..."
python3 scripts/generate_sample_data.py

echo ">> Cargando datos sintéticos en CL_CARTERA.TBL_HISTORIAL_CARTERA..."
docker exec -i termometro_sqlserver_test /opt/mssql-tools18/bin/sqlcmd -C -S localhost -U sa -P "$SA_PASSWORD" < infra/sql/03_seed_cartera.sql

echo ""
echo "✅ Ambiente de pruebas listo."
echo "   - SQL Server disponible en localhost:${PORT} (usuario 'sa')"
echo "   - Copia infra/.env.test a .env (o expórtalo) antes de correr el pipeline:"
echo "       cp infra/.env.test .env"
echo "       python main.py --periodo 202607 --fecha-inicio 2026-07-01 --fecha-fin 2026-07-31"
