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
curl -s https://raw.githubusercontent.com/AMonten/firmware-notifier/master/firmware_notifier.sh | bash
```

## 📋 Requisitos
Python 3.7+
bash (para versión ligera)
curl, grep, awk (para versión bash)

## 📜 Licencia
Este proyecto está bajo la Licencia MIT.
