#!/bin/bash
# Script para ejecutar los tests de desafío del agente
# Uso: ./run_challenge_tests.sh [test_number]

set -e  # Exit on error

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Banner
echo -e "${BLUE}╔══════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║          AGENT CHALLENGE TESTS - v1.11                   ║${NC}"
echo -e "${BLUE}╚══════════════════════════════════════════════════════════╝${NC}"
echo ""

# Check if pytest is installed
if ! command -v pytest &> /dev/null; then
    echo -e "${RED}❌ pytest no está instalado${NC}"
    echo "Instalar con: pip install pytest pytest-asyncio"
    exit 1
fi

# Check if mock API is running
if ! curl -s http://localhost:5000/health > /dev/null 2>&1; then
    echo -e "${YELLOW}⚠️  Mock API no está corriendo en puerto 5000${NC}"
    echo "Iniciar con: python mock_api.py"
    echo ""
    read -p "¿Continuar de todos modos? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Function to run test
run_test() {
    local test_file=$1
    local test_name=$2

    echo -e "\n${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${GREEN}▶ Ejecutando: ${test_name}${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

    pytest "${test_file}" -v -s --tb=short

    if [ $? -eq 0 ]; then
        echo -e "\n${GREEN}✅ ${test_name} - PASÓ${NC}"
    else
        echo -e "\n${RED}❌ ${test_name} - FALLÓ${NC}"
    fi
}

# Main logic
case "${1:-all}" in
    1)
        run_test "tests/challenge/test_1_complete_flows.py" "TEST 1: Flujos Completos"
        ;;
    2)
        run_test "tests/challenge/test_2_edge_cases.py" "TEST 2: Edge Cases"
        ;;
    3)
        run_test "tests/challenge/test_3_concurrency.py" "TEST 3: Concurrencia"
        ;;
    4)
        run_test "tests/challenge/test_4_resilience.py" "TEST 4: Resiliencia"
        ;;
    all)
        echo -e "${YELLOW}📋 Ejecutando TODOS los tests de desafío...${NC}\n"

        run_test "tests/challenge/test_1_complete_flows.py" "TEST 1: Flujos Completos"
        run_test "tests/challenge/test_2_edge_cases.py" "TEST 2: Edge Cases"
        run_test "tests/challenge/test_3_concurrency.py" "TEST 3: Concurrencia"
        run_test "tests/challenge/test_4_resilience.py" "TEST 4: Resiliencia"

        echo -e "\n${BLUE}╔══════════════════════════════════════════════════════════╗${NC}"
        echo -e "${BLUE}║                  RESUMEN FINAL                           ║${NC}"
        echo -e "${BLUE}╚══════════════════════════════════════════════════════════╝${NC}"
        echo ""
        echo "Todos los tests completados"
        echo "Revisar salida arriba para ver resultados detallados"
        ;;
    *)
        echo -e "${RED}Uso: $0 [1|2|3|4|all]${NC}"
        echo ""
        echo "Opciones:"
        echo "  1   - Test 1: Flujos Completos End-to-End"
        echo "  2   - Test 2: Edge Cases y Comportamientos Impredecibles"
        echo "  3   - Test 3: Concurrencia y Carga"
        echo "  4   - Test 4: Resiliencia y Manejo de Errores"
        echo "  all - Ejecutar TODOS los tests (por defecto)"
        echo ""
        echo "Ejemplo: $0 1"
        exit 1
        ;;
esac

echo ""
echo -e "${GREEN}✨ Ejecución completada${NC}"
