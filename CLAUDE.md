# SantoniBot - Sistema Inteligente de Análisis de Datos Empresariales

## Resumen del Proyecto
Sistema de IA empresarial para **Alimentos Santoni, C.A.** (procesadora de arroz y maíz en Venezuela).
Desarrollado por **OVA Agency**. Arquitectura multi-agente con 7 agentes departamentales especializados
que consultan datos en tiempo real desde el ERP iDempiere.

**Objetivo:** Permitir a gerentes y supervisores de cada departamento consultar datos operativos
en lenguaje natural via chat (web y futuro WhatsApp), sin necesidad de conocer SQL ni navegar el ERP.

---

## Tech Stack

| Capa | Tecnología |
|------|-----------|
| Frontend | Next.js 14 + React + TypeScript + Tailwind CSS |
| Backend | Python 3.12 + FastAPI |
| DB interna | PostgreSQL 16 (usuarios, conversaciones, auditoría) |
| DB empresarial | PostgreSQL 13 (iDempiere ERP - solo lectura) |
| Vector DB | ChromaDB (RAG / base de conocimiento) |
| IA primaria | OpenRouter (DeepSeek Chat v3) - producción |
| IA secundaria | Groq (Llama 3.3 70B) - alternativa gratuita |
| IA documentos | Claude API (Anthropic) - análisis de documentos/imágenes |
| Orquestación | LangChain |
| Deploy | Docker Compose + Nginx reverse proxy |
| CI/CD | GitHub Actions + Coolify |
| Monitoreo | Sentry (opcional) + logging estructurado |

---

## Estructura del Proyecto

```
Santoni-Bot/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI app entry point
│   │   ├── config.py            # Settings desde .env
│   │   ├── database.py          # SQLAlchemy engines (dual DB)
│   │   ├── api/routes/          # Endpoints REST
│   │   ├── agents/              # Agentes IA (ver sección abajo)
│   │   │   ├── orchestrator.py  # Clasificador de intención + router
│   │   │   ├── base_agent.py    # Clase base para todos los agentes
│   │   │   ├── date_utils.py    # Parsing de fechas en español
│   │   │   ├── ventas.py
│   │   │   ├── finanzas.py
│   │   │   ├── contabilidad.py
│   │   │   ├── rrhh.py
│   │   │   ├── produccion.py
│   │   │   ├── compras_insumos.py
│   │   │   └── compras_productores.py
│   │   ├── models/              # SQLAlchemy models
│   │   ├── schemas/             # Pydantic schemas
│   │   ├── services/
│   │   │   ├── auth.py          # Autenticación JWT + bcrypt
│   │   │   ├── query_service.py # Queries a iDempiere (read-only)
│   │   │   ├── idempiere_queries.py # SQL queries específicas
│   │   │   ├── llm_factory.py   # Factory para cambio de proveedor IA
│   │   │   ├── rag_service.py   # ChromaDB / base de conocimiento
│   │   │   ├── export_service.py # Exportación CSV/Excel/PDF
│   │   │   ├── document_service.py # Análisis de documentos
│   │   │   ├── audit.py         # Logging de auditoría
│   │   │   └── cache.py         # Cache de queries
│   │   ├── middleware/          # Auth, seguridad, CORS
│   │   └── utils/
│   ├── tests/                   # 150+ tests (pytest)
│   ├── alembic/                 # Migraciones de DB
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/
│   ├── app/                     # Next.js pages
│   ├── components/              # React components (chat, sidebar, admin)
│   ├── hooks/                   # useAuth, etc.
│   ├── lib/                     # API client, utilidades
│   ├── __tests__/               # Tests frontend
│   ├── Dockerfile
│   └── package.json
├── nginx/                       # Reverse proxy config
├── scripts/                     # setup-vm.sh, deploy.sh, backup.sh
├── coolify/                     # Coolify deployment config
├── docs/                        # Documentación del proyecto
│   ├── ESTATUS_PROYECTO.md      # Tracking detallado de tareas
│   ├── DOCUMENTO_TECNICO.md     # Documento técnico completo
│   ├── cuestionario_validacion_agentes.md # Formularios de validación
│   └── manuales varios
├── docker-compose.yml           # Desarrollo (5 servicios)
├── docker-compose.prod.yml      # Override producción
├── .env.example                 # Template de variables de entorno
└── CLAUDE.md                    # Este archivo
```

---

## Comandos Principales

