#!/bin/bash

echo "=== Firmware Notifier (Bash) ==="

# Solicitar los datos al usuario
read -p "🔧 Ingresa el modelo (ej: S901U1): " model
read -p "🌐 Ingresa el CSC (ej: XAA): " csc
read -p "📦 Ingresa tu versión actual (ej: S901U1UES8EYC1): " current_version
read -p "📬 Ingresa tu Webhook de Discord: " webhook_url

# Construir la URL con los datos del modelo y CSC
url="https://samfw.com/firmware/SM-${model}/${csc}"
check_interval=1800  # 30 minutos

# Iniciar el bucle de verificación de versiones
while true; do
    echo "🔎 Verificando actualizaciones $(date '+%Y-%m-%d %H:%M:%S')..."
    
    # Obtener la última versión desde el sitio
    latest_version=$(curl -s -A "Mozilla/5.0" "$url" | grep -oP '(?<=<td class="text-nowrap">).*?(?=</td>)' | head -n 1)
    
    if [ -z "$latest_version" ]; then
        echo "⚠️ No se pudo obtener la última versión."
    elif [ "$latest_version" != "$current_version" ]; then
        echo "✅ ¡Nueva versión detectada! ($latest_version) Enviando notificación..."
        curl -H "Content-Type: application/json" \
            -X POST \
            -d "{\"content\": \"🚨 **Nueva actualización disponible!** 🚨\n📱 **Modelo:** SM-${model}/${csc}\n🆕 **Versión:** ${latest_version}\n🔗 ${url}\", \"username\": \"One UI Notifier\"}" \
            "$webhook_url"
        break
    else
        echo "⏳ No hay nuevas versiones (actual: $current_version)"
    fi

    # Esperar el intervalo antes de la siguiente comprobación
    sleep $check_interval
done
