#!/bin/bash
# Script para ejecutar el chat CLI con el entorno virtual activado

# Colores para output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}🤖 Iniciando Appointment Booking Agent...${NC}\n"

# Verificar que estamos en el directorio correcto
if [ ! -f "chat_cli.py" ]; then
    echo -e "${RED}❌ Error: chat_cli.py no encontrado${NC}"
    echo "Asegúrate de estar en el directorio agent-appoiments-v2/"
    exit 1
fi

# Verificar que existe el venv
if [ ! -d "venv" ]; then
    echo -e "${RED}❌ Error: Virtual environment no encontrado${NC}"
    echo "Ejecuta primero: python3 -m venv venv"
    exit 1
fi

# Verificar API key
if grep -q "test-key" .env 2>/dev/null; then
    echo -e "${YELLOW}⚠️  WARNING: Usando test-key en .env${NC}"
    echo "Para usar el agente completo, necesitas una API key real de OpenAI"
    echo "Edita .env y reemplaza 'test-key' con tu API key"
    echo ""
    read -p "¿Continuar de todos modos? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 0
    fi
fi

# Activar entorno virtual y ejecutar
echo -e "${GREEN}✅ Activando entorno virtual...${NC}"
source venv/bin/activate

echo -e "${GREEN}✅ Ejecutando chat CLI...${NC}\n"
python3 chat_cli.py

# Desactivar al salir
deactivate
