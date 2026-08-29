"""
Lógica compartida de chequeo/notificación entre main.py (servicio Flask/Render)
y firmware_notifier.py (CLI standalone). Antes vivía duplicada letra por letra
en los dos archivos.

El chequeo de versión usa el servidor FUS de Samsung
(fota-cloud-dn.ospserver.net) — el mismo endpoint que consultan Kies/Smart
Switch/Frija/Odin para buscar actualizaciones — en vez de scrapear el HTML de
samfw.com. Se cambió el 2026-08-29 porque samfw.com empezó a exigir un
challenge JS de Cloudflare (no resoluble con requests/headers, hace falta un
browser real); el FUS es la fuente oficial y no tiene protección anti-bot.
samfw.com se sigue usando como link humano de referencia en la notificación
(un browser real sí puede resolver su challenge).
"""

import xml.etree.ElementTree as ET

import requests


def build_url(model, csc):
    """Página humana en samfw.com, sólo para el link de la notificación."""
    return f"https://samfw.com/firmware/SM-{model}/{csc}"


def build_check_url(model, csc):
    """Servidor FUS de Samsung usado por el chequeo automático de versión."""
    return f"https://fota-cloud-dn.ospserver.net/firmware/{csc}/SM-{model}/version.xml"


## FUNCIÓN: get_latest_version()
# Propósito: Consultar el FUS de Samsung y devolver la última versión publicada.
# Devuelve (version, error): error es None si todo salió bien, o un mensaje
# legible si falló (para que cada caller decida cómo loguearlo/notificarlo).
def get_latest_version(model, csc, timeout=15):
    url = build_check_url(model, csc)
    try:
        response = requests.get(url, timeout=timeout)
        response.raise_for_status()

        root = ET.fromstring(response.content)
        latest_el = root.find(".//latest")
        if latest_el is None or not (latest_el.text or "").strip():
            return None, "El XML de Samsung no trae <latest>"

        # Formato "PDA/CSC/PHONE" (ej. "S901U1UESAGZF3/S901U1OYMAGZF3/S901U1UESAGZF3").
        # Se usa el primer componente (PDA), que es el estilo de versión que
        # ya se venía usando en este proyecto (ej. S901U1UES8EYC1).
        return latest_el.text.strip().split("/")[0], None

    except ET.ParseError as e:
        return None, f"XML inválido: {e}"
    except Exception as e:
        return None, str(e)


## FUNCIÓN: format_update_message()
# Propósito: Armar el texto del mensaje de Discord para una nueva versión.
def format_update_message(model, csc, latest_version, url):
    return (
        f"🚨 **Nueva actualización disponible!** 🚨\n"
        f"📱 **Modelo:** SM-{model}/{csc}\n"
        f"🆕 **Versión:** {latest_version}\n"
        f"🔗 {url}"
    )


## FUNCIÓN: send_discord_notification()
# Propósito: Postear un mensaje a un webhook de Discord.
# Devuelve (ok, error) en vez de tirar la excepción, para que el caller decida
# cómo loguearlo.
def send_discord_notification(webhook_url, message, username="One UI Notifier", timeout=10):
    data = {"content": message, "username": username}
    try:
        response = requests.post(webhook_url, json=data, timeout=timeout)
        response.raise_for_status()
        return True, None
    except Exception as e:
        return False, str(e)
