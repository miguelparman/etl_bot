import os
import time
import shutil
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.firefox.options import Options
from webdriver_manager.firefox import GeckoDriverManager
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# Ruta de la carpeta donde se descargará el archivo
carpeta_descargas = r"D:\Descargas"
# Ruta y nombre del archivo final que deseas
ruta_destino = r"D:\IRISCENE ENGINEERING CORPORATION SLU\Data Analytics Reporting Fractalia - Medallia\Encuestas_Medallia.csv"

# Prefijo de los archivos que quieres filtrar
prefijo_archivo = "Telefonica Moviles Chile SA_export_"

# Configuración de FirefoxOptions
firefox_options = Options()
firefox_options.add_argument("--headless")  # Ejecuta Firefox en modo headless

# Configuración de preferencias para descargas directamente en las opciones
firefox_options.set_preference("browser.download.folderList", 2)
firefox_options.set_preference("browser.download.manager.showWhenStarting", False)
firefox_options.set_preference("browser.download.dir", carpeta_descargas)
firefox_options.set_preference("browser.helperApps.neverAsk.saveToDisk", "text/csv,application/csv,application/vnd.ms-excel,text/plain")
firefox_options.set_preference("pdfjs.disabled", True)
firefox_options.set_preference("browser.download.manager.useWindow", False)
firefox_options.set_preference("browser.download.manager.focusWhenStarting", False)
firefox_options.set_preference("browser.helperApps.alwaysAsk.force", False)
firefox_options.set_preference("browser.download.manager.alertOnEXEOpen", False)
firefox_options.set_preference("browser.download.manager.showAlertOnComplete", False)
firefox_options.set_preference("browser.download.manager.closeWhenDone", True)
firefox_options.set_preference("browser.tabs.warnOnClose", False)
firefox_options.set_preference("browser.tabs.warnOnOpen", False)
firefox_options.set_preference("network.http.use-cache", False)
firefox_options.set_preference("browser.cache.disk.enable", False)
firefox_options.set_preference("browser.cache.memory.enable", False)
firefox_options.set_preference("browser.cache.offline.enable", False)
firefox_options.set_preference("network.http.use-cache", False)

# Inicializar WebDriver para Firefox usando webdriver-manager
print("Iniciando el navegador Firefox en modo headless...")
driver = webdriver.Firefox(
    service=Service(GeckoDriverManager().install()),
    options=firefox_options
)

try:
    # URL de Login
    url_login = 'https://telefonicacl.medallia.com/telefonicacl/'
    # URL de la página de registros
    url_registros = 'https://telefonicacl.medallia.com/telefonicacl/applications/ex_WEB-9/pages/208?roleId=646&f.pfe_tf_tipo_encuesta_enum=543_9&f.timeperiod=490&fi.pfe_tf_tipo_encuesta_enum=543_9&fi.timeperiod=490'
    #url_registros = 'https://telefonicacl.medallia.com/telefonicacl/applications/ex_WEB-9/pages/208?roleId=646&f.pfe_tf_tipo_encuesta_enum=543_9&f.timeperiod=4486&fi.pfe_tf_tipo_encuesta_enum=543_9&fi.timeperiod=490'
    print("Accediendo a la página de inicio de sesión...")
    # Abrimos la página de login
    driver.get(url_login)

    # Esperamos a que los campos de usuario y contraseña estén presentes
    print("Esperando a que aparezcan los campos de inicio de sesión...")
    username = WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.NAME, "username")))
    password = driver.find_element(By.NAME, "password")

    # Ingresamos las credenciales (reemplaza con tus datos)
    print("Ingresando las credenciales...")
    # Ingresamos las credenciales (reemplaza con tus datos)
    username.send_keys("abraham.ramirez")
    password.send_keys("/b38vIArH!D2_2")
    
    # Iniciar sesión
    print("Iniciando sesión...")
    driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()

    # Esperamos a que el inicio de sesión se complete y la nueva URL cargue
    print("Esperando a que se complete el inicio de sesión...")
    WebDriverWait(driver, 20).until(EC.url_changes(url_login))

    # Navegamos a la página de registros
    print("Navegando a la página de registros...")
    driver.get(url_registros)

    # Esperamos que el botón de exportación esté disponible y hacemos clic
    print("Esperando al botón de exportación...")
    desplegar_opciones_button = WebDriverWait(driver, 30).until(
        EC.element_to_be_clickable((By.ID, "openExportMenu"))
    )
    print("Haciendo clic en el botón de exportación...")
    desplegar_opciones_button.click()

    # Esperamos que la opción de CSV esté disponible y hacemos clic
    print("Esperando a la opción de exportación CSV...")
    export_csv_button = WebDriverWait(driver, 30).until(
        EC.element_to_be_clickable((By.XPATH, '//button[@data-title="CSV"]'))
    )
    print("Haciendo clic en la opción de exportación CSV...")
    export_csv_button.click()

    # Esperamos a que el archivo se descargue
    print("Esperando a que se descargue el archivo...")
    time.sleep(10)  # Ajusta el tiempo si la descarga toma más tiempo

    # Verificamos si el archivo ha sido descargado
    print("Verificando si el archivo ha sido descargado...")
    archivos_filtrados = [f for f in os.listdir(carpeta_descargas) if f.startswith(prefijo_archivo)]
    if archivos_filtrados:
        archivo_descargado = max(
            [os.path.join(carpeta_descargas, f) for f in archivos_filtrados],
            key=os.path.getctime
        )

        # Movemos y renombramos el archivo al destino final
        shutil.move(archivo_descargado, ruta_destino)
        print(f"Archivo descargado y renombrado a: {ruta_destino}")
    else:
        print(f"No se encontró ningún archivo que comience con '{prefijo_archivo}' en la carpeta de descargas.")

except Exception as e:
    print(f"Ocurrió un error: {e}")

finally:
    print("Cerrando el navegador...")
    driver.quit()
    print("Proceso completado.")