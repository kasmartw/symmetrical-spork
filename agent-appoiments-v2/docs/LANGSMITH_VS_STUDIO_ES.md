# LangSmith vs LangGraph Studio - Guía de Uso

## 🤔 ¿Cuál es la diferencia?

### **LangSmith** (Lo que configuramos antes)
- **Qué es**: Plataforma de **observabilidad y tracing**
- **Cuándo usar**: Para ver qué hace tu agente en **producción/testing**
- **Qué ves**: Traces de conversaciones reales
- **Cómo se usa**: Automático, solo con variables de entorno

### **LangGraph Studio**
- **Qué es**: IDE visual para **desarrollo**
- **Cuándo usar**: Para **depurar y visualizar** el grafo mientras desarrollas
- **Qué ves**: Visualización del grafo, estado en tiempo real, breakpoints
- **Cómo se usa**: Comando `langgraph dev` + interfaz web

## 📊 Comparación Rápida

| Característica | LangSmith | LangGraph Studio |
|---------------|-----------|------------------|
| **Propósito** | Observabilidad | Desarrollo visual |
| **Interfaz** | Dashboard web | IDE interactivo |
| **Requiere** | API key | `langgraph.json` |
| **Uso** | Automático | Manual (`langgraph dev`) |
| **Costo** | Gratis hasta cierto límite | Gratis |
| **Cuándo** | Producción/Testing | Desarrollo local |

---

## 🚀 Opción 1: Usar LangSmith (Recomendado para ti)

### Si solo quieres ver traces de tus conversaciones:

**1. Configurar `.env`:**
```bash
LANGCHAIN_TRACING_V2=true
LANGCHAIN_API_KEY=lsv2_pt_tu_key_aqui
LANGCHAIN_PROJECT=appointment-agent-v1.2
```

**2. Ejecutar normalmente:**
```bash
# Terminal 1
python mock_api.py

# Terminal 2
python chat_cli.py
```

**3. Ver traces:**
- Ve a: https://smith.langchain.com/
- Proyecto: `appointment-agent-v1.2`
- Verás todas las conversaciones

✅ **ESTO ES LO QUE YA TIENES CONFIGURADO**

---

## 🎨 Opción 2: Usar LangGraph Studio

### Si quieres visualizar el grafo mientras desarrollas:

**1. Instalar LangGraph CLI:**
```bash
pip install "langgraph-cli[inmem]"
```

**2. Verificar que existe `langgraph.json`:**
```bash
# Ya lo creé para ti
cat langgraph.json
```

**3. Ejecutar LangGraph Studio:**
```bash
langgraph dev
```

**4. Abrir navegador:**
- Automáticamente abre: http://localhost:8123
- Verás tu grafo visualmente
- Puedes hacer debugging interactivo

---

## 🔧 Tu Error Específico

### Error 1: "Failed to fetch assistants: Not Found"
**Causa**: No tenías `langgraph.json`
**Solución**: ✅ Ya lo creé para ti

### Error 2: `AttributeError: 'str' object has no attribute 'value'`
**Causa**: Bug en el código con enums
**Solución**: ✅ Ya lo arreglé en `src/agent.py`

---

## 📝 ¿Qué Opción Elegir?

### Usa **LangSmith** (Opción 1) si:
- ✅ Quieres ver qué hace tu agente en conversaciones reales
- ✅ Quieres analizar performance y costos
- ✅ Estás haciendo testing o en producción
- ✅ **ES TU CASO ACTUAL**

### Usa **LangGraph Studio** (Opción 2) si:
- 🛠️ Estás desarrollando/modificando el grafo
- 🛠️ Quieres ver el flujo visualmente
- 🛠️ Necesitas debugging paso a paso
- 🛠️ Quieres breakpoints en nodos específicos

### Usa **AMBOS** si:
- 💪 Quieres lo mejor de ambos mundos
- 💪 Desarrollas en Studio, depliegas con LangSmith

---

## 🎯 Guía Paso a Paso para TI

Basado en tu error, te recomiendo:

### Paso 1: Probar el Fix del Bug
```bash
cd agent-appoiments-v2
source venv/bin/activate

# Prueba que el bug esté arreglado
python test_langsmith_tracing.py
```

### Paso 2: Ejecutar con LangSmith (Más Simple)
```bash
# Terminal 1: API
python mock_api.py

# Terminal 2: Agente
python chat_cli.py

# Usa el agente normalmente
# Ve los traces en: https://smith.langchain.com/
```

### Paso 3 (Opcional): Probar LangGraph Studio
```bash
# Instalar CLI
pip install "langgraph-cli[inmem]"

# Ejecutar Studio
langgraph dev

# Se abrirá http://localhost:8123
```

---

## 🐛 Troubleshooting

### Si LangGraph Studio no funciona:

**Error: "Failed to fetch assistants"**
```bash
# Verifica que langgraph.json existe
ls -la langgraph.json

# Verifica que el grafo exporta correctamente
python -c "from src.agent import create_graph; print('OK')"
```

**Error: "Module not found"**
```bash
# Instala dependencias
pip install -e .
```

### Si LangSmith no muestra traces:

**No aparecen traces**
```bash
# Verifica las variables
cat .env | grep LANGCHAIN

# Deberías ver:
# LANGCHAIN_TRACING_V2=true
# LANGCHAIN_API_KEY=lsv2_pt_...
# LANGCHAIN_PROJECT=appointment-agent-v1.2
```

---

## 💡 Recomendación Final

Para tu caso, **usa LangSmith (Opción 1)**:

1. Ya está configurado
2. No requiere comandos extra
3. Funciona automáticamente
4. Perfecto para ver qué hace tu agente

**LangGraph Studio es opcional** - solo si quieres desarrollo visual avanzado.

---

## 📚 Recursos

- LangSmith Docs: https://docs.smith.langchain.com/
- LangGraph Studio Docs: https://langchain-ai.github.io/langgraph/tutorials/
- Tu guía de LangSmith: `docs/LANGSMITH_QUICKSTART_ES.md`
