"""
config.py - Configuración segura del bot
Carga las variables de entorno desde el archivo .env
"""

import os
from dotenv import load_dotenv

# Cargar variables del archivo .env
load_dotenv()

# Obtener configuraciones
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
CHAT_ID = os.getenv('CHAT_ID')
SOPORTE_USERNAME = os.getenv('SOPORTE_USERNAME', 'Tekvoblack')

# TU ID DE USUARIO (Para reconocerte como admin)
ADMIN_ID = 6913856812

# Validar que existan las configuraciones requeridas
if not TELEGRAM_TOKEN:
    raise ValueError("⚠️ No se encontró TELEGRAM_TOKEN en el archivo .env")

if not CHAT_ID:
    raise ValueError("⚠️ No se encontró CHAT_ID en el archivo .env")

# Función para obtener configuración
def get_config():
    return {
        'token': TELEGRAM_TOKEN,
        'chat_id': CHAT_ID,
        'soporte': SOPORTE_USERNAME,
        'admin_id': ADMIN_ID
    }