```bash
# Desarrollo local
cd backend && uvicorn app.main:app --reload     # Backend en :8000
cd frontend && npm run dev                       # Frontend en :3000

# Docker (ambiente completo)
docker compose up -d --build                     # Levantar todo
docker compose logs backend --tail 50            # Ver logs backend
docker compose logs frontend --tail 50           # Ver logs frontend
docker compose down && docker compose up -d      # Reiniciar todo

# Tests
cd backend && pytest                             # Tests backend (150+)
cd frontend && npm test                          # Tests frontend

# Migraciones
cd backend && alembic upgrade head               # Aplicar migraciones

# Producción (en servidor 192.168.1.26)
cd /opt/santonibot
git pull origin main
docker compose build --no-cache backend frontend && docker compose up -d
```

---

## Los 7 Agentes + Orquestador

### Flujo de una consulta:
1. Usuario envía mensaje por chat
2. **Selector de agente** (frontend): si el usuario seleccionó un agente, va directo a él
3. **Orchestrator** (fallback): si no hay selector, clasifica la intención y selecciona el agente
4. El agente especializado genera la query SQL apropiada
5. Se ejecuta contra iDempiere (read-only) via `query_service.py`
6. El agente formatea la respuesta con tablas markdown
7. Se devuelve al usuario con opción de exportar (CSV/Excel/PDF)

### Selector de agentes (implementado Mar 2026):
- Frontend muestra tabs con los agentes disponibles para el usuario
- Si el usuario selecciona un agente, `agent_name` se envía en el `ChatRequest`
- Backend valida permisos y envía directo al agente sin pasar por el orchestrator
- Si "Automático" está seleccionado, funciona como antes (orchestrator decide)
- Endpoint `GET /api/chat/agents` retorna los agentes disponibles para el usuario

### Agentes:

| # | Agente | Archivo | Capacidades principales |
|---|--------|---------|------------------------|
| 1 | **Ventas** | `ventas.py` | Top clientes, facturación, cobranza, zonas, tipología, por moneda (VES/USD), por organización |
| 2 | **Finanzas** | `finanzas.py` | Saldos bancarios, cuentas por cobrar/pagar, flujo de caja |
| 3 | **Contabilidad** | `contabilidad.py` | Balance general, estado de resultados, libro diario/mayor, cuentas contables |
| 4 | **RRHH** | `rrhh.py` | Empleados activos, búsqueda por cargo, ausentismo, nómina, rotación, cumpleañeros |
| 5 | **Producción** | `produccion.py` | Órdenes de producción, cantidades, desperdicios, inventario (m_storageonhand) |
| 6 | **Compras Insumos** | `compras_insumos.py` | Compras por producto/proveedor, historial, precios, separación por moneda, órdenes de compra pendientes (c_order), comparación de precios entre proveedores, estado de pago de facturas |
| 7 | **Compras Productores** | `compras_productores.py` | Compras agrícolas (arroz, maíz), productores registrados, pagos pendientes, precios |

### Características transversales de los agentes:
- **Follow-ups inteligentes**: Heredan contexto temporal (mes/año/rango), producto y filtros del historial
- **Fallback sin datos**: Si un período no tiene datos, algunos agentes (ventas) intentan con el año completo
- **Error handling dual**: try/except en `base_agent.py` + try/except interno en cada `fetch_data()`
- **Confidence score**: Cada respuesta incluye nivel de confianza
- **Detección automática de moneda**: Separan consultas en VES y USD
- **Anti-hallucination**: No inventan datos, indican cuando no tienen información
- **Historial**: 40 mensajes (20 intercambios) de contexto

---

## Organizaciones en iDempiere

El ERP maneja 8 organizaciones (empresas del grupo):

| # | Organización | Código moneda (iso_code) | Actividad |
|---|-------------|-------------------------|-----------|
| 1 | **INPROA SANTONI C.A.** | DOL | Procesadora de arroz (principal) |
| 2 | **InproMaiz C.A** | DoL | Procesadora de maíz |
| 3 | **Santoni Service C.A** | DLA | Servicios |
| 4 | **AGROPECUARIA R.R. C.A.** | dol | Agropecuaria |
| 5 | **AGA AGRICOLA C.A** | (VES) | Agrícola |
| 6 | **AGROINPROA C.A** | USA | Agroindustrial |
| 7 | **INVERSIONES AGA C.A** | Dol | Inversiones |
| 8 | **Agro Import** | - | Importaciones |

