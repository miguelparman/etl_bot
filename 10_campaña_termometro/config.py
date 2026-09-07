"""
Configuración del pipeline, leída desde variables de entorno (.env).

Reemplaza:
- Los Connection Managers del .dtsx (OLEDB "162", EXCEL "ACTUAL_", FLATFILE "Reporte_termometro_v2")
- Las variables User::Fecha_inicio, User::Fecha_fin, User::Periodo
"""
import os
from datetime import date
from dataclasses import dataclass

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # python-dotenv es opcional; si no está, se usan variables de entorno del sistema


@dataclass(frozen=True)
class Settings:
    # --- Conexión SQL Server (reemplaza Connection Manager "162") ---
    db_server: str = os.getenv("DB_SERVER", "172.17.0.162")
    db_database: str = os.getenv("DB_DATABASE", "CL_CAMPAÑAS")
    db_user: str = os.getenv("DB_USER", "")
    db_password: str = os.getenv("DB_PASSWORD", "")
    db_driver: str = os.getenv("DB_DRIVER", "ODBC Driver 18 for SQL Server")

    # --- Base de datos de cartera (usada en el JOIN final) ---
    db_cartera_database: str = os.getenv("DB_CARTERA_DATABASE", "CL_CARTERA")

    # --- Rutas de archivos fuente (reemplaza Connection Manager "ACTUAL_" y "Reporte_termometro_v2") ---
    excel_clientes_path: str = os.getenv(
        "EXCEL_CLIENTES_PATH",
        r"D:\IRISCENE ENGINEERING CORPORATION SLU\BPO - Insumos\Chile\Campanhas\Termometro\SOURCE\ACTUAL_.xlsx",
    )
    excel_clientes_sheet: str = os.getenv("EXCEL_CLIENTES_SHEET", "DB")
    excel_detractores_sheet: str = os.getenv("EXCEL_DETRACTORES_SHEET", "DB_DETRACTOR")

    csv_salesforce_path: str = os.getenv(
        "CSV_SALESFORCE_PATH",
        r"D:\IRISCENE ENGINEERING CORPORATION SLU\BPO - Insumos\Chile\Campanhas\Termometro\SF\Reporte_termometros_v2.csv",
    )
    csv_salesforce_encoding: str = os.getenv("CSV_SALESFORCE_ENCODING", "latin-1")
    csv_salesforce_delimiter: str = os.getenv("CSV_SALESFORCE_DELIMITER", ",")

    # --- Parámetros del proceso (reemplaza User::Periodo, User::Fecha_inicio, User::Fecha_fin) ---
    periodo: int = int(os.getenv("PERIODO", date.today().strftime("%Y%m")))
    fecha_inicio: str = os.getenv("FECHA_INICIO", date.today().replace(day=1).isoformat())
    fecha_fin: str = os.getenv("FECHA_FIN", date.today().isoformat())

    @property
    def sqlalchemy_url(self) -> str:
        from urllib.parse import quote_plus

        odbc_str = (
            f"DRIVER={{{self.db_driver}}};"
            f"SERVER={self.db_server};"
            f"DATABASE={self.db_database};"
            f"UID={self.db_user};PWD={self.db_password};"
            f"TrustServerCertificate=yes;"
        )
        return f"mssql+pyodbc:///?odbc_connect={quote_plus(odbc_str)}"


settings = Settings()
