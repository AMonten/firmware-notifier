import requests
from bs4 import BeautifulSoup
import time
import os
import random

# Configuración
WEBHOOK_URL = "https://discord.com/api/webhooks/1367514282710925353/7yaHBlboti4QDb7YhfdmBIPk2F5z8ZLzxt_0pC2eZrncrlHHKr3XKLTz2sOrDDT7Qek2"
CURRENT_VERSION = "S901U1UES8EYC2"
URL = "https://samfw.com/firmware/SM-S901U1/XAA"
CHECK_INTERVAL = 1800  # 30 minutos en segundos
LOG_FILE = "firmware_check.log"

# Lista de User-Agents realistas
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_3) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.1 Safari/605.1.15",
    "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:124.0) Gecko/20100101 Firefox/124.0",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_4 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (Linux; Android 13; SM-S901U1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.6367.93 Mobile Safari/537.36",
]

def get_headers():
    return {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "DNT": "1",  # Do Not Track enabled
    }

def get_latest_version():
    try:
        response = requests.get(URL, headers=get_headers(), timeout=15)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        table = soup.find('table', {'id': 'firmwares'})
        
        if not table:
            log_error("No se encontró la tabla de firmwares")
            return None
            
        first_row = table.tbody.find('tr')
        if not first_row:
            log_error("No hay filas en la tabla")
            return None
            
        version_td = first_row.find_all('td')[2]  # Tercera columna
        version_link = version_td.find('a')
        
        if version_link:
            return version_link.text.strip()
            
        return None
        
    except Exception as e:
        log_error(f"Error al obtener la versión: {str(e)}")
        return None

def send_notification(message):
    data = {
        "content": f"🚨 **Nueva actualización disponible!** 🚨\n{message}",
        "username": "One UI 7 Notifier"
    }
    try:
        response = requests.post(WEBHOOK_URL, json=data, timeout=10)
        response.raise_for_status()
    except Exception as e:
        log_error(f"Error enviando notificación: {str(e)}")

def log_error(message):
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    log_entry = f"[{timestamp}] {message}\n"
    with open(LOG_FILE, 'a') as f:
        f.write(log_entry)

def check_version():
    latest_version = get_latest_version()
    
    if not latest_version:
        return False
        
    if latest_version != CURRENT_VERSION:
        send_notification(
            f"📱 **Modelo:** SM-S901U1/XAA\n"
            f"🆕 **Versión:** {latest_version}\n"
            f"🔗 {URL}"
        )
        return True
        
    return False

if __name__ == "__main__":
    print("Iniciando monitor de actualizaciones...")
    while True:
        try:
            print(f"Verificando {time.strftime('%Y-%m-%d %H:%M:%S')}...")
            if check_version():
                print("¡Nueva versión detectada! Notificación enviada.")
                break  # Detener si se encuentra actualización
        except Exception as e:
            log_error(f"Error en el loop principal: {str(e)}")
        
        time.sleep(CHECK_INTERVAL)
