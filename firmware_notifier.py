import time

from firmware_scraper import build_url, get_latest_version, send_discord_notification, format_update_message

# Configuración fija
CHECK_INTERVAL = 1800  # 30 minutos
LOG_FILE = "firmware_check.log"


def log_error(message):
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    log_entry = f"[{timestamp}] {message}\n"
    with open(LOG_FILE, 'a') as f:
        f.write(log_entry)


def main():
    print("=== Firmware Notifier ===")
    model = input("🔧 Ingresa el modelo (ej: S901U1): ").strip().upper()
    csc = input("🌐 Ingresa el CSC (ej: XAA): ").strip().upper()
    current_version = input("📦 Ingresa tu versión actual (ej: S901U1UES8EYC1): ").strip().upper()
    webhook_url = input("📬 Ingresa tu Webhook de Discord: ").strip()

    url = build_url(model, csc)
    print(f"\n📡 URL generada: {url}")

    while True:
        try:
            print(f"\n🔎 Verificando actualizaciones {time.strftime('%Y-%m-%d %H:%M:%S')}...")
            latest_version, error = get_latest_version(model, csc)

            if error:
                print(f"⚠️ No se pudo obtener la última versión: {error}")
                log_error(f"Error al obtener la versión: {error}")
            elif latest_version != current_version:
                print(f"✅ ¡Nueva versión detectada! ({latest_version}) Enviando notificación...")
                message = format_update_message(model, csc, latest_version, url)
                ok, send_error = send_discord_notification(webhook_url, message)
                if not ok:
                    log_error(f"Error enviando notificación: {send_error}")
                break  # Termina si detecta nueva versión
            else:
                print(f"⏳ No hay nuevas versiones (actual: {current_version})")

        except Exception as e:
            log_error(f"Error en el loop principal: {str(e)}")

        time.sleep(CHECK_INTERVAL)


if __name__ == "__main__":
    main()
