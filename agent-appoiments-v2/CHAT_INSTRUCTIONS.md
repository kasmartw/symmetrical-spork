# 💬 Instrucciones para Ejecutar el Chat - ¡SOLUCIÓN AL ERROR!

## ❌ **Error Común**

Si ves este error:
```
ModuleNotFoundError: No module named 'llm_guard'
```

**Causa:** No activaste el entorno virtual antes de ejecutar el script.

---

## ✅ **Solución: 3 Formas de Ejecutar el Chat**

### **Opción 1: Script Automático (MÁS FÁCIL)** 🚀

```bash
./run_chat.sh
```

Este script:
- ✅ Activa automáticamente el venv
- ✅ Verifica que todo esté OK
- ✅ Ejecuta el chat
- ✅ Desactiva el venv al salir

---

### **Opción 2: Comando Manual (UNA LÍNEA)**

```bash
source venv/bin/activate && python3 chat_cli.py
```

**Nota:** Tienes que ejecutar esto **cada vez** en una línea.

---

### **Opción 3: Paso a Paso (DETALLADO)**

```bash
# 1. Activar entorno virtual
source venv/bin/activate

# 2. Verificar que está activado (deberías ver "(venv)" en el prompt)
# Tu prompt debería verse así:
# (venv) usuario@pc:~/path/agent-appoiments-v2$

# 3. Ejecutar el chat
python3 chat_cli.py

# 4. Al terminar, desactivar (opcional)
deactivate
```

---

## 🎯 **Método Recomendado**

**Usa el script automático:**

```bash
./run_chat.sh
```

**¿Por qué?**
- ✅ No tienes que recordar activar el venv
- ✅ Verifica errores automáticamente
- ✅ Te avisa si falta la API key
- ✅ Más fácil y seguro

---

## 🔍 **Verificación Rápida**

Si quieres verificar que el venv está activado correctamente:

```bash
source venv/bin/activate
which python3
```

**Debería mostrar:**
```
/home/tu-usuario/path/agent-appoiments-v2/venv/bin/python3
```

**NO debería mostrar:**
```
/usr/bin/python3  ❌ (Esto es Python del sistema, no del venv)
```

---

## 🛠️ **Si Aún No Funciona**

### Problema: "venv/bin/activate: No such file or directory"

**Solución:** Crear el venv primero
```bash
python3 -m venv venv
pip install --upgrade pip
pip install -e ".[dev]"
```

### Problema: "Permission denied: ./run_chat.sh"

**Solución:** Dar permisos de ejecución
```bash
chmod +x run_chat.sh
```

### Problema: Sigue apareciendo "ModuleNotFoundError"

**Solución:** Reinstalar dependencias
```bash
source venv/bin/activate
pip install --upgrade pip
pip install -e ".[dev]"
```

---

## 📝 **Resumen - Lo que NO Funciona**

❌ **INCORRECTO:**
```bash
python chat_cli.py          # Sin activar venv
python3 chat_cli.py         # Sin activar venv
./chat_cli.py               # Sin activar venv
```

✅ **CORRECTO:**
```bash
./run_chat.sh                              # Opción 1: Automático
source venv/bin/activate && python3 chat_cli.py  # Opción 2: Manual
```

---

## 🎓 **Explicación Técnica**

### ¿Por qué necesito activar el venv?

1. **Python del sistema** (`/usr/bin/python3`):
   - No tiene llm-guard instalado
   - No tiene las dependencias del proyecto

2. **Python del venv** (`venv/bin/python3`):
   - ✅ Tiene todas las dependencias instaladas
   - ✅ Versión correcta de todos los paquetes

3. **Activar venv** hace que:
   - Tu shell use el Python del venv
   - Los comandos `python` y `pip` usen el venv
   - Las dependencias estén disponibles

---

## 🚀 **Quick Start - Copia y Pega**

```bash
# Configurar API key (solo primera vez)
nano .env  # Reemplazar "test-key" con tu API key real

# Ejecutar chat (siempre)
./run_chat.sh
```

**¡ESO ES TODO!** 🎉

---

## 📚 **Más Información**

- **Guía de testing**: `TESTING_GUIDE.md`
- **Guía de chat detallada**: `CHAT_QUICKSTART.md`
- **README principal**: `README.md`

---

## 💡 **Pro Tips**

1. **Alias útil** (añade a tu `.bashrc` o `.zshrc`):
   ```bash
   alias chat='cd ~/path/agent-appoiments-v2 && ./run_chat.sh'
   ```
   Ahora solo ejecuta: `chat`

2. **Verifica siempre** que veas `(venv)` en tu prompt

3. **Si cambias de terminal**, activa el venv de nuevo

---

**¿Sigue sin funcionar?** Ejecuta:
```bash
source venv/bin/activate
pip install -e ".[dev]"
./run_chat.sh
```
