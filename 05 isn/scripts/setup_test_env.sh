#!/usr/bin/env bash
# Levanta el ambiente de pruebas local para Contactos: SQL Server en Docker +
# esquema + CSV sintético. Requiere Docker y Docker Compose instalados.
#
# ISN no tiene ambiente local (ver README): sus queries tocan 7 bases de
# datos de producción distintas y replicarlas localmente es desproporcionado
# frente al alcance de esta migración -- su paridad se valida corriendo el
# .dtsx original y este pipeline sobre los mismos datos reales/restaurados
# (ver parity/).
set -euo pipefail

cd "$(dirname "$0")/.."

SA_PASSWORD="${SA_PASSWORD:-Contactos_Test_2026!}"
PORT="14331"
CONTAINER="isn_contactos_sqlserver_test"

echo ">> Levantando contenedor de SQL Server (puede tardar ~30-60s la primera vez)..."
SA_PASSWORD="$SA_PASSWORD" docker compose -f infra/docker-compose.yml up -d

echo ">> Esperando a que SQL Server esté listo..."
for i in $(seq 1 30); do
    if docker exec "$CONTAINER" /opt/mssql-tools18/bin/sqlcmd -C -S localhost -U sa -P "$SA_PASSWORD" -Q "SELECT 1" > /dev/null 2>&1; then
        echo "   Listo."
        break
    fi
    sleep 3
    if [ "$i" -eq 30 ]; then
        echo "   ERROR: SQL Server no respondió a tiempo. Revisa 'docker logs $CONTAINER'."
        exit 1
    fi
done

echo ">> Creando base de datos y tablas..."
docker exec -i "$CONTAINER" /opt/mssql-tools18/bin/sqlcmd -C -S localhost -U sa -P "$SA_PASSWORD" < infra/sql/01_create_databases.sql
docker exec -i "$CONTAINER" /opt/mssql-tools18/bin/sqlcmd -C -S localhost -U sa -P "$SA_PASSWORD" < infra/sql/02_create_tables.sql

echo ">> Generando CSV sintético de contactos..."
python3 scripts/generate_sample_data.py

echo ""
echo "Ambiente de pruebas listo."
echo "   - SQL Server disponible en localhost:${PORT} (usuario 'sa')"
echo "   - Copia infra/.env.test a .env antes de correr el pipeline:"
echo "       cp infra/.env.test .env"
echo "       python main.py --saltar isn"
