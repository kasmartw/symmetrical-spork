# ✅ Commit Checklist - Antes de Hacer Commit

## 🎯 Quick Reference

### ¿Qué archivos agregar?

```bash
# ✅ AGREGAR estos archivos nuevos al proyecto:
git add .gitignore
git add GIT_GUIDE.md
git add COMMIT_CHECKLIST.md
git add CHANGELOG.md
git add LANGUAGE_AGNOSTIC_UPDATE.md
git add MOCK_API_GUIDE.md
git add QUICKSTART.md
git add SECURITY_NOTES.md
git add mock_api.py
git add pytest.ini
git add run_mock_api.sh
git add src/__init__.py
git add src/config.py
git add src/agent.py          # modificado
git add src/security.py       # modificado
git add src/tools.py          # modificado
git add tests/__init__.py
git add tests/unit/test_api_tools.py
git add tests/unit/test_security.py  # modificado

# O todos a la vez:
git add .gitignore GIT_GUIDE.md COMMIT_CHECKLIST.md CHANGELOG.md \
        LANGUAGE_AGNOSTIC_UPDATE.md MOCK_API_GUIDE.md QUICKSTART.md \
        SECURITY_NOTES.md mock_api.py pytest.ini run_mock_api.sh \
        src/ tests/
```

---

## 🚨 Verificación de Seguridad

### ANTES de hacer commit, verifica:

```bash
# 1. ¿El .env NO está en la lista?
git status | grep -q "\.env$" && echo "⚠️  PELIGRO: .env detectado!" || echo "✅ .env no incluido"

# 2. ¿El venv/ NO está en la lista?
git status | grep -q "venv/" && echo "⚠️  venv/ detectado!" || echo "✅ venv/ no incluido"

# 3. ¿No hay archivos __pycache__?
git status | grep -q "__pycache__" && echo "⚠️  __pycache__ detectado!" || echo "✅ Sin cache"

# 4. ¿No hay archivos .pyc?
git status | grep -q "\.pyc" && echo "⚠️  .pyc detectado!" || echo "✅ Sin .pyc"

# 5. Ver qué archivos se van a commitear:
git status --short
```

---

## 📋 Checklist Completo

### Antes de `git add`:

- [ ] He verificado que `.env` NO está en `git status`
- [ ] He verificado que `venv/` NO está visible
- [ ] He verificado que NO hay `__pycache__/`
- [ ] He revisado cada archivo con `git diff` antes de agregarlo
- [ ] He ejecutado los tests: `pytest`
- [ ] Los tests pasan: ✅ 34 tests passing

### Antes de `git commit`:

- [ ] He revisado `git status` completo
- [ ] He revisado `git diff --staged` (archivos a commitear)
- [ ] El mensaje de commit es descriptivo
- [ ] No incluye información sensible en el mensaje
- [ ] He verificado que solo voy a commitear lo necesario

### Archivos que SÍ deben estar:

```
✅ src/*.py           (código fuente)
✅ tests/**/*.py      (tests)
✅ *.md               (documentación)
✅ pyproject.toml     (configuración)
✅ .env.example       (plantilla)
✅ .gitignore         (reglas de git)
✅ *.sh               (scripts)
```

### Archivos que NO deben estar:

```
❌ .env               (secretos!)
❌ venv/              (entorno virtual)
❌ __pycache__/       (cache de Python)
❌ *.pyc              (bytecode)
❌ .pytest_cache/     (cache de tests)
❌ htmlcov/           (reportes)
❌ .coverage          (datos de coverage)
❌ *.log              (logs)
```

---

## 🎬 Workflow Recomendado

### 1. Revisar cambios:
```bash
git status
git diff
```

### 2. Agregar archivos uno por uno (recomendado):
```bash
git add .gitignore
git status  # verificar

git add src/config.py
git status  # verificar

# etc...
```

### 3. O agregar por categoría:
```bash
# Agregar toda la documentación
git add *.md

# Agregar todo el código fuente
git add src/

# Agregar todos los tests
git add tests/

# Agregar scripts
git add *.sh

# Agregar configuración
git add .gitignore pyproject.toml pytest.ini
```

### 4. Revisar antes de commitear:
```bash
# Ver qué va a ser commiteado
git diff --staged

# Ver solo los nombres de archivo
git diff --staged --name-only
```