**IMPORTANTE — Monedas en iDempiere:**
Cada organización tiene su propia moneda con iso_code diferente (DOL, DoL, Dol, dol, DLA, USA, US., etc.)
pero TODAS representan dólares. El bot las agrupa usando `c_currency_id`:
- `c_currency_id = 205` → **Bolívares (VES/Bs.)**
- `c_currency_id IN (100, 1000000, 1000003, 1000006, 1000008, 1000009, 1000011, 1000013, 1000017)` → **Dólares (USD)**

Los agentes filtran por organización cuando el usuario lo especifica.

---

## Seguridad

- **RBAC**: Roles (usuario, supervisor, administrador) + departamentos (7)
- **JWT**: Tokens con expiración configurable
- **iDempiere read-only**: `SET default_transaction_read_only = ON`
- **Anonymizer**: Datos sensibles se enmascaran antes de enviar al LLM
- **Rate limiting**: API 30r/m, login 5r/m, export 10r/m
- **Nginx**: CSP, X-Frame-Options, gzip, security headers
- **Audit logs**: Cada acción queda registrada con usuario, IP, timestamp

---

## Datos del Entorno de Producción

| Recurso | Valor |
|---------|-------|
| Servidor SantoniBot | 192.168.1.26 (Ubuntu, 16GB RAM, 8 CPU) |
| Servidor iDempiere | 192.168.1.73:5432 (PostgreSQL 13) |
| DB iDempiere | `idempiere_produccion` |
| Ruta en servidor | `/opt/santonibot` |
| VPN | FortiClient (requerido desde fuera de Santoni) |

---

## Proveedores de IA (configuración via AI_PROVIDER en .env)

| Proveedor | Variable | Uso | Notas |
|-----------|----------|-----|-------|
| OpenRouter | `OPENROUTER_API_KEY` | Producción (DeepSeek v3) | Recomendado, pay-as-you-go |
| Groq | `GROQ_API_KEY` | Alternativa gratuita | Límite 100K tokens/día |
| Anthropic | `ANTHROPIC_API_KEY` | Análisis de documentos | Requiere proxy en Venezuela (`ANTHROPIC_BASE_URL`) |

---

## Dataset de Entrenamiento

Se mantiene un dataset de escenarios de entrenamiento/validación para el orchestrator:
- **364 escenarios** (v2.6) cubriendo los 7 agentes
- Incluye: pregunta, agente esperado, tipo de consulta, follow-ups
- 78 escenarios de follow-up con herencia de contexto
- Tipos de error rastreados: routing, herencia temporal, fallback sin datos, errores DB,
  docstatus_incompleto, org_name_no_extraido, no_access_text
- Usado para medir confidence score y mejorar clasificación

---

## Cuestionarios de Validación

Se crearon cuestionarios para que cada departamento valide las respuestas del bot contra datos reales:
- Archivo: `docs/cuestionario_validacion_agentes.md`
- También existe versión Word: `docs/CUESTIONARIO DE LEVANTAMIENTO Alimentos santoni.docx`
- Los responsables de cada área llenan las preguntas exactas y respuestas esperadas
- Esto permite verificar precisión antes de puesta en producción

---

## Estado Actual del Proyecto (Marzo 2026)

### Completado (~91% del alcance Fase 1):
- Backend core completo (FastAPI, auth, RBAC, API endpoints)
- 7 agentes IA + orchestrator funcionando con iDempiere real
- Frontend completo (chat, login, admin panel, exportaciones)
- Docker/deploy configurado y funcionando en servidor
- 150+ tests automatizados
- CI/CD con GitHub Actions
- Documentación completa
- Seguridad hardened

### Trabajo reciente (Feb-Mar 2026):
- **Datos históricos locales (10/Mar 2026)**: Sistema para cachear datos de iDempiere pre-marzo 2026 en DB local (ver sección abajo)
- Conexión exitosa a iDempiere real (queries de nómina, ventas, compras)
- Follow-ups inteligentes con herencia de contexto temporal
- Confidence score + dataset de 355 escenarios (v2.5)
- Separación de compras por moneda (VES/USD)
- Inventario desde m_storageonhand
- Corrección de múltiples bugs reportados por usuarios reales
- Script de pruebas en vivo (65 preguntas, 7 agentes)
- Diagnóstico de nómina iDempiere
- **Fix crítico (Mar 2026)**: Herencia temporal + manejo de errores en los 7 agentes (ver sección abajo)
- **Expansión compras_insumos (10/Mar 2026)**:
  - Órdenes de compra pendientes (c_order) - antes solo consultaba facturas confirmadas
  - Comparación de precios entre proveedores para un mismo producto
  - Estado de pago de facturas (pagadas vs pendientes vs vencidas)
  - Fallback automático sin fecha cuando período específico no tiene datos
  - Búsqueda de productos más flexible (normalización de acentos, OR para 3+ palabras)
  - Fix de texto "no tengo acceso" en capabilities de todos los agentes (causaba falsos positivos en tests)
