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