### 5. Commit con mensaje descriptivo:
```bash
git commit -m "feat: add mock API and language-agnostic security

- Add mock_api.py with REST endpoints for services/availability/appointments
- Update security.py to be language-agnostic (no language bias)
- Add comprehensive documentation (QUICKSTART, MOCK_API_GUIDE, etc.)
- Add .gitignore to prevent committing secrets/venv/cache
- Add 11 new tests for API tools (34 total passing)
- Update agent.py to use new API tools and improved prompts

Breaking changes: None (backward compatible)
Tests: ✅ 34/34 passing"
```

---

## 🔍 Comandos Útiles

### Ver qué está siendo ignorado:
```bash
git status --ignored
```

### Ver qué está trackeado:
```bash
git ls-files
```

### Ver tamaño del repositorio:
```bash
git count-objects -vH
```

### Verificar si un archivo está ignorado:
```bash
git check-ignore -v .env
# Debe mostrar: .gitignore:7:.env    .env
```

### Buscar secretos accidentalmente agregados:
```bash
git diff --staged | grep -i "api.key\|password\|secret"
```

---

## ⚠️ Si Cometiste un Error

### 1. Agregaste .env por accidente:
```bash
# Antes de commit:
git reset .env

# Después de commit (local, no pushed):
git reset --soft HEAD~1
git reset .env
```

### 2. Commiteaste .env (pero no hiciste push):
```bash
# Deshacer último commit
git reset --hard HEAD~1

# O eliminar del commit:
git rm --cached .env
git commit --amend
```

### 3. Hiciste push de .env a GitHub:
```bash
# 🚨 EMERGENCIA:
# 1. Rotar TODAS las API keys inmediatamente
# 2. Eliminar de historial:
git filter-branch --force --index-filter \
  'git rm --cached --ignore-unmatch .env' \
  --prune-empty --tag-name-filter cat -- --all

# 3. Force push (cuidado!):
git push origin --force --all
```

---

## 📊 Estado Actual del Proyecto

### Archivos nuevos listos para commit:
```
📄 Documentación (8 archivos):
   - CHANGELOG.md
   - COMMIT_CHECKLIST.md
   - GIT_GUIDE.md
   - LANGUAGE_AGNOSTIC_UPDATE.md
   - MOCK_API_GUIDE.md
   - QUICKSTART.md
   - SECURITY_NOTES.md
   - .gitignore

💻 Código (4 archivos):
   - mock_api.py
   - src/config.py
   - src/__init__.py
   - tests/__init__.py

🧪 Tests (1 archivo):
   - tests/unit/test_api_tools.py

🔧 Configuración (2 archivos):
   - pytest.ini
   - run_mock_api.sh

📝 Modificados (4 archivos):
   - src/agent.py
   - src/security.py
   - src/tools.py
   - tests/unit/test_security.py

Total: 19 archivos para agregar
```

### Archivos correctamente ignorados:
```
🚫 .env                    (secretos)
🚫 venv/                   (500MB entorno virtual)
🚫 __pycache__/            (cache Python)
🚫 .pytest_cache/          (cache tests)
🚫 src/*.egg-info/         (metadata)

✅ Total ignorado: ~508MB que NO va a git
```

---

## 🎯 Comando Final

```bash
# Agregar todo lo nuevo (verificado que no incluye secretos)
git add .gitignore GIT_GUIDE.md COMMIT_CHECKLIST.md CHANGELOG.md \
        LANGUAGE_AGNOSTIC_UPDATE.md MOCK_API_GUIDE.md QUICKSTART.md \
        SECURITY_NOTES.md mock_api.py pytest.ini run_mock_api.sh \
        src/ tests/

# Verificar una última vez
git status

# Commit
git commit -m "feat: add mock API and language-agnostic security detection

Major features:
- Mock API with REST endpoints (services, availability, appointments)
- Language-agnostic security (English, Spanish, Chinese support)
- Comprehensive documentation (8 new guides)
- 11 new API tool tests (34 total passing)
- Complete .gitignore configuration

Tests: ✅ 34/34 passing
Coverage: 90%+
"

# Push
git push origin master
```

---

**¿Dudas?** Revisa `GIT_GUIDE.md` para más detalles.