- **Fix docstatus + org_name en compras (11/Mar 2026)**:
  - `docstatus = 'CO'` → `docstatus IN ('CO', 'CL')` en TODAS las queries de idempiere_queries.py
    (facturas pagadas cambian a 'CL' en iDempiere, se estaban excluyendo)
  - Extracción de org_name del mensaje en compras_insumos (`_extract_org_name`)
    para filtrar por organización (ej: "en INPROA SANTONI", "en InproMaiz")
  - `org_name` propagado a `build_supplier_price_comparison()` y `build_product_purchase_history()`
  - System prompts de todos los agentes actualizados para reflejar `docstatus IN ('CO','CL')`
  - Regla PROHIBIDO "no tengo acceso" agregada al system prompt de los 7 agentes
    (antes solo la tenía compras_insumos; finanzas decía "no tengo acceso" para préstamos)
  - Dataset v2.5: 5 nuevos escenarios (352-356), 3 nuevos tipos de error

- **Selector de agentes + verificación de datos (13/Mar 2026)**:
  - Selector de agentes en frontend (tabs) con `agent_name` en ChatRequest
  - Backend: routing directo al agente, bypass orchestrator, validación de permisos
  - Endpoint `GET /api/chat/agents` para listar agentes disponibles
  - Anti-alucinación mejorada: detecta "no tengo acceso" cuando SÍ hay datos (has_data=True)
  - Fix acentos: `build_producer_purchases` y `build_producer_pending_payments` usan `_add_product_search_filter`
  - Desglose por fecha (`por_fecha`) en `build_production_summary` — evita que el LLM invente fechas
  - Script `verify_data.py` — verificación directa contra iDempiere
  - Script `test_agent_queries.py` — 21 preguntas de prueba contra los 7 agentes
  - Dataset v2.6: 364 escenarios (+8 nuevos de verificación)
  - Documentación de monedas por organización (DOL, DoL, Dol, dol, DLA, USA)

### Pendiente:
- Mapeo completo de todas las tablas iDempiere (algunas queries aún en ajuste)
- Tests E2E
- Script de migración datos demo → datos reales
- Sentry (monitoreo de errores)
- WhatsApp (Fase 2, post-lanzamiento)

---

## Patrones de Resiliencia en Agentes (implementado Mar 2026)

Todos los 7 agentes implementan estos 3 patrones de forma consistente:

### 1. Herencia de contexto temporal en follow-ups
Cuando un follow-up no incluye período (mes/fecha), el agente busca en el historial:
```python
# En fetch_data(), después de extract_date_range/extract_month_year:
if not date_from and not date_to and not mes and history:
    for role, content in reversed(history):
        if role != "user": continue
        df, dt = extract_date_range(content)
        if df and dt:
            date_from, date_to = df, dt
            break
        m, a = extract_month_year(content)
        if m:
            mes, anio = m, a
            break
```

### 2. Fallback de período vacío (ventas)
Cuando un período específico no tiene datos, se intenta con el año completo:
```python
if self._is_empty_result(data) and (mes or (date_from and date_to)):
    data_year = build_top_clients(mes=None, anio=anio, ...)
    if not self._is_empty_result(data_year):
        sections.append("**NOTA:** No se encontraron datos para {label}...")
```

### 3. Error handling global en base_agent + fetch_data
- `base_agent.py`: try/except alrededor de `self.fetch_data()` protege TODOS los agentes
- Cada agente: try/except interno en `fetch_data()` con mensaje de error amigable
- Errores de DB se logean con `logger.error()` y se presentan al usuario como mensaje informativo

---

## Datos Históricos Locales (implementado Mar 2026)

Para evitar depender de iDempiere para consultas de datos anteriores a marzo 2026,
se implementó un sistema de caché local:

