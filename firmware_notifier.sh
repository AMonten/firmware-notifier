#!/bin/bash

# Configuración
CHECK_INTERVAL=1800  # 30 minutos en segundos
USER_AGENT="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

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

# Validar formato de versión
validate_version() {
    if [[ ! "$1" =~ ^S[0-9]{3}[A-Za-z0-9]+UES[0-9A-Z]+$ ]]; then
        echo -e "${RED}Error: Formato de versión inválido (ej: S901U1UES8EYC1)${NC}"
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
    validate_input "$current_version" && validate_version "$current_version" && break
done

while true; do
    read -p "📬 Ingresa tu Webhook de Discord: " webhook_url
    if [[ -z "$webhook_url" ]]; then
        echo -e "${YELLOW}Advertencia: Sin webhook, las notificaciones no se enviarán.${NC}"
        read -p "¿Continuar sin webhook? (s/n): " choice
        [[ "$choice" =~ ^[sS] ]] && break
    else
        if [[ "$webhook_url" =~ ^https://discord\.com/api/webhooks/ ]]; then
            break
        else
            echo -e "${RED}Error: URL de webhook inválida. Debe comenzar con: https://discord.com/api/webhooks/${NC}"
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
        
        response=$(curl -sw "%{http_code}" -H "Content-Type: application/json" \
            -X POST \
            -d "{\"content\": \"$message\", \"username\": \"One UI Notifier\"}" \
            "$webhook_url")
        
        status_code=${response: -3}
        
        if [ $status_code -ge 200 ] && [ $status_code -lt 300 ]; then
            echo -e "${GREEN}✓ Notificación enviada a Discord (Código: $status_code)${NC}"
        else
            echo -e "${RED}✗ Error al enviar notificación (Código: $status_code)${NC}"
            echo -e "${YELLOW}Respuesta del servidor: ${response%???}${NC}"
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
    
    page_content=$(curl -s -A "$USER_AGENT" -w "%{http_code}" "$url")
    status_code=${page_content: -3}
    content=${page_content%???}
    
    if [[ $status_code -ne 200 ]]; then
        echo -e "${RED}✗ Error en la solicitud (Código: $status_code)${NC}"
        sleep 60
        continue
    fi
    
    if [[ -z "$content" ]]; then
        echo -e "${RED}✗ No se recibió contenido del servidor${NC}"
        sleep 60
        continue
    fi
    
    latest_version=$(echo "$content" | grep -oP 'S[0-9]{3}[A-Za-z0-9]+UES[0-9A-Z]+(?=")' | head -n 1)
    
    if [[ -z "$latest_version" ]]; then
        echo -e "${RED}✗ No se pudo extraer la versión de la página${NC}"
        echo -e "${YELLOW}ℹ Posibles causas:\n1. Modelo/CSC incorrectos\n2. Estructura del sitio cambiada\n3. No hay actualizaciones disponibles${NC}"
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
