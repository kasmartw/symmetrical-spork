#!/bin/bash
# Script para crear paquete de revisión para supervisor
# Uso: bash create_review_package.sh [minimal|full]

PACKAGE_TYPE=${1:-minimal}
DATE=$(date +%Y%m%d)
OUTPUT_DIR="review_package_${DATE}"

echo "📦 Creando paquete de revisión: $PACKAGE_TYPE"

# Crear directorio de salida
mkdir -p "$OUTPUT_DIR"

# Archivos comunes a ambos paquetes
echo "📋 Copiando documentación esencial..."
cp MVP_READINESS_REPORT.md "$OUTPUT_DIR/"
cp README.md "$OUTPUT_DIR/"
cp instruction_and_logic.md "$OUTPUT_DIR/"
cp docs/v1.10-production-verdict.md "$OUTPUT_DIR/" 2>/dev/null || echo "⚠️  v1.10-production-verdict.md no encontrado"

# Copiar código core
echo "🧠 Copiando código principal..."
mkdir -p "$OUTPUT_DIR/src"
cp src/agent.py "$OUTPUT_DIR/src/"
cp src/tools.py "$OUTPUT_DIR/src/"

# Copiar tests
echo "🧪 Copiando tests..."
cp test_v110_concurrency.py "$OUTPUT_DIR/" 2>/dev/null || echo "⚠️  test_v110_concurrency.py no encontrado"

if [ "$PACKAGE_TYPE" == "full" ]; then
    echo "📦 Modo COMPLETO: agregando archivos adicionales..."

    # Más documentación
    cp ../docs/plans/2025-01-16-production-resilience-improvements.md "$OUTPUT_DIR/" 2>/dev/null

    # Más código
    cp src/state.py "$OUTPUT_DIR/src/"
    cp src/tools_appointment_mgmt.py "$OUTPUT_DIR/src/"
    cp src/config.py "$OUTPUT_DIR/src/"
    cp src/org_config.py "$OUTPUT_DIR/src/"

    # Configuración
    cp langgraph.json "$OUTPUT_DIR/"
    cp pyproject.toml "$OUTPUT_DIR/"

    # Tests adicionales
    mkdir -p "$OUTPUT_DIR/tests/integration"
    cp tests/integration/test_agent_flows.py "$OUTPUT_DIR/tests/integration/" 2>/dev/null
fi

# Crear archivo de índice
cat > "$OUTPUT_DIR/INDEX.md" << 'EOF'
# Índice de Archivos - Revisión de MVP

## Documentación
- `MVP_READINESS_REPORT.md` - **EMPEZAR AQUÍ**: Resumen ejecutivo y análisis de preparación
- `README.md` - Documentación general del proyecto
- `instruction_and_logic.md` - Lógica detallada y flujos de conversación
- `v1.10-production-verdict.md` - Análisis técnico de versión 1.10

## Código Principal
- `src/agent.py` - Grafo de LangGraph (orquestación principal)
- `src/tools.py` - Herramientas del agente (servicios, disponibilidad, validaciones)
- `src/state.py` - Definición de estado conversacional (si incluido)
- `src/tools_appointment_mgmt.py` - Herramientas de gestión de citas (si incluido)

## Configuración
- `src/config.py` - Configuración del sistema (si incluido)
- `src/org_config.py` - Configuración multi-tenancy (si incluido)
- `langgraph.json` - Configuración de LangGraph (si incluido)
- `pyproject.toml` - Dependencias del proyecto (si incluido)

## Testing
- `test_v110_concurrency.py` - Pruebas de concurrencia
- `tests/integration/test_agent_flows.py` - Tests de flujos completos (si incluido)

## Orden de Lectura Recomendado

1. **MVP_READINESS_REPORT.md** - Visión general y conclusiones
2. **instruction_and_logic.md** - Entender el diseño y flujos
3. **src/agent.py** - Ver la implementación principal
4. **v1.10-production-verdict.md** - Análisis técnico profundo
5. Resto de archivos según interés específico

EOF

# Comprimir
echo "🗜️  Comprimiendo paquete..."
tar -czf "${OUTPUT_DIR}.tar.gz" "$OUTPUT_DIR"

echo ""
echo "✅ Paquete creado exitosamente:"
echo "   📁 Directorio: $OUTPUT_DIR/"
echo "   📦 Archivo:    ${OUTPUT_DIR}.tar.gz"
echo ""
echo "📧 Para enviar:"
echo "   - Adjunta el archivo .tar.gz a tu email, o"
echo "   - Comparte la carpeta $OUTPUT_DIR/ directamente"
echo ""
echo "📋 Archivos incluidos:"
ls -lh "$OUTPUT_DIR"
echo ""
echo "📊 Tamaño total:"
du -sh "$OUTPUT_DIR"
du -sh "${OUTPUT_DIR}.tar.gz"