### Arquitectura
- **Schema `adempiere`** en la DB local de SantoniBot (PostgreSQL 16) con las mismas tablas
- Las queries SQL existentes funcionan **sin cambios** porque usan `adempiere.tabla`
- Routing automático: `_get_session()` en `idempiere_queries.py` decide qué DB usar

### Flujo de datos
```
Consulta del usuario → Agente extrae fechas → _get_session(date_from, date_to, mes, anio)
  → Si fecha < 2026-03-01 y HISTORICAL_DATA_ENABLED=true → DB local (HistoricalSession)
  → Si fecha >= 2026-03-01 o sin fecha → iDempiere en vivo (IdempiereSession)
```

### Tablas copiadas
- **Referencia** (copia completa): ad_org, c_bpartner, m_product, c_currency, hr_employee, etc.
- **Transaccionales** (filtradas por fecha < corte): c_invoice, c_payment, c_order, fact_acct, etc.
- **Snapshots** (estado actual): m_storageonhand, c_bankaccount

### Comandos
```bash
# 1. Aplicar migración (crea schema + tablas)
docker compose exec backend alembic upgrade head

# 2. Extraer datos de iDempiere
docker compose exec backend python scripts/extract_historical_data.py

# 3. Activar en .env
HISTORICAL_DATA_ENABLED=true
HISTORICAL_DATA_CUTOFF=2026-03-01

# 4. Reiniciar
docker compose restart backend
```

### Configuración (.env)
```
HISTORICAL_DATA_ENABLED=false   # Activar después de extraer datos
HISTORICAL_DATA_CUTOFF=2026-03-01  # Fecha de corte
```

### Funciones sin fecha (siempre van a iDempiere)
- `build_overdue_receivables` - cuentas por cobrar actuales
- `build_employee_summary` - plantilla actual
- `build_inventory_stock` - stock actual
- `build_registered_producers` - productores registrados
- `build_producer_pending_payments` - pagos pendientes actuales

---

## CAMBIOS PENDIENTES DE APLICAR (sesión 13/Mar 2026 - check-santoni-chat-9teWt)

Estos cambios fueron desarrollados en el branch `claude/check-santoni-chat-9teWt` pero no se pudieron
mergear limpiamente al servidor (main). Hay que aplicarlos manualmente sobre el código actual del servidor.
El servidor está en main con HEAD = `c987aa3` (branch `claude/general-session-YZXaU`).

### 1. Fix conteo inflado de empleados (1056→701)

**Archivo**: `backend/app/services/idempiere_queries.py` — función `build_employee_summary`

**Problema**: `build_employee_summary` no hacía JOIN a `c_bpartner` y no filtraba `bp.isactive='Y'`.
Personas desactivadas a nivel de partner (c_bpartner.isactive='N') pero con registros activos en
hr_employee se contaban. Resultado: 1,056 en vez de ~701 reales.

**Cambio requerido** en `build_employee_summary()`:
```python
# ANTES:
conditions = ["1=1"]
params: dict = {}
_add_org_filter(conditions, params, org_ids, "e")
where = " AND ".join(conditions)
# Y las queries solo usan: FROM adempiere.hr_employee e

# DESPUÉS:
conditions = ["e.isactive = 'Y'", "bp.isactive = 'Y'"]
params: dict = {}
_add_org_filter(conditions, params, org_ids, "e")
where = " AND ".join(conditions)
bp_join = "JOIN adempiere.c_bpartner bp ON e.c_bpartner_id = bp.c_bpartner_id"
# Agregar {bp_join} después de FROM adempiere.hr_employee e en las 4 sub-queries (totals, by_org, by_dept, by_job)
```

En la query `totals_q`, simplificar:
```python
# ANTES:
f"COUNT(DISTINCT e.c_bpartner_id) AS total, "
f"COUNT(DISTINCT CASE WHEN e.isactive = 'Y' THEN e.c_bpartner_id END) AS activos, "
f"COUNT(DISTINCT CASE WHEN e.isactive = 'N' THEN e.c_bpartner_id END) AS inactivos "
f"FROM adempiere.hr_employee e "

# DESPUÉS:
f"COUNT(DISTINCT e.c_bpartner_id) AS total "
f"FROM adempiere.hr_employee e "
f"{bp_join} "

# Y en el dict de resultado:
totals = {
    "total": row[0] if row else 0,
    "activos": row[0] if row else 0,  # todos son activos por el filtro
    "inactivos": 0,
}
```

