#!/usr/bin/env bash
# Exit on error
set -o errexit

# Instalar dependencias
pip install -r requirements.txt

# Servidor de producción (gunicorn + worker gevent, ambos en requirements.txt).
# Un solo worker: el thread de verificación de firmware corre a nivel de
# módulo (ver main.py), así que más de un worker lanzaría más de un loop de
# chequeo en paralelo y notificaciones duplicadas.
exec gunicorn --worker-class gevent --workers 1 --bind "0.0.0.0:${PORT:-10000}" main:app
