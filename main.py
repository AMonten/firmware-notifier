import os
import threading
import time
import json

from flask import Flask, render_template_string, redirect, url_for, request

from firmware_scraper import build_url, get_latest_version, send_discord_notification, format_update_message

# Inicializar Flask
app = Flask(__name__)

# Configuración fija
CHECK_INTERVAL = 1800  # 30 minutos (en segundos)
FAILURE_ALERT_THRESHOLD = int(os.environ.get("FAILURE_ALERT_THRESHOLD", 5))
TEMP_DIR = os.getenv('TEMP', '/tmp')
LOG_FILE = os.path.join(TEMP_DIR, "firmware_check.log")
# STATE_DIR es configurable porque en Render el filesystem por defecto (/tmp)
# es efímero: se pierde en cada reinicio/redeploy, y con él la última versión
# detectada — al reiniciar, cada dispositivo vuelve a su seed_version y puede
# disparar una notificación repetida de una versión que ya se avisó.
# Si se monta un disco persistente en Render, apuntar STATE_DIR a ese path
# para que el estado sobreviva a los reinicios.
STATE_DIR = os.getenv('STATE_DIR', TEMP_DIR)
STATE_FILE = os.path.join(STATE_DIR, "firmware_state.json")

# Estado persistente (protegido por CHECK_LOCK durante escrituras/lecturas de un chequeo)
LAST_CHECK = None
NEXT_CHECK = None
DEVICE_STATE = {}  # key "MODEL/CSC" -> {current_version, consecutive_failures, failure_alerted}
CHECK_LOCK = threading.Lock()

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
        .status-card.warning { border-left-color: #f39c12; }
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
        .log-entry { margin-bottom: 5px; }
        .success { color: #2ecc71; }
        .error { color: #e74c3c; }
        .warning { color: #f39c12; }
        .info { color: #3498db; }
        button {
            background: #3498db;
            color: white;
            border: none;
            padding: 10px 18px;
            border-radius: 4px;
            cursor: pointer;
            font-size: 14px;
        }
        button:hover { background: #2980b9; }
    </style>
</head>
<body>
    <div class="container">
        <h1>Firmware Notifier Status</h1>

        <div class="status-card">
            <h2>Service Information</h2>
            <p><strong>Status:</strong> <span class="success">✔ Running</span></p>
            <p><strong>Last Check:</strong> {{ last_check }}</p>
            <p><strong>Next Check:</strong> {{ next_check }}</p>
            <p><strong>Check Interval:</strong> {{ check_interval }} minutes</p>
            {% if msg %}<p><strong>ℹ {{ msg }}</strong></p>{% endif %}
            <form method="POST" action="/check">
                <button type="submit">🔄 Chequear ahora</button>
            </form>
        </div>

        <h2>Dispositivos monitoreados</h2>
        {% for dev in devices %}
        <div class="status-card {% if dev.consecutive_failures > 0 %}warning{% endif %}">
            <p><strong>Modelo:</strong> SM-{{ dev.model }}/{{ dev.csc }}</p>
            <p><strong>Versión actual conocida:</strong> {{ dev.current_version }}</p>
            {% if dev.consecutive_failures > 0 %}
            <p><strong>⚠ Fallos seguidos:</strong> {{ dev.consecutive_failures }}</p>
            {% endif %}
        </div>
        {% endfor %}

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


## FUNCIÓN: load_devices_config()
# Propósito: Leer DEVICES_JSON (lista de {model,csc,current_version}) si está
# configurado; si no, caer al comportamiento original de un solo dispositivo
# vía MODEL/CSC/CURRENT_VERSION, para no romper despliegues existentes.
def load_devices_config():
    raw = os.environ.get("DEVICES_JSON")
    if raw:
        try:
            raw_devices = json.loads(raw)
            parsed = [
                {
                    "model": str(d["model"]).strip().upper(),
                    "csc": str(d["csc"]).strip().upper(),
                    "seed_version": str(d.get("current_version", "")).strip().upper(),
                }
                for d in raw_devices
            ]
            if parsed:
                return parsed
        except Exception as e:
            print(f"⚠️ DEVICES_JSON inválido ({e}), usando MODEL/CSC/CURRENT_VERSION.")

    return [{
        "model": os.environ.get("MODEL", "S921U").strip().upper(),
        "csc": os.environ.get("CSC", "TMB").strip().upper(),
        "seed_version": os.environ.get("CURRENT_VERSION", "S921USQS6DZG1").strip().upper(),
    }]


DEVICES = load_devices_config()


def device_key(device):
    return f"{device['model']}/{device['csc']}"


def log_error(message):
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    log_entry = f"[{timestamp}] {message}"
    print(log_entry)
    with open(LOG_FILE, 'a') as f:
        f.write(log_entry + "\n")


## FUNCIÓN: save_state() / load_state()
# Propósito: Persistir/recuperar last_check/next_check y el estado por dispositivo.
def save_state():
    state = {
        'last_check': LAST_CHECK,
        'next_check': NEXT_CHECK,
        'devices': DEVICE_STATE,
    }
    with open(STATE_FILE, 'w') as f:
        json.dump(state, f)


def load_state():
    global LAST_CHECK, NEXT_CHECK, DEVICE_STATE

    saved_devices = None
    try:
        with open(STATE_FILE, 'r') as f:
            state = json.load(f)
        LAST_CHECK = state.get('last_check')
        NEXT_CHECK = state.get('next_check')
        saved_devices = state.get('devices')
        if saved_devices is None and 'current_version' in state and len(DEVICES) == 1:
            # Formato de antes del soporte multi-dispositivo: migrarlo.
            saved_devices = {
                device_key(DEVICES[0]): {
                    "current_version": state.get("current_version"),
                    "consecutive_failures": 0,
                    "failure_alerted": False,
                }
            }
    except (FileNotFoundError, json.JSONDecodeError):
        pass

    saved_devices = saved_devices or {}
    for device in DEVICES:
        key = device_key(device)
        DEVICE_STATE[key] = saved_devices.get(key, {
            "current_version": device["seed_version"],
            "consecutive_failures": 0,
            "failure_alerted": False,
        })


## FUNCIÓN: check_device()
# Propósito: Chequear un dispositivo, notificar si hay versión nueva, y
# alertar por Discord si el chequeo lleva FAILURE_ALERT_THRESHOLD fallos
# seguidos (antes esos fallos sólo quedaban en un log que nadie mira).
def check_device(device, webhook_url):
    key = device_key(device)
    url = build_url(device["model"], device["csc"])  # link humano de referencia en la notificación
    dstate = DEVICE_STATE[key]

    latest_version, error = get_latest_version(device["model"], device["csc"])

    if error:
        dstate["consecutive_failures"] += 1
        log_error(f"⚠️ [{key}] Error al obtener la versión: {error} (fallos seguidos: {dstate['consecutive_failures']})")
        if dstate["consecutive_failures"] >= FAILURE_ALERT_THRESHOLD and not dstate["failure_alerted"]:
            msg = (
                f"⚠️ **Firmware Notifier**: {dstate['consecutive_failures']} chequeos seguidos fallando "
                f"para SM-{device['model']}/{device['csc']}.\nÚltimo error: {error}\n{url}"
            )
            send_discord_notification(webhook_url, msg)
            dstate["failure_alerted"] = True
        return

    if dstate["consecutive_failures"] > 0:
        log_error(f"✅ [{key}] Se recuperó el chequeo tras {dstate['consecutive_failures']} fallo(s) seguido(s).")
    dstate["consecutive_failures"] = 0
    dstate["failure_alerted"] = False

    if latest_version != dstate["current_version"]:
        log_error(f"✅ [{key}] ¡Nueva versión detectada! ({latest_version}) Enviando notificación...")
        message = format_update_message(device["model"], device["csc"], latest_version, url)
        ok, send_error = send_discord_notification(webhook_url, message)
        if ok:
            log_error("✅ Notificación enviada correctamente.")
        else:
            log_error(f"❌ Error al enviar notificación: {send_error}")
        dstate["current_version"] = latest_version
    else:
        log_error(f"⏳ [{key}] No hay nuevas versiones (actual: {dstate['current_version']})")


## FUNCIÓN: run_all_checks()
# Propósito: Correr un pase de chequeo sobre todos los dispositivos. La usan
# tanto el loop automático como el botón "Chequear ahora" del dashboard.
def run_all_checks():
    global LAST_CHECK, NEXT_CHECK

    webhook_url = os.environ.get("WEBHOOK_URL")
    if not webhook_url:
        log_error("❌ WEBHOOK_URL no está configurado.")
        return

    LAST_CHECK = time.strftime("%Y-%m-%d %H:%M:%S")
    NEXT_CHECK = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(time.time() + CHECK_INTERVAL))
    log_error(f"🔎 Verificando actualizaciones {LAST_CHECK}...")

    for device in DEVICES:
        check_device(device, webhook_url)

    save_state()


def firmware_check_loop():
    log_error("=== Firmware Notifier ===")
    for device in DEVICES:
        log_error(f"📡 Monitoring: SM-{device['model']}/{device['csc']} (seed: {device['seed_version']})")

    while True:
        try:
            if CHECK_LOCK.acquire(blocking=False):
                try:
                    run_all_checks()
                finally:
                    CHECK_LOCK.release()
            else:
                log_error("⏳ Chequeo manual en curso, se omite este ciclo automático.")
        except Exception as e:
            log_error(f"❌ Error en el loop principal: {str(e)}")

        time.sleep(CHECK_INTERVAL)


def read_logs():
    try:
        with open(LOG_FILE, 'r') as f:
            return f.read().splitlines()
    except FileNotFoundError:
        return ["No hay registros disponibles."]


# Rutas Flask
@app.route('/')
def home():
    devices_view = [
        {
            "model": device["model"],
            "csc": device["csc"],
            "current_version": DEVICE_STATE.get(device_key(device), {}).get("current_version", "?"),
            "consecutive_failures": DEVICE_STATE.get(device_key(device), {}).get("consecutive_failures", 0),
        }
        for device in DEVICES
    ]
    return render_template_string(HTML_TEMPLATE,
        devices=devices_view,
        last_check=LAST_CHECK or "No se ha verificado aún",
        next_check=NEXT_CHECK or "No programado",
        check_interval=CHECK_INTERVAL // 60,
        logs=read_logs(),
        msg=request.args.get("msg"),
    )


@app.route('/check', methods=['POST'])
def manual_check():
    if CHECK_LOCK.acquire(blocking=False):
        try:
            run_all_checks()
            msg = "Chequeo manual completado."
        finally:
            CHECK_LOCK.release()
    else:
        msg = "Ya hay un chequeo en curso — esperá a que termine."
    return redirect(url_for('home', msg=msg))


# Inicialización: corre tanto si el módulo se ejecuta directo (python main.py)
# como si lo importa un servidor WSGI (gunicorn main:app) — con gunicorn nunca
# se llega al bloque __main__, así que el thread de verificación tiene que
# arrancar a nivel de módulo para no quedar sin correr.
load_state()
threading.Thread(target=firmware_check_loop, daemon=True).start()

if __name__ == '__main__':
    # Servidor de desarrollo de Flask, sólo para correr local (python main.py).
    # En producción (Render) se usa gunicorn vía build_and_run.sh.
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
