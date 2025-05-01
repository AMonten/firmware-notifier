import os
import threading
import time
import random
import requests
from bs4 import BeautifulSoup
from flask import Flask

# Inicializar Flask
app = Flask(__name__)

# Configuración fija
CHECK_INTERVAL = 1800  # 30 minutos
LOG_FILE = "firmware_check.log"

# Lista de User-Agents
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
        "DNT": "1",
    }

def log_error(message):
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    log_entry = f"[{timestamp}] {message}\n"
    with open(LOG_FILE, 'a') as f:
        f.write(log_entry)

def get_latest_version(url):
    try:
        response = requests.get(url, headers=get_headers(), timeout=15)
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
            
        version_td = first_row.find_all('td')[2]
        version_link = version_td.find('a')
        
        if version_link:
            return version_link.text.strip()
        return None
        
    except Exception as e:
        log_error(f"Error al obtener la versión: {str(e)}")
        return None

def send_notification(webhook_url, model, csc, latest_version, url):
    data = {
        "content": (
            f"🚨 **Nueva actualización disponible!** 🚨\n"
            f"📱 **Modelo:** SM-{model}/{csc}\n"
            f"🆕 **Versión:** {latest_version}\n"
            f"🌐 **Descargar:** {url}"
        )
    }
    try:
        response = requests.post(webhook_url, json=data, timeout=10)
        response.raise_for_status()
        log_error("✅ Notificación enviada correctamente.")
    except Exception as e:
        log_error(f"Error al enviar notificación: {str(e)}")

def firmware_check_loop():
    print("=== Firmware Notifier ===")
    model = os.environ.get("MODEL", "S901U1")
    csc = os.environ.get("CSC", "XAA")
    current_version = os.environ.get("CURRENT_VERSION", "S901U1UES8EYC1")
    webhook_url = os.environ.get("WEBHOOK_URL")

    if not webhook_url:
        log_error("❌ WEBHOOK_URL no está configurado.")
        return

    url = f"https://samfw.com/firmware/SM-{model}/{csc}"
    log_error(f"📡 URL generada: {url}")
    
    while True:
        try:
            log_error(f"🔎 Verificando actualizaciones {time.strftime('%Y-%m-%d %H:%M:%S')}...")
            latest_version = get_latest_version(url)
            
            if not latest_version:
                log_error("⚠️ No se pudo obtener la última versión.")
            elif latest_version != current_version:
                log_error(f"✅ ¡Nueva versión detectada! ({latest_version}) Enviando notificación...")
                send_notification(webhook_url, model, csc, latest_version, url)
                current_version = latest_version  # Actualiza la versión actual para futuras comparaciones
            else:
                log_error(f"⏳ No hay nuevas versiones (actual: {current_version})")
                
        except Exception as e:
            log_error(f"Error en el loop principal: {str(e)}")
        
        time.sleep(CHECK_INTERVAL)

# Ruta simple para verificar que el servicio está funcionando
@app.route('/')
def home():
    return "Firmware Notifier funcionando correctamente."

# Lanzar la app y el thread de verificación
if __name__ == '__main__':
    # Iniciar el thread de verificación de firmware
    threading.Thread(target=firmware_check_loop, daemon=True).start()
    
    # Configuración del puerto
    port = int(os.environ.get("PORT", 10000))
    
    # Iniciar Flask con configuración para producción
    app.run(host='0.0.0.0', port=port, threaded=True)
