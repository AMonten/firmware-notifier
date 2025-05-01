#!/usr/bin/env bash
# Exit on error
set -o errexit

# Instalar dependencias
pip install -r requirements.txt

# Iniciar la aplicación en segundo plano
nohup python main.py > app.log 2>&1 &

# Opcional: mantener el proceso activo para que Render no lo termine
# (esto depende de cómo Render maneje los build commands)
tail -f /dev/null
