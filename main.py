import os
import threading
import time
import random
import requests
from bs4 import BeautifulSoup
from flask import Flask, render_template_string

# Inicializar Flask
app = Flask(__name__)

# Configuración fija
CHECK_INTERVAL = 780  # 13 minutos
LOG_FILE = "firmware_check.log"

# Lista de User-Agents
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_3) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.1 Safari/605.1.15",
    "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:124.0) Gecko/20100101 Firefox/124.0",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_4 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (Linux; Android 13; SM-S901U1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.6367.93 Mobile Safari/537.36",
]

# HTML template con CSS integrado
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Firmware Notifier Status</title>
    <style>
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            line-height: 1.6;
            margin: 0;
            padding: 20px;
            background-color: #f5f5f5;
            color: #333;
        }
        .container {
            max-width: 1000px;
            margin: 0 auto;
            background: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        h1 {
            color: #2c3e50;
            border-bottom: 2px solid #3498db;
            padding-bottom: 10px;
        }
        .status-card {
            background: #f8f9fa;
            border-left: 4px solid #3498db;
            padding: 15px;
            margin-bottom: 20px;
            border-radius: 4px;
        }
        .log-container {
            background: #2c3e50;
            color: #ecf0f1;
            padding: 15px;
            border-radius: 4px;
            font-family: monospace;
            white-space: pre-wrap;
            overflow-x: auto;
            max-height: 500px;
            overflow-y: auto;
        }
        .log-entry {
            margin-bottom: 5px;
        }
        .success { color: #2ecc71; }
        .error { color: #e74c3c; }
        .warning { color: #f39c12; }
        .info { color: #3498db; }
    </style>
</head>
<body>
    <div class="container">
        <h1>Firmware Notifier Status</h1>
        
        <div class="status-card">
            <h2>Service Information</h2>
            <p><strong>Status:</strong> <span class="success">✔ Running</span></p>
            <p><strong>Model:</strong> SM-{{ model }}/{{ csc }}</p>
            <p><strong>Current Version:</strong> {{ current_version }}</p>
            <p><strong>Last Check:</strong> {{ last_check }}</p>
            <p><strong>Next Check:</strong> {{ next_check }}</p>
            <p><strong>Check Interval:</strong> {{ check_interval }} minutes</p>
        </div>
        
        <h2>Recent Logs</h2>
        <div class="log-container">
            {% for log in logs[-50:] %}
                <div class="log-entry 
                    {% if '✅' in log or '✔' in log %}success
                    {% elif '❌' in log or 'Error' in log %}error
                    {% elif '⚠️' in log or 'Warning' in log %}warning
                    {% else %}info{% endif %}">
                    {{ log }}
                </div>
            {% endfor %}
        </div>
    </div>
</body>
</html>
"""

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
    log_entry = f"[{timestamp}] {message}"
    print(log_entry)  # También imprimir en consola
    with open(LOG_FILE, 'a') as f:
        f.write(log_entry + "\n")

def get_latest_version(url):
    try:
        response = requests.get(url, headers=get_headers(), timeout=15)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        table = soup.find('table', {'id': 'firmwares'})
        
        if not table:
            log_error("⚠️ No se encontró la tabla de firmwares")
            return None
            
        first_row = table.tbody.find('tr')
        if not first_row:
            log_error("⚠️ No hay filas en la tabla")
            return None
            
        version_td = first_row.find_all('td')[2]
        version_link = version_td.find('a')
        
        if version_link:
            return version_link.text.strip()
        return None
        
    except Exception as e:
        log_error(f"❌ Error al obtener la versión: {str(e)}")
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
        log_error(f"❌ Error al enviar notificación: {str(e)}")

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
    log_error("📡 URL generada: " + url)
    
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
            log_error(f"❌ Error en el loop principal: {str(e)}")
        
        time.sleep(CHECK_INTERVAL)

def read_logs():
    try:
        with open(LOG_FILE, 'r') as f:
            return f.read().splitlines()
    except FileNotFoundError:
        return ["No hay registros disponibles."]

@app.route('/')
def home():
    return render_template_string(HTML_TEMPLATE,
        model=os.environ.get("MODEL", "S901U1"),
        csc=os.environ.get("CSC", "XAA"),
        current_version=os.environ.get("CURRENT_VERSION", "S901U1UES8EYC1"),
        last_check=time.strftime("%Y-%m-%d %H:%M:%S"),
        next_check=time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(time.time() + CHECK_INTERVAL)),
        check_interval=CHECK_INTERVAL//60,
        logs=read_logs()
    )

# Lanzar la app y el thread de verificación
if __name__ == '__main__':
    # Iniciar el thread de verificación de firmware
    threading.Thread(target=firmware_check_loop, daemon=True).start()
    
    # Iniciar Flask
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
