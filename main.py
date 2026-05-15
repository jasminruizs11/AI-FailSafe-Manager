
import json
import logging
from pathlib import Path
from getpass import getpass
from pydantic import BaseModel, Field
from tenacity import retry, stop_after_attempt, wait_exponential
from google import genai

# ==========================================
# 1. CONFIGURACIÓN CORPORATIVA Y LOGGING
# ==========================================
# Reemplazamos los 'prints' por un sistema de logs real
logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - [%(levelname)s] - %(message)s'
)

BACKUP_DIR = Path("backup_data")
BACKUP_DIR.mkdir(exist_ok=True)

# Clave maestra para recuperar datos sensibles (En producción usar variables de entorno)
AUTH_KEY_ADMIN = "admin2026"

# ==========================================
# 2. ESTRUCTURA DE DATOS ESTRICTA (Pydantic)
# ==========================================
class PaqueteDatos(BaseModel):
    id_operacion: str
    contenido: str
    es_sensible: bool = Field(description="Clasificación definida por el usuario. True = Requiere Auth.")
    metadata: dict = Field(default_factory=dict)

# ==========================================
# 3. LÓGICA DE IA CON REINTENTOS (Tenacity)
# ==========================================
# Si falla, espera 2 segundos y reintenta. Sube el tiempo exponencialmente hasta 3 intentos.
@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
def procesar_con_ia(paquete: PaqueteDatos):
    logging.info(f"Conectando a IA para operación {paquete.id_operacion}...")
    
    # Usamos una Key falsa a propósito para forzar la falla y ver el Fail-Safe en acción
    client = genai.Client(api_key="API_KEY_CAIDA_PARA_SIMULACION")
    
    response = client.models.generate_content(
        model='gemini-2.5-flash',
        contents=f"Procesa esta información: {paquete.contenido}"
    )
    return response.text

# ==========================================
# 4. FAIL-SAFE Y PERSISTENCIA LOCAL
# ==========================================
def activar_fail_safe(paquete: PaqueteDatos, error_msg: str):
    """Encapsula los datos y los protege en el disco local."""
    archivo_destino = BACKUP_DIR / f"contingencia_{paquete.id_operacion}.json"
    
    payload = {
        "error_tecnico": str(error_msg),
        "datos": paquete.model_dump() # Convierte el modelo Pydantic a diccionario seguro
    }
    
    with open(archivo_destino, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=4, ensure_ascii=False)
    
    logging.warning(f"FAIL-SAFE ACTIVADO. Datos asegurados en {archivo_destino}")

# ==========================================
# 5. PROTOCOLO DE RECUPERACIÓN CON PERMISOS
# ==========================================
def recuperar_contingencias():
    """Lee los backups. Si es sensible, exige credenciales antes de procesar."""
    archivos = list(BACKUP_DIR.glob("contingencia_*.json"))
    
    if not archivos:
        logging.info("El sistema está estable. No hay contingencias pendientes.")
        return

    logging.info(f"Iniciando Protocolo de Recuperación. Archivos detectados: {len(archivos)}")
    
    for archivo in archivos:
        with open(archivo, "r", encoding="utf-8") as f:
            data_recuperada = json.load(f)
            
        paquete = PaqueteDatos(**data_recuperada["datos"])
        
        # Bloque de seguridad para datos clasificados
        if paquete.es_sensible:
            logging.warning(f"ALERTA: El archivo {archivo.name} contiene información SENSIBLE.")
            # getpass oculta lo que escribes en la terminal por seguridad
            intento_clave = getpass("🔒 Ingrese clave de autorización para desencriptar y procesar: ")
            
            if intento_clave != AUTH_KEY_ADMIN:
                logging.error("Clave incorrecta. Operación abortada para este archivo.\n")
                continue # Salta este archivo y sigue con el próximo
            logging.info("✅ Autorización concedida.")
        
        # Simulamos que el sistema volvió a tener internet y procesa el dato
        logging.info(f"Re-procesando operación {paquete.id_operacion} con éxito.")
        archivo.unlink() # Elimina el archivo de backup una vez procesado con éxito
        logging.info(f"Archivo {archivo.name} eliminado del almacenamiento de contingencia.\n")


# ==========================================
# EJECUCIÓN DEL ENTORNO
# ==========================================
if __name__ == "__main__":
    print("\n" + "="*50)
    print("INICIANDO SISTEMA DE ALTA DISPONIBILIDAD")
    print("="*50 + "\n")
    
    # 1. El usuario define la clasificación de la información
    dato_comun = PaqueteDatos(
        id_operacion="OP-001", 
        contenido="Consulta de horarios de apertura.", 
        es_sensible=False
    )
    
    dato_critico = PaqueteDatos(
        id_operacion="OP-002", 
        contenido="Actualización de CUIT y cuenta bancaria del proveedor.", 
        es_sensible=True
    )

    # 2. Intentamos procesar. Como la API es falsa, fallarán y se guardarán.
    for dato in [dato_comun, dato_critico]:
        try:
            procesar_con_ia(dato)
        except Exception as e:
            activar_fail_safe(dato, e)
            
    print("\n" + "="*50)
    print("SIMULANDO RESTABLECIMIENTO DEL SISTEMA (RECUPERACIÓN)")
    print("="*50 + "\n")
    
    # 3. Disparamos la recuperación manual
    recuperar_contingencias()