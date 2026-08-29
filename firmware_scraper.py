"""
Lógica compartida de scraping/notificación entre main.py (servicio Flask/Render)
y firmware_notifier.py (CLI standalone). Antes vivía duplicada letra por letra
en los dos archivos — si samfw.com cambia el HTML, ahora sólo hay que tocar
un lugar.
"""

import random
import requests
from bs4 import BeautifulSoup

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


def build_url(model, csc):
    return f"https://samfw.com/firmware/SM-{model}/{csc}"


## FUNCIÓN: get_latest_version()
# Propósito: Scrapear samfw.com y devolver la última versión publicada.
# Devuelve (version, error): error es None si todo salió bien, o un mensaje
# legible si falló (para que cada caller decida cómo loguearlo/notificarlo).
def get_latest_version(url, timeout=15):
    try:
        response = requests.get(url, headers=get_headers(), timeout=timeout)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")
        table = soup.find("table", {"id": "firmwares"})
        if not table:
            return None, "No se encontró la tabla de firmwares"

        first_row = table.tbody.find("tr")
        if not first_row:
            return None, "No hay filas en la tabla"

        version_td = first_row.find_all("td")[2]
        version_link = version_td.find("a")
        if not version_link:
            return None, "No se encontró el link de versión"

        return version_link.text.strip(), None

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
