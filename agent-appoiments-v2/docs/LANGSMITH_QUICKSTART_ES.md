# Guía Rápida: Ejecutar LangSmith

## 📋 Requisitos Previos

1. Cuenta en LangSmith: https://smith.langchain.com/
2. Python y el entorno virtual activado

## 🚀 Pasos para Activar LangSmith

### 1. Obtener tu API Key

1. Ve a https://smith.langchain.com/
2. Inicia sesión (o crea una cuenta gratis)
3. Ve a **Settings** → **API Keys**
4. Crea una nueva API Key
5. Copia la key

### 2. Configurar Variables de Entorno

Edita tu archivo `.env` en la raíz del proyecto:

```bash
# LangSmith Tracing (v1.2)
LANGCHAIN_TRACING_V2=true
LANGCHAIN_API_KEY=lsv2_pt_tu_api_key_aqui
LANGCHAIN_PROJECT=appointment-agent-v1.2
```

### 3. Ejecutar el Agente

El tracing ahora está **automáticamente activado**. Solo ejecuta tu agente normalmente:

```bash
# Terminal 1: Mock API
cd agent-appoiments-v2
source venv/bin/activate
python mock_api.py
```

```bash
# Terminal 2: Agente
cd agent-appoiments-v2
source venv/bin/activate
python chat_cli.py
```

### 4. Ver los Traces en LangSmith

1. Abre https://smith.langchain.com/
2. Ve a tu proyecto `appointment-agent-v1.2`
3. Verás todas las conversaciones en tiempo real

## 📊 ¿Qué Verás en LangSmith?

### Dashboard Principal
- **Runs**: Lista de todas las ejecuciones del agente
- **Latency**: Tiempo de respuesta de cada nodo
- **Cost**: Costo de tokens consumidos
- **Errors**: Trazas de errores si ocurren

### Detalles de Cada Run
- **Timeline**: Secuencia de nodos ejecutados
- **Messages**: Mensajes entre usuario y agente
- **Tool Calls**: Qué herramientas se llamaron y con qué parámetros
- **LLM Calls**: Prompts enviados y respuestas recibidas
- **Tokens**: Uso detallado de tokens (input/output)

## 🔍 Ejemplo de Trace

Cuando un usuario reserva una cita, verás:

```
Run: appointment-booking-12345
├─ Node: agent (120ms)
│  ├─ LLM Call: gpt-4o-mini
│  └─ Tool Decision: get_services_tool
├─ Node: tools (85ms)
│  └─ Tool Execution: get_services_tool
├─ Node: agent (95ms)
│  └─ Response: "Aquí están los servicios..."
```

## ⚙️ Configuración Opcional

### Cambiar el Nombre del Proyecto

En `.env`:
```bash
LANGCHAIN_PROJECT=mi-proyecto-personalizado
```

### Desactivar Tracing Temporalmente

En `.env`:
```bash
LANGCHAIN_TRACING_V2=false
```

### Tracing Solo para Producción

En tu código:
```python
from src.tracing import setup_langsmith_tracing

# Solo activar en producción
if os.getenv("ENVIRONMENT") == "production":
    setup_langsmith_tracing()
```

## 🐛 Solución de Problemas

### "⚠️ LANGCHAIN_API_KEY not set"

**Problema**: No encuentra la API key
**Solución**: Verifica que tu `.env` tenga la variable correcta:
```bash
LANGCHAIN_API_KEY=lsv2_pt_tu_key_aqui
```

### "ℹ️ LangSmith tracing disabled"

**Problema**: Tracing desactivado
**Solución**: Verifica en `.env`:
```bash
LANGCHAIN_TRACING_V2=true  # No "false"
```

### No veo traces en el dashboard

**Problema**: Los traces no aparecen
**Solución**:
1. Verifica que ambas variables estén configuradas
2. Reinicia el agente
3. Espera 10-30 segundos (a veces hay retraso)

## 📈 Casos de Uso

### 1. Debugging
Ver exactamente qué pasó en una conversación fallida

### 2. Optimización
Identificar nodos lentos (> 1s) y optimizar

### 3. Análisis de Costo
Monitorear cuántos tokens consume tu agente

### 4. Testing
Comparar diferentes versiones del prompt

## 🎯 Próximos Pasos

- **Datasets**: Crea datasets de prueba en LangSmith
- **Evaluations**: Configura evaluaciones automáticas
- **Annotations**: Marca runs importantes con etiquetas
- **Feedback**: Agrega feedback de usuario a los runs

## 📚 Más Información

- Documentación oficial: https://docs.smith.langchain.com/
- Guía completa: `docs/LANGSMITH.md` (en inglés)
