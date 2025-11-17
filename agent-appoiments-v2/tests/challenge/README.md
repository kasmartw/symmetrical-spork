# 🔥 Tests de Desafío del Agente

Suite de tests diseñados para **retar** al agente de reservas y verificar su robustez en condiciones reales y extremas.

## 📋 Índice de Tests

### ✅ Test 1: Flujos Completos End-to-End
**Archivo:** `test_1_complete_flows.py`

**Objetivo:** Verificar que el agente completa flujos completos sin errores.

**Tests incluidos:**
- ✅ Booking perfecto en español
- ✅ Booking perfecto en inglés
- ✅ Cancelación con confirmation válido
- 🔥 Cancelación con confirmation inválido (debe escalar después de 2 intentos)
- ✅ Reprogramación completa

**Ejecutar:**
```bash
./run_challenge_tests.sh 1
# O directamente:
pytest tests/challenge/test_1_complete_flows.py -v -s
```

---

### 🔥 Test 2: Edge Cases y Comportamientos Impredecibles
**Archivo:** `test_2_edge_cases.py`

**Objetivo:** Verificar que el agente maneja comportamientos impredecibles del usuario.

**Tests incluidos:**
- 🔥 Usuario cambia de opinión a mitad del flujo
- 🔥 Usuario da toda la info en un mensaje
- 🔥 Usuario envía gibberish y intentos de injection
- 🔥 Usuario envía múltiples mensajes rápidamente (double-texting)
- 🔥 Emails inválidos (validación robusta)
- 🔥 Teléfonos inválidos (validación robusta)
- 🔥 Fechas límite (pasado, futuro lejano)

**Ejecutar:**
```bash
./run_challenge_tests.sh 2
# O directamente:
pytest tests/challenge/test_2_edge_cases.py -v -s
```

---

### ⚡ Test 3: Concurrencia y Carga
**Archivo:** `test_3_concurrency.py`

**Objetivo:** Verificar que el agente maneja múltiples usuarios simultáneos.

**Tests incluidos:**
- ✅ 5 usuarios concurrentes (carga ligera)
- 🔥 10 usuarios concurrentes (carga media)
- 🔥🔥 20 usuarios concurrentes (carga alta)
- ✅ 10 usuarios secuenciales (carga realista)

**Métricas evaluadas:**
- Success rate (>=80%)
- Tiempo promedio (<90s)
- Tiempo máximo (<150s)
- Desviación estándar

**Ejecutar:**
```bash
./run_challenge_tests.sh 3
# O directamente:
pytest tests/challenge/test_3_concurrency.py -v -s
```

---

### 🛡️ Test 4: Resiliencia y Manejo de Errores
**Archivo:** `test_4_resilience.py`

**Objetivo:** Verificar que el agente maneja errores y se recupera correctamente.

**Tests incluidos:**
- 🔥 API no disponible (graceful degradation)
- 🔥 Timeout de API (retry logic)
- 🔥 Estado inválido (recovery)
- 🔥 Conversación larga (sliding window)
- 🔥 Cambios rápidos entre threads
- 🔥 Intentos de prompt injection
- 🔥 Datos con caracteres especiales

**Ejecutar:**
```bash
./run_challenge_tests.sh 4
# O directamente:
pytest tests/challenge/test_4_resilience.py -v -s
```

---

## 🚀 Ejecución Rápida

### Ejecutar TODOS los tests:
```bash
./run_challenge_tests.sh all
# O simplemente:
./run_challenge_tests.sh
```

### Ejecutar un test específico:
```bash
./run_challenge_tests.sh 1   # Solo Test 1
./run_challenge_tests.sh 2   # Solo Test 2
./run_challenge_tests.sh 3   # Solo Test 3
./run_challenge_tests.sh 4   # Solo Test 4
```

### Ejecutar con pytest directamente:
```bash
# Ejecutar todo con output detallado
pytest tests/challenge/ -v -s

# Ejecutar solo un archivo
pytest tests/challenge/test_1_complete_flows.py -v -s

# Ejecutar un test específico
pytest tests/challenge/test_1_complete_flows.py::TestCompleteBookingFlows::test_perfect_booking_flow_spanish -v -s

# Ejecutar en paralelo (requiere pytest-xdist)
pytest tests/challenge/ -n auto
```

---

## 📊 Interpretación de Resultados

### ✅ Símbolos
- ✅ **Test pasa** - El agente cumple los criterios
- ❌ **Test falla** - El agente no cumple los criterios
- 🔥 **Test de estrés** - Diseñado para ser difícil

### 📈 Métricas Clave

**Success Rate:**
- ✅ ≥90%: Excelente
- ⚠️ 80-90%: Aceptable
- ❌ <80%: Requiere mejoras

**Tiempo Promedio:**
- ✅ <60s: Excelente
- ⚠️ 60-90s: Aceptable
- ❌ >90s: Requiere optimización

**Concurrencia:**
- ✅ 10+ usuarios sin degradación: Listo para producción
- ⚠️ 5-10 usuarios: Uso limitado
- ❌ <5 usuarios: Solo desarrollo

---

## 🔧 Requisitos

### Dependencias:
```bash
pip install pytest pytest-asyncio
```

### Servicios necesarios:
1. **Mock API** debe estar corriendo:
   ```bash
   python mock_api.py
   ```

2. **LangGraph** (opcional, solo para Studio):
   ```bash
   langgraph dev
   ```

---

## 🎯 Criterios de Éxito para MVP

Para considerar el agente **listo para MVP**, debe cumplir:

- [ ] **Test 1:** 100% de flujos completos pasan
- [ ] **Test 2:** ≥80% de edge cases manejados
- [ ] **Test 3:** Soporta ≥10 usuarios concurrentes con success rate ≥80%
- [ ] **Test 4:** Maneja errores sin crashear (100% recovery)

---

## 🐛 Troubleshooting

### Error: "No se pudo crear booking para fixture"
- **Causa:** Mock API no está corriendo o tiene datos corruptos
- **Solución:** Reiniciar `python mock_api.py`

### Error: "Connection refused"
- **Causa:** Puerto 5000 no disponible
- **Solución:** Verificar que Mock API está corriendo

### Tests muy lentos
- **Causa:** Múltiples llamadas a API sin cache
- **Solución:** Verificar que el cache está habilitado en `src/cache.py`

### Success rate bajo en concurrencia
- **Causa:** MemorySaver no es thread-safe
- **Solución:** Esperado con MemorySaver, PostgreSQL lo resolvería

---

## 📝 Notas de Desarrollo

### Limitaciones conocidas con MemorySaver:
- No es thread-safe (esperado en tests de concurrencia)
- Estado se pierde al reiniciar proceso
- No adecuado para producción distribuida

### Mejoras futuras:
- Agregar tests de latencia TTFT
- Tests de memory leaks
- Tests de degradación sostenida
- Integración con métricas de LangSmith

---

## 📞 Soporte

Si encuentras problemas con los tests:
1. Verificar que Mock API está corriendo
2. Verificar versiones de dependencias (`pip list | grep pytest`)
3. Revisar logs en `tests/challenge/pytest.log` (si existe)

**Reporte de bugs:** Incluir output completo de pytest con `-v -s`
