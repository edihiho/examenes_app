import json
import os
import logging

CONFIG_FILE = "app_settings.json"

# Configuración básica del logger (puedes configurar a nivel de aplicación)
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

def load_app_config():
    """
    Carga la configuración desde CONFIG_FILE (JSON).
    Retorna un diccionario con la configuración o {} si el archivo no existe.
    """
    if not os.path.exists(CONFIG_FILE):
        return {}
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data
    except Exception as e:
        logger.error(f"Error al cargar la configuración: {e}")
        return {}

def save_app_config(config_data):
    """
    Guarda el diccionario config_data en CONFIG_FILE en formato JSON.
    """
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(config_data, f, ensure_ascii=False, indent=4)
        logger.info(f"Configuración guardada en {CONFIG_FILE}")
    except Exception as e:
        logger.error(f"Error al guardar la configuración: {e}")
