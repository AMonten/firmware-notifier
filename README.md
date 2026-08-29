# 📱 Firmware Notifier

![Powered by Python](https://img.shields.io/badge/Powered%20by-Python-blue?logo=python&logoColor=white)
![Version](https://img.shields.io/badge/Version-1.0.0-brightgreen)

Un script que verifica automáticamente nuevas versiones de firmware para dispositivos Samsung y notifica mediante un webhook de Discord.

## 🚀 Instalación

```bash
git clone https://github.com/AMonten/firmware-notifier.git
cd firmware-notifier
pip install -r requirements.txt
```
## ⚙️ Uso

```bash
python firmware_notifier.py
```
También disponible una versión ligera para Texmux:

```bash
 curl -O https://raw.githubusercontent.com/AMonten/firmware-notifier/master/firmware_notifier.sh
chmod +x firmware_notifier.sh
./firmware_notifier.sh
```

## 📋 Requisitos
Python 3.7+
bash (para versión ligera)
curl, grep, awk (para versión bash)

## 🔧 Variables de entorno (`main.py` / Render)

| Variable | Default | Descripción |
|---|---|---|
| `MODEL` | `S901U1` | Modelo del dispositivo (sin el prefijo `SM-`). Ignorada si `DEVICES_JSON` está seteada |
| `CSC` | `XAA` | Código CSC/región. Ignorada si `DEVICES_JSON` está seteada |
| `WEBHOOK_URL` | — | Webhook de Discord (obligatorio) |
| `CURRENT_VERSION` | `S901U1UES8EYC1` | Versión de referencia inicial. Ignorada si `DEVICES_JSON` está seteada |
| `DEVICES_JSON` | — | Lista JSON para monitorear **más de un dispositivo** a la vez, reemplaza a `MODEL`/`CSC`/`CURRENT_VERSION`. Ej.: `[{"model":"S901U1","csc":"XAA","current_version":"S901U1UES8EYC1"},{"model":"S918U1","csc":"XAA","current_version":"S918U1UES1AYE1"}]` |
| `FAILURE_ALERT_THRESHOLD` | `5` | Chequeos fallidos seguidos (por dispositivo) antes de mandar una alerta de Discord avisando que el scraper puede estar roto (cambio en samfw.com, bloqueo, etc.) |
| `PORT` | `10000` | Puerto donde escucha el dashboard |
| `STATE_DIR` | `/tmp` | Carpeta donde se persiste `firmware_state.json` entre reinicios. En Render, `/tmp` es efímero — si montás un disco persistente, apuntá `STATE_DIR` a ese path para no perder la última versión detectada en cada redeploy/reinicio |

## 🖥️ Dashboard

`main.py` expone un dashboard en `/` con el estado de cada dispositivo, los últimos logs, y un botón **"🔄 Chequear ahora"** que dispara un chequeo inmediato sin esperar al intervalo de 30 minutos (`POST /check`).

## ⏰ Mantener el servicio despierto en Render (plan free)

Los "Web Services" gratis de Render se duermen tras ~15 minutos sin recibir tráfico HTTP. Como el chequeo de firmware corre en un thread *dentro* del mismo proceso del dashboard, si nadie visita `/` el proceso entero se duerme y el chequeo se detiene con él — no hay forma de arreglar esto desde el código, es una limitación de la infraestructura.

Solución: configurar un pinger externo gratuito (por ejemplo [UptimeRobot](https://uptimerobot.com) o [cron-job.org](https://cron-job.org)) que le pegue a la URL pública del dashboard (`https://tu-app.onrender.com/`) cada 10-14 minutos. Esto mantiene el proceso despierto y, de paso, sirve como monitoreo de uptime.

## 📜 Licencia
Este proyecto está bajo la Licencia MIT.
