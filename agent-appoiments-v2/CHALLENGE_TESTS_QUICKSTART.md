# 🚀 Quick Start - Tests de Desafío

Guía rápida para ejecutar los tests de desafío del agente.

## 📦 Setup (Una sola vez)

```bash
# 1. Instalar dependencias
pip install pytest pytest-asyncio

# 2. Iniciar Mock API (dejar corriendo en una terminal)
python mock_api.py
```

## ⚡ Ejecución Rápida

### Ejecutar TODOS los tests:
```bash
./run_challenge_tests.sh
```

### Ejecutar un test específico:
```bash
./run_challenge_tests.sh 1   # Test 1: Flujos Completos
./run_challenge_tests.sh 2   # Test 2: Edge Cases
./run_challenge_tests.sh 3   # Test 3: Concurrencia
./run_challenge_tests.sh 4   # Test 4: Resiliencia
```

## 📊 ¿Qué se está probando?

### Test 1: Flujos Completos ✅
- Booking en español e inglés
- Cancelación y reprogramación
- **Criterio:** 100% de flujos completan

### Test 2: Edge Cases 🔥
- Cambios de opinión
- Gibberish y injection attempts
- Validaciones de email/teléfono
- **Criterio:** ≥80% manejados

### Test 3: Concurrencia ⚡
- 5, 10, 20 usuarios simultáneos
- **Criterio:** Success rate ≥80%

### Test 4: Resiliencia 🛡️
- API caída, timeouts
- Prompt injection
- **Criterio:** 100% recovery sin crashes

## ✅ Interpretar Resultados

```
✅ PASSED - El agente pasó el test
❌ FAILED - El agente falló (revisar output)
⚠️  WARNINGS - Pasó pero con advertencias
```

## 🐛 Problemas Comunes

**Error: Connection refused**
```bash
# Solución: Iniciar Mock API
python mock_api.py
```

**Tests muy lentos**
```bash
# Normal - cada test puede tomar 30-60s
# Para tests rápidos, ejecutar uno solo:
./run_challenge_tests.sh 1
```

## 📝 Siguiente Paso

Después de ejecutar los tests, revisar:
- `tests/challenge/README.md` - Documentación completa
- Output detallado en terminal
- Success rate y tiempos promedio

---

**¿Listo para MVP?** El agente debe pasar ≥80% de todos los tests.
