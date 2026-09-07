FROM python:3.12-slim

# Driver ODBC de Microsoft para SQL Server (msodbcsql18) - unico componente
# "Microsoft" que se mantiene, porque el destino de datos sigue siendo SQL
# Server (ver seccion 6 del analisis: no se migra la base, solo el ETL).
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl gnupg apt-transport-https ca-certificates \
    && curl https://packages.microsoft.com/keys/microsoft.asc | apt-key add - \
    && curl https://packages.microsoft.com/config/debian/12/prod.list > /etc/apt/sources.list.d/mssql-release.list \
    && apt-get update \
    && ACCEPT_EULA=Y apt-get install -y --no-install-recommends msodbcsql18 \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ src/
COPY sql/ sql/
COPY main.py .
COPY pytest.ini .

RUN mkdir -p logs

ENTRYPOINT ["python", "main.py"]
