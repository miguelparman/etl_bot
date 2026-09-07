import pyodbc
from datetime import datetime
from dateutil.relativedelta import relativedelta

BATCH_SIZE = 1000

hoy = datetime.today()
periodo_actual = hoy.strftime("%Y%m")
dos_meses_atras = hoy - relativedelta(months=1)
periodo_anterior = dos_meses_atras.strftime("%Y%m")
periodo = periodo_anterior if hoy.day <= 4 else periodo_actual

print(f"Período: {periodo}")

cursor_src = None
cursor_dest = None
conn_src = None
conn_dest = None

try:
    conn_src = pyodbc.connect(
        "DRIVER={ODBC Driver 17 for SQL Server};"
        "SERVER=sqlclu01lis01.tchile.local;"
        "DATABASE=Externos_Frac;"
        "Trusted_Connection=yes;"
        "TrustServerCertificate=yes;",
        autocommit=True
    )
    print("Conexión al servidor Chile exitosa.")

    conn_dest = pyodbc.connect(
        "DRIVER={ODBC Driver 17 for SQL Server};"
        "SERVER=172.17.0.162;"
        "DATABASE=CL_TEMPORALES;"
        "UID=palermo.reyes;"
        "PWD=Fractalia2025%"
    )
    print("Conexión al servidor TCH exitosa.")

    cursor_src = conn_src.cursor()
    cursor_dest = conn_dest.cursor()

    # Contar total de registros
    cursor_src.execute(
        "SELECT COUNT(*) FROM [Externos_Frac].[dbo].[CALLBACK] "
        "WHERE CONVERT(VARCHAR(6),[FECHA],112) >= ?", (periodo,)
    )
    total_registros = cursor_src.fetchone()[0]
    print(f"Total de registros a cargar: {total_registros:,}")

    if total_registros == 0:
        print("No hay registros para cargar.")
    else:
        tiempo_inicio = datetime.now()
        print(f"Inicio: {tiempo_inicio.strftime('%Y-%m-%d %H:%M:%S')}")

        cursor_src.execute(
            "SELECT * FROM [Externos_Frac].[dbo].[CALLBACK] "
            "WHERE CONVERT(VARCHAR(6),[FECHA],112) >= ?", (periodo,)
        )

        sql_insert = """
            INSERT INTO [CL_TEMPORALES].[dbo].[TBL_TRAFICO_CALLBACK](
                [ANI],[ID],[NRO_DISCAR],[OPCION],[FECHA],[ESTADO],[AGENTE],[RESULTADO],
                [HORA_INICIO_LLAMADA],[HORA_FIN_LLAMADA],[NOMBRE_AGENTE],[TIPO_CLIENTE],
                [ID_GENESYS],[SKILL],[FECHA_EXTRACCION]
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """

        insertados = 0
        errores = 0

        while True:
            lote = cursor_src.fetchmany(BATCH_SIZE)
            if not lote:
                break

            datos = [
                (r.ANI, r.ID, r.NRO_DISCAR, r.OPCION, r.FECHA, r.ESTADO, r.AGENTE,
                 r.RESULTADO, r.HORA_INICIO_LLAMADA, r.HORA_FIN_LLAMADA, r.NOMBRE_AGENTE,
                 r.TIPO_CLIENTE, r.ID_GENESYS, r.SKILL, r.FECHA_EXTRACCION)
                for r in lote
            ]

            try:
                cursor_dest.executemany(sql_insert, datos)
                conn_dest.commit()
                insertados += len(datos)
            except pyodbc.Error as insert_err:
                errores += len(datos)
                print(f"Error en lote: {insert_err}")

            porcentaje = (insertados + errores) / total_registros * 100
            transcurrido = datetime.now() - tiempo_inicio
            print(
                f"  Progreso: {insertados + errores:,}/{total_registros:,} "
                f"({porcentaje:.1f}%) | Transcurrido: {str(transcurrido).split('.')[0]}",
                end="\r"
            )

        tiempo_fin = datetime.now()
        transcurrido_total = tiempo_fin - tiempo_inicio

        print()  # salto de línea tras el \r
        print("-" * 60)
        print(f"Inicio:      {tiempo_inicio.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Fin:         {tiempo_fin.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Transcurrido:{str(transcurrido_total).split('.')[0]}")
        print(f"Insertados:  {insertados:,}")
        if errores:
            print(f"Errores:     {errores:,}")
        print("-" * 60)

except pyodbc.Error as e:
    print(f"\nError en la conexión o en la operación SQL: {e}")

finally:
    for obj in [cursor_src, conn_src, cursor_dest, conn_dest]:
        try:
            if obj:
                obj.close()
        except Exception:
            pass
    print("Conexiones cerradas.")