En las queries `by_org_q`, `by_dept_q`, `by_job_q`: agregar `{bp_join}` después de `FROM adempiere.hr_employee e`
y cambiar `COUNT(DISTINCT CASE WHEN e.isactive = 'Y' THEN e.c_bpartner_id END) AS activos`
por `COUNT(DISTINCT e.c_bpartner_id) AS activos` (ya están filtrados por el WHERE).

### 2. Filtrado por nombre de organización en agente de producción

**Problema CRÍTICO**: El agente de producción ignoraba el nombre de organización en el mensaje.
Cuando alguien preguntaba "producción de InproMaiz hoy", el agente solo filtraba por `org_ids`
del usuario autenticado. Si el usuario estaba asignado a INPROA SANTONI, mostraba datos de INPROA,
NO de InproMaiz. Esto causó la discrepancia reportada por el personal de InproMaiz.

**Archivo 1**: `backend/app/agents/produccion.py`

Agregar `_ORG_MAP` y `_extract_org_name` (igual que compras_insumos, ventas, compras_productores):
```python
# Después de _INVENTORY_KEYWORDS, agregar:
_ORG_MAP = [
    ("inpromaiz", "InproMaiz"),
    ("inpro maiz", "InproMaiz"),
    ("inproa santoni", "INPROA SANTONI"),
    ("inproa", "INPROA SANTONI"),
    ("santoni service", "Santoni Service"),
    ("agropecuaria", "AGROPECUARIA"),
    ("aga agricola", "AGA AGRICOLA"),
    ("aga agrícola", "AGA AGRICOLA"),
    ("agroinproa", "AGROINPROA"),
    ("inversiones aga", "INVERSIONES AGA"),
]

@classmethod
def _extract_org_name(cls, msg: str) -> str | None:
    msg_lower = msg.lower()
    for kw, val in cls._ORG_MAP:
        if kw in msg_lower:
            return val
    return None
```

En `fetch_data()`:
```python
# Al inicio, después de sections = []:
org_name = self._extract_org_name(message)

# Después de herencia temporal, agregar herencia de org_name:
if not org_name and history:
    for role, content in reversed(history):
        if role != "user":
            continue
        inherited = self._extract_org_name(content)
        if inherited:
            org_name = inherited
            break

# En el label:
label = build_period_label(date_from, date_to, mes, anio)
if org_name:
    label = f"{org_name} - {label}"

# Pasar org_name a las funciones de query:
summary = build_production_summary(
    mes=mes, anio=anio, org_ids=org_ids,
    date_from=date_from, date_to=date_to,
    org_name=org_name,  # NUEVO
)

data = build_production_orders(
    mes=mes, anio=anio, org_ids=org_ids,
    date_from=date_from, date_to=date_to,
    org_name=org_name,  # NUEVO
)
```

**Archivo 2**: `backend/app/services/idempiere_queries.py`

Agregar `org_name: str | None = None` como parámetro a `build_production_summary` y `build_production_orders`.
En ambas funciones, usar `_add_org_name_filter` (ya existe) cuando `org_name` está presente:
```python
# En ambas funciones, después de construir conditions:
_add_org_name_filter(conditions, params, org_name, "io")
if not org_name:
    _add_org_filter(conditions, params, org_ids, "io")
```
Esto da prioridad al nombre de org del mensaje sobre los org_ids del usuario.

**Archivo 3**: `backend/app/services/query_service.py`

Agregar `org_name: str | None = None` a `build_production_summary` y `build_production_orders`,
y propagarlo al llamar las funciones de `idempiere_queries.py`.

### 3. Desglose por organización en verify_data.py

**Archivo**: `backend/scripts/verify_data.py` — función `check_produccion`

Agregar antes de "Top 10 productos movidos":
- Desglose de movimientos de HOY por organización (query con GROUP BY o.name)
- Check específico de InproMaiz para hoy (sin filtro de docstatus para ver borradores)
- Histórico de InproMaiz últimos 7 días

Esto es para diagnóstico — permite ver qué org tiene movimientos cuando hay discrepancias.

---

## Convenciones de Código

- **Idioma del código**: Variables y funciones en inglés, comentarios y mensajes al usuario en español
- **Commits**: En español, formato `tipo: descripción` (feat, fix, test, docs, data, diag)
- **SQL**: Queries parametrizadas, nunca concatenación de strings
- **Agentes**: Heredan de `base_agent.py`, implementan `fetch_data()` y `format_response()`
- **Frontend**: Componentes funcionales React, hooks personalizados, Tailwind para estilos
