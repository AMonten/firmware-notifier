#!/bin/bash

# Configuración
CHECK_INTERVAL=1800  # 30 minutos en segundos
USER_AGENT="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

# Colores para la salida
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Mostrar banner
echo -e "\n${BLUE}=== Firmware Notifier (Bash) ===${NC}\n"

# Función para validar entrada
validate_input() {
    if [[ -z "$1" ]]; then
        echo -e "${RED}Error: Este campo no puede estar vacío.${NC}"
        return 1
    fi
    return 0
}

# Solicitar los datos al usuario con validación
while true; do
    read -p "🔧 Ingresa el modelo (ej: S901U1): " model
    validate_input "$model" && break
done

while true; do
    read -p "🌐 Ingresa el CSC (ej: XAA): " csc
    validate_input "$csc" && break
done

while true; do
    read -p "📦 Ingresa tu versión actual (ej: S901U1UES8EYC1): " current_version
    validate_input "$current_version" && break
done

while true; do
    read -p "📬 Ingresa tu Webhook de Discord: " webhook_url
    if [[ -z "$webhook_url" ]]; then
        echo -e "${YELLOW}Advertencia: Sin webhook, las notificaciones no se enviarán.${NC}"
        read -p "¿Continuar sin webhook? (s/n): " choice
        [[ "$choice" =~ ^[sS] ]] && break
    else
        # Validación básica de URL
        if [[ "$webhook_url" =~ ^https://discord\.com/api/webhooks/ ]]; then
            break
        else
            echo -e "${RED}Error: La URL del webhook no parece válida.${NC}"
        fi
    fi
done

# Construir URL
url="https://samfw.com/firmware/SM-${model}/${csc}"
echo -e "\n${BLUE}ℹ URL de verificación: $url${NC}"

# Función para enviar notificación a Discord
send_notification() {
    if [[ -n "$webhook_url" ]]; then
        local message="🚨 **Nueva actualización disponible!** 🚨\n📱 **Modelo:** SM-${model}/${csc}\n🆕 **Versión:** ${latest_version}\n🔗 ${url}"
        
        curl -sS -H "Content-Type: application/json" \
             -X POST \
             -d "{\"content\": \"$message\", \"username\": \"One UI Notifier\"}" \
             "$webhook_url" > /dev/null
        
        if [ $? -eq 0 ]; then
            echo -e "${GREEN}✓ Notificación enviada a Discord${NC}"
        else
            echo -e "${RED}✗ Error al enviar notificación a Discord${NC}"
        fi
    fi
}

# Bucle principal de verificación
echo -e "\n${YELLOW}🔍 Iniciando verificación de actualizaciones...${NC}"
echo -e "${BLUE}ℹ Presiona Ctrl+C para detener el script.${NC}\n"

while true; do
    current_time=$(date '+%Y-%m-%d %H:%M:%S')
    echo -e "\n${BLUE}=== Verificación iniciada: $current_time ===${NC}"
    
    # Obtener la última versión
    echo -e "${YELLOW}⏳ Obteniendo información del servidor...${NC}"
    page_content=$(curl -s -A "$USER_AGENT" "$url")
    
    if [[ -z "$page_content" ]]; then
        echo -e "${RED}✗ Error: No se pudo obtener datos del servidor${NC}"
        sleep 60  # Esperar 1 minuto antes de reintentar
        continue
    fi
    
    latest_version=$(echo "$page_content" | grep -oP '(?<=<td class="text-nowrap">).*?(?=</td>)' | head -n 1)
    
    if [[ -z "$latest_version" ]]; then
        echo -e "${RED}✗ No se pudo extraer la versión de la página${NC}"
        echo -e "${YELLOW}ℹ Puede que el modelo o CSC sean incorrectos, o el sitio haya cambiado su estructura.${NC}"
    else
        echo -e "${BLUE}ℹ Versión actual: $current_version${NC}"
        echo -e "${BLUE}ℹ Última versión disponible: $latest_version${NC}"
        
        if [[ "$latest_version" != "$current_version" ]]; then
            echo -e "${GREEN}🎉 ¡Nueva versión detectada!${NC}"
            send_notification
            break
        else
            echo -e "${GREEN}✓ Ya tienes la última versión${NC}"
        fi
    fi
    
    # Esperar para la próxima verificación
    echo -e "\n${YELLOW}⏳ Esperando $((CHECK_INTERVAL/60)) minutos para la próxima verificación...${NC}"
    sleep $CHECK_INTERVAL
done
