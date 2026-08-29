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
| `MODEL` | `S901U1` | Modelo del dispositivo (sin el prefijo `SM-`) |
| `CSC` | `XAA` | Código CSC/región |
| `WEBHOOK_URL` | — | Webhook de Discord (obligatorio) |
| `CURRENT_VERSION` | `S901U1UES8EYC1` | Versión de referencia inicial |
| `PORT` | `10000` | Puerto donde escucha el dashboard |
| `STATE_DIR` | `/tmp` | Carpeta donde se persiste `firmware_state.json` entre reinicios. En Render, `/tmp` es efímero — si montás un disco persistente, apuntá `STATE_DIR` a ese path para no perder la última versión detectada en cada redeploy/reinicio |

## 📜 Licencia
Este proyecto está bajo la Licencia MIT.
