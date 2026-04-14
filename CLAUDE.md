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
│   └── qa/                      # ← Scripts de QA automatizado
│       ├── test_infrastructure.sh
│       ├── test_connectivity.sh
│       ├── test_agents.sh
│       ├── test_resilience.sh
│       └── run_full_qa.sh       # Master script
├── coolify/                     # Coolify deployment config
├── docs/
│   ├── ESTATUS_PROYECTO.md
│   ├── DOCUMENTO_TECNICO.md
│   ├── cuestionario_validacion_agentes.md
│   └── manuales varios
├── docker-compose.yml
├── docker-compose.prod.yml
├── .env.example
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

# Tests unitarios
cd backend && pytest                             # Tests backend (150+)
cd frontend && npm test                          # Tests frontend

# Migraciones
cd backend && alembic upgrade head               # Aplicar migraciones

# Producción (en servidor 192.168.1.26)
cd /opt/santonibot
git pull origin main
docker compose build --no-cache backend frontend && docker compose up -d

# ═══ QA AUTOMATIZADO ═══
cd /opt/santonibot/scripts/qa
chmod +x *.sh
./run_full_qa.sh                                 # QA completo (todas las capas)
./test_infrastructure.sh                         # Solo infraestructura Docker
./test_connectivity.sh                           # Solo conectividad DBs
./test_agents.sh                                 # Solo agentes IA
./test_resilience.sh                             # Solo resiliencia y edge cases
```

---

## Los 7 Agentes + Orquestador

### Flujo de una consulta:
1. Usuario envía mensaje por chat
2. **Orchestrator** clasifica la intención y selecciona el agente correcto
3. El agente especializado genera la query SQL apropiada
4. Se ejecuta contra iDempiere (read-only) via `query_service.py`
5. El agente formatea la respuesta con tablas markdown
6. Se devuelve al usuario con opción de exportar (CSV/Excel/PDF)

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

El ERP maneja múltiples organizaciones (empresas del grupo):
- **INPROA SANTONI** (principal)
- **InproMaiz**
- Otras subsidiarias

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
- **356 escenarios** (v2.5) cubriendo los 7 agentes
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

## Estado Actual del Proyecto (Abril 2026)

### Completado (~95% del alcance Fase 1):
- Backend core completo (FastAPI, auth, RBAC, API endpoints)
- 7 agentes IA + orchestrator funcionando con iDempiere real
- Frontend completo (chat, login, admin panel, exportaciones)
- Docker/deploy configurado y funcionando en servidor
- 150+ tests automatizados + **41 golden tests contra iDempiere (100% PASS)**
- CI/CD con GitHub Actions
- Documentación completa + verificación de schema contra iDempiere real
- Seguridad hardened
- **RRHH migrado a view oficial `lve_empleadosactivos`** (números coinciden con reportes oficiales)

### Trabajo reciente (Feb-Abr 2026):
- **Datos históricos locales (10/Mar 2026)**: Sistema para cachear datos de iDempiere pre-marzo 2026 en DB local
- Conexión exitosa a iDempiere real (queries de nómina, ventas, compras)
- Follow-ups inteligentes con herencia de contexto temporal
- Confidence score + dataset de 355 escenarios (v2.5)
- Separación de compras por moneda (VES/USD)
- Inventario desde m_storageonhand
- Corrección de múltiples bugs reportados por usuarios reales
- Script de pruebas en vivo (65 preguntas, 7 agentes)
- **Fix crítico (Mar 2026)**: Herencia temporal + manejo de errores en los 7 agentes
- **Expansión compras_insumos (10/Mar 2026)**
- **Fix docstatus + org_name en compras (11/Mar 2026)**
- **Sesión 08/Abr/2026** — branch `claude/santoni-fresh-start-XlnT2`:
  - Fix dedup vendedores con `_dedupe_salesrep_rows` (ROJAS OBANDO RENEE = RENEE ROJAS OBANDO)
  - Fix default a VES cuando no se especifica moneda (antes mezclaba Bs + USD → totales contaminados)
  - Flujo de clarificación de organización ambigua (en vez de adivinar)
  - Tabla de vendedores pre-formateada con formato venezolano (el LLM dejó de reordenar columnas)
  - Script de verificación de schema (`scripts/verificar_schema_ventas_santoni.sql`)
  - Framework de golden tests SantoniBot vs iDempiere (`backend/tests/golden/`)
  - Alineación de ground truth SQL con queries del bot (docstatus IN ('CO','CL'), totallines en ventas, allocation JOIN en CxC/CxP)

- **Sesión 09/Abr/2026** — branch `claude/update-claude-md-docker-MbDJK`:
  - **Golden tests: 33/33 PASS = 100%** cubriendo 7/7 agentes
  - Análisis de 1,273 preguntas reales de usuarios (admin + 5 supervisores Santoni)
  - `docs/BUGS_REGISTRY.md`: registro formal de 39 bugs con proceso cross-agent review obligatorio
  - Fix COMP-100/103/104/105: TypeError silencioso en 4 wrappers de query_service.py
  - Fix RRHH-101: "cumplen años" no matcheaba + "no tengo acceso" prohibido en agente general
  - Fix COMP-101: "empaque" removido de keywords de produccion
  - Fix AGRI-103: plurales faltantes en compras_productores
  - Fix PERF-100: `_add_date_filter` usa rangos BETWEEN + `_ALLOC_JOIN` con filtro 3 años
  - Pre-routing rules en orchestrator para conflictos de keywords
  - Parser del runner mejorado para formato venezolano
  - Runner con `--delay` y `--retry-timeout`

- **Sesión 10/Abr/2026** — branch `claude/update-claude-md-docker-MbDJK`:
  - **Golden tests: 41/41 PASS = 100%** (expandido de 33 a 41 casos)
  - **Hallazgo crítico**: los golden tests iniciales eran auto-referenciales (mi SQL copiaba
    el código del bot, ambos podían estar equivocados contra la realidad). Descubierto al
    comparar el bot vs reportes reales de Santoni del log de esalas.
  - **Descubrimiento de 179 views LVE** en iDempiere (Localización Venezuela). Estas views
    son la fuente oficial de los reportes que Santoni usa cada día. El bot las ignoraba
    completamente y consultaba tablas raw. Mapeo completo en `docs/DATOS_VERIFICACION_IDEMPIERE.md`
    sección 21.
  - **Fase 1 RRHH completada**: migradas 3 funciones (`build_employee_summary`,
    `build_birthday_list`, `build_employee_list`) de `hr_employee` raw a `lve_empleadosactivos`.
    Los números ahora coinciden con los reportes oficiales:
    * INPROA SANTONI: 258 (antes 457 — inflaba 77%)
    * InproMaiz: 101 (antes 217 — inflaba 106%)
    * AGA AGRICOLA: 15 (antes 91 — inflaba 507%)
    * Grupo total: 544 (antes 1,056 — inflaba 94%)
  - **Fase 2 Ventas CANCELADA**: investigación reveló que `lve_invoice` es line-level
    (21,792 filas feb 2026 vs 2,110 facturas) y empeoraría los números en vez de mejorarlos.
    `c_invoice` raw ya es correcto para ventas (no tiene multiplicación como `hr_employee`).
  - **Fix VENT-300**: cobranza devolvía datos de VENTAS porque "cobró" (con acento) no
    matcheaba "cobra"/"cobro" (sin acento) en keywords. Agregadas variantes acentuadas.
    Impacto: cualquier supervisor que preguntaba "¿cuánto se cobró?" recibía facturación
    (Bs 2,646M) en vez de cobranza real (Bs 12,105M). Diferencia de 5x.
  - **Fix VENT-400**: "divisas" (sinónimo venezolano de dólares) no matcheaba el regex USD.
    El bot defaulteaba a VES y el LLM etiquetaba como USD, mostrando $503M donde eran
    Bs. 503M. Fix: regex USD ahora incluye `divisas?`. Anti-alucinación: regla nueva en el
    system prompt de ventas que prohíbe etiquetar la moneda según la palabra del usuario
    cuando no coincide con los datos.
  - **Fix parser movimientos producción**: el bot desglosa m_inout por tipo (V+/C-/M+/P+)
    y no presenta total sumado. Golden test ajustado para validar V+ específico.

### Pendiente para cierre Fase 1:
- ~~Verificación SQL ground truth vs bot~~ ✅ COMPLETADO (09/Abr)
- ~~Tests E2E~~ ✅ **CUBIERTO POR GOLDEN TESTS (41 casos, 100% PASS)**
- ~~Fase 1 RRHH (migrar a lve_empleadosactivos)~~ ✅ COMPLETADO (10/Abr)
- ~~Fase 2 Ventas (migrar a lve_invoice)~~ ❌ **CANCELADA** — c_invoice raw ya es correcto
- Filtro de orgs demo en queries USD (datos demo contaminan totales USD)
- Migrar Finanzas a views LVE (`lve_disponibilidadbancaria`, `lve_saldosclientes`, `lve_saldosproveedor`)
- Migrar Compras a views LVE (`lve_saldosproductor`, `lve_inventario_*`)
- Migrar Contabilidad a views LVE (`lve_trialbalance`, `lve_fact_acct`)
- Sentry (monitoreo de errores)
- WhatsApp (Fase 2, post-lanzamiento)

---

## Patrones de Resiliencia en Agentes (implementado Mar 2026)

Todos los 7 agentes implementan estos 3 patrones de forma consistente:

### 1. Herencia de contexto temporal en follow-ups
```python
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

## Decisiones Arquitectónicas del Agente de Ventas (08/Abr/2026)

Sesión de debugging con Darwin que destapó 4 bugs en cascada. Todas las fixes en
`backend/app/agents/ventas.py` y `backend/app/services/idempiere_queries.py`.

### 1. Default a VES cuando no se especifica moneda (CRÍTICO)
**Bug:** Al preguntar "top vendedores feb 2026 en inproa", el bot sumaba Bs + USD como números
pelados y etiquetaba el total como "Bolívares". Matemática verificada:
`Bs 738,438,895.74 + USD 1,008,658.65 + USD 421,741.40 = 739,869,295.79` → exactamente el valor
erróneo que mostraba.

**Fix:** `ventas.py` ahora defaultea a `currency_ids = [205]` (VES) cuando no se menciona moneda.
Usuarios que quieran USD deben decirlo explícitamente ("en dólares").

### 2. Consolidación de vendedores duplicados
**Bug:** "ROJAS OBANDO RENEE DE JESUS" y "RENEE DE JESUS ROJAS OBANDO" aparecían como 2 filas
separadas porque corresponden a 2 registros `ad_user` distintos con el mismo nombre en orden
permutado.

**Fix:** Helper `_dedupe_salesrep_rows()` en `idempiere_queries.py` que fusiona filas cuyos
tokens ordenados coinciden. Aplicado en `build_sales_summary` y `build_sales_orders`.

### 3. Clarificación de organización ambigua (no adivinar)
**Bug:** "inproa" se interpretaba como INPROA SANTONI, pero podía significar el grupo completo.
Hardcoded mapping fue rechazado — decisión del usuario: "mejor que el bot pregunte a mezclar".

**Fix:** `_is_ambiguous_org()` detecta palabras ambiguas ("inproa" sin calificador). Si no hay
org específica en historial ni en mensaje actual, devuelve mensaje pidiendo clarificación
(SANTONI, InproMaiz, AGROINPROA). Si el usuario dice nombre específico → directo sin preguntar.

### 4. Tabla de vendedores pre-formateada (LLM reordenaba columnas)
**Bug:** El LLM recibía 6 columnas similares y mezclaba pairings vendedor↔monto al re-renderizar.
Los valores no cuadraban con las posiciones del ranking.

**Fix:** Helper `_format_vendedores_table()` construye la tabla del lado del agente con:
- Orden por venta neta DESC (consistente con header)
- Columna `#` con posición ya calculada
- Formato venezolano: `503.174.967,88` (punto=miles, coma=decimal)
- Headers explícitos: `Venta Bruta (Bs.)`, `Monto NC (Bs.)`, `Venta Neta (Bs.)`
- Instrucción blindada: "TABLA PRE-FORMATEADA — COPIA EXACTA, NO reordenes"

Este patrón **solo está aplicado a la tabla por vendedor**. Otras tablas (top clientes, por zona,
por región) usan `_format_table` genérico y pueden tener el mismo problema — aplicar el mismo
patrón cuando se detecte evidencia.

---

## Verificación de Schema iDempiere (08/Abr/2026)

Script: `scripts/verificar_schema_ventas_santoni.sql`. Validó 20 tablas, 17 flags críticos y
relaciones FK contra el doc de Santoni. Hallazgos importantes:

### ✅ Confirmado
- Las 20 tablas del doc existen con los flags esperados (`issotrx`, `isreceipt`, `iscustomer`,
  `iskpi`, `docstatus`, `salesrep_id → ad_user`, etc.)
- `c_currency_id = 205` es efectivamente VES (Bolivar Soberano)
- Distribución real de `docstatus` en `c_invoice`: CO (89.7%), RE (9.8%), VO, DR, IN, CL (10),
  IP (2)

### ⚠️ Hallazgos que requieren atención
- **11 monedas activas**: 10 variantes de "dólar" (USD, DOL, USA, Dol, dol, US., DoL, Dla, DLA) +
  Euros (1000004). El bot agrupa todas las variantes dólar como USD correctamente pero **Euros
  caen en categoría "Otro"**. Si Santoni factura en euros con frecuencia, agregar etiqueta EUR.
- **Organizaciones mixtas**: El ERP tiene orgs reales de Santoni (`INPROA SANTONI C.A.`,
  `InproMaiz C.A`, `AGROINPROA C.A`, etc.) mezcladas con **orgs demo de iDempiere** (`HQ`, `Store
  Central`, `Store East/North/South/West`, `Furniture`, `Fertilizer`, `Ocean Equipment`). Sin
  filtro de org explícito, los totales podrían incluir facturas dummy de orgs demo.
- **Usuarios admin en ad_user**: El ranking de vendedores puede incluir a "AdminMaiz" o
  "AgropecuariaAdmin" si tienen facturas asignadas. Considerar filtro por email/dominio.

### Distinción crítica sobre compras
- **Compras a productores (arroz, maíz)** → `c_order` + `ol.qtyordered` + `o.dateordered`. En
  Santoni, la **guía** es el documento real; la factura puede tardar o nunca registrarse.
  (Ver `build_producer_purchases` en `idempiere_queries.py`.)
- **Compras a proveedores de insumos** → `c_invoice`. Flujo distinto, documento final es la
  factura.

---

## Framework de Golden Tests vs iDempiere (08-10/Abr/2026)

Ubicación: `backend/tests/golden/`. Ejecuta preguntas contra el bot vía HTTP y compara con SQL
ground truth ejecutado directamente contra iDempiere.

### Estado actual: **41/41 PASS = 100%** (10/Abr/2026)

| Tipo de validación | Casos | Qué verifica |
|---|---:|---|
| `valor_exacto` | 5 | Un número escalar del bot coincide con SQL ±tolerancia |
| `conteo_exacto` | 6 | Un conteo entero exacto (facturas, empleados, kg) |
| `tabla_ordenada` | 3 | Top N filas coinciden en etiqueta + valor + posición |
| `agente_esperado` | 27 | El orchestrator rutea al agente correcto |
| **Total** | **41** | **7/7 agentes cubiertos** |

### Cobertura de funciones build_* verificadas con datos numéricos: **11/31 (35%)**

Funciones con datos verificados contra iDempiere:
- `build_sales_summary` (ventas totales, facturas, NC, vendedores)
- `build_top_clients` (top 10 clientes VES)
- `build_collection_summary` (cobranza VES)
- `build_employee_summary` (empleados activos — usa `lve_empleadosactivos`)
- `build_birthday_list` (cumpleañeros — usa `lve_empleadosactivos`)
- `build_supply_purchases` (compras insumos totales)
- `build_producer_purchases` (guías de arroz paddy)
- `build_production_summary` (recepciones V+ de m_inout)
- `build_accounting_summary` (asientos contables)
- `build_financial_summary` (saldos bancarios VES)
- `build_inventory_stock` (routing verificado)

### Componentes

1. **`cases.yaml`**: 41 casos con pregunta, SQL ground truth, comparador, tolerancia. Cada caso
   de datos documenta la función del bot que dispara, el campo que verifica, y la correspondencia
   exacta con el código de `idempiere_queries.py`.
2. **`runner.py`**: Cliente HTTP al bot + psycopg2 a iDempiere + parser de tablas markdown +
   parser de números venezolanos (maneja `1.234.567,89` y `1,234,567.89` y `1.730` = 1730) +
   4 comparadores (`valor_exacto`, `conteo_exacto`, `tabla_ordenada`, `agente_esperado`) +
   reporte PASS/FAIL con timings y top-3 candidatos cercanos en fallos.
3. **Flags de estabilidad**: `--delay N` (segundos entre casos), `--retry-timeout` (reintenta
   si timeout), `--only <substring>` (correr solo un caso), `-v` (verbose).

### Ejecución
```bash
cd /opt/santonibot
docker compose exec \
  -e BOT_USERNAME=admin \
  -e BOT_PASSWORD='SantoniAdmin2026!' \
  -e IDEMPIERE_PASSWORD='ova2026*' \
  backend python -m tests.golden.runner --delay 2

# Solo un caso:
... backend python -m tests.golden.runner --only top_10_vendedores
# Verbose (ver respuestas completas del bot):
... backend python -m tests.golden.runner -v
```

### ⚠️ LECCIÓN CRÍTICA: golden tests auto-referenciales (10/Abr/2026)

**Los golden tests escritos leyendo el código del bot son PELIGROSOS.** Si el bot calcula mal
y mi SQL copia esa misma lógica incorrecta, ambos coinciden mientras los dos están equivocados
contra la realidad de iDempiere.

Ejemplo real: `empleados_activos_inproa_santoni` daba 457 (bot) vs 457 (mi SQL) = PASS. Pero
el reporte oficial de Santoni (view `lve_empleadosactivos`) daba **258**. El test pasaba mientras
el bot inflaba 77% el número real. Detectado al comparar con logs reales de la supervisora esalas.

**Corrección del proceso (post 10/Abr/2026):**
- Para funciones donde exista una **view LVE** (Localización Venezuela), el ground truth DEBE
  usar esa view, NO el código del bot.
- Si no existe view LVE, el SQL del ground truth sigue la función del bot PERO se documenta
  como "auto-referencial — pendiente de validación contra reporte oficial de Santoni".
- Las views LVE están catalogadas en `docs/DATOS_VERIFICACION_IDEMPIERE.md` sección 21
  (179 views identificadas, mapeadas por dominio).

### Historial de precisión

| Run | Fecha | PASS | % |
|---|---|---:|---:|
| Tranche 1 baseline | 09/Abr am | 8/10 | 80% |
| Tranche 1 cerrado | 09/Abr am | 10/10 | 100% |
| Tranche 2 baseline | 09/Abr pm | 13/24 | 54% |
| Tranche 2 post-parser | 09/Abr pm | 18/24 | 75% |
| Tranche 2 post-routing | 09/Abr pm | 22/24 | 91.7% |
| Tranche 3 baseline | 09/Abr | 30/34 | 88.2% |
| Tranche 3 post-fixes | 09/Abr | 33/34 | 97.1% |
| Post Fase 1 RRHH LVE | 10/Abr | 39/40 | 97.5% |
| **Post VENT-300/400** | **10/Abr** | **41/41** | **100%** |

---

## Datos Históricos Locales (implementado Mar 2026)

### Arquitectura
- **Schema `adempiere`** en la DB local de SantoniBot (PostgreSQL 16) con las mismas tablas
- Routing automático: `_get_session()` en `idempiere_queries.py` decide qué DB usar

### Flujo de datos
```
Consulta del usuario → Agente extrae fechas → _get_session(date_from, date_to, mes, anio)
  → Si fecha < 2026-03-01 y HISTORICAL_DATA_ENABLED=true → DB local (HistoricalSession)
  → Si fecha >= 2026-03-01 o sin fecha → iDempiere en vivo (IdempiereSession)
```

### Configuración (.env)
```
HISTORICAL_DATA_ENABLED=false   # Activar después de extraer datos
HISTORICAL_DATA_CUTOFF=2026-03-01  # Fecha de corte
```

---

## Convenciones de Código

- **Idioma del código**: Variables y funciones en inglés, comentarios y mensajes al usuario en español
- **Commits**: En español, formato `tipo: descripción` (feat, fix, test, docs, data, diag)
- **SQL**: Queries parametrizadas, nunca concatenación de strings
- **Agentes**: Heredan de `base_agent.py`, implementan `fetch_data()` y `format_response()`
- **Frontend**: Componentes funcionales React, hooks personalizados, Tailwind para estilos

---

## ⚠️ PROCESO OBLIGATORIO — Registro de Bugs y Cross-Agent Review

**Toda sesión donde se detecte o arregle un bug DEBE actualizar `docs/BUGS_REGISTRY.md`.**

### Ciclo obligatorio al arreglar un bug

1. **Abrir ticket** en `docs/BUGS_REGISTRY.md` usando el template de la sección 4 del registro.
   ID del ticket según convención: `VENT-NNN`, `RRHH-NNN`, `FIN-NNN`, `CONT-NNN`, `PRDC-NNN`,
   `COMP-NNN`, `AGRI-NNN`, `ORCH-NNN`, `BASE-NNN`.

2. **Identificar el PATRÓN del bug**, no el síntoma. Ej: síntoma = "ventas suma Bs+USD",
   patrón = "agente no defaultea moneda cuando usuario no especifica".

3. **Cross-agent review OBLIGATORIO**: buscar el mismo patrón en los otros 6 agentes con
   `Grep` / lectura de código. Por cada agente anotar una de:
   - ✅ No aplica (con razón técnica)
   - ⚠️ Aplica parcial (crear ticket separado)
   - 🔴 Mismo patrón (crear ticket + arreglar en el mismo commit)

4. **Aplicar fix** al agente principal + a los afectados encontrados en paso 3.

5. **Mover ticket a "Resueltos"** con fecha, commit hash y resultado del cross-agent review.

6. **Actualizar la tabla resumen** al inicio del registro.

### Por qué es obligatorio

Muchos bugs históricos se arreglaron en un agente sin verificar que el mismo patrón existiera
en los otros. Ejemplo: el default a VES (fix de ventas, 08/Abr/2026) no se aplicó a
`compras_insumos.py` en su momento — y hoy `compras_insumos` sigue mezclando monedas por
default. Ese bug sigue vivo y no lo habíamos detectado hasta el análisis de logs del 09/Abr.

**Si el proceso hubiera existido cuando se arregló ventas, el bug de compras_insumos se habría
cazado en la misma sesión.**

### Referencia rápida

- **Archivo:** `docs/BUGS_REGISTRY.md` (~900 líneas, tabla resumen + sección por agente)
- **Tabla resumen global:** sección 5
- **Template de ticket:** sección 4
- **Proceso completo:** sección 2

Al inicio de cada sesión donde se toque código de agentes, consultar la tabla resumen del
registro para ver qué bugs abiertos hay. **No avanzar con features nuevas si hay bugs 🔴
críticos sin resolver en el agente que se va a tocar.**

---

# ══════════════════════════════════════════════════════════════════
# PROTOCOLO DE QA Y CIERRE DE PROYECTO
# ══════════════════════════════════════════════════════════════════

## Objetivo del QA
Validar TODAS las capas del sistema de forma sistemática para identificar fallas pendientes,
corregirlas, y cerrar la Fase 1. Cada capa tiene un script bash en `scripts/qa/`.

## Criterios de Evaluación
- ✅ **PASS**: Resultado esperado sin errores
- ⚠️ **WARN**: Funciona con degradación (latencia alta, datos incompletos)
- ❌ **FAIL**: Error, timeout, resultado incorrecto, crash

## Ejecución Rápida
```bash
cd /opt/santonibot/scripts/qa && chmod +x *.sh
./run_full_qa.sh              # Todo
./test_infrastructure.sh      # Solo Capa 1
./test_connectivity.sh        # Solo Capa 2
./test_agents.sh              # Solo Capa 3
./test_resilience.sh          # Solo Capa 5
```

---

### CAPA 1: Infraestructura Docker
**Script:** `scripts/qa/test_infrastructure.sh`

| Test | Criterio PASS | Criterio FAIL |
|------|--------------|---------------|
| 5 servicios running | Todos "Up" | Cualquiera "Exit" o ausente |
| RAM backend | < 2GB | > 2GB sostenido |
| CPU servidor | < 80% | > 80% sostenido |
| Disco libre | > 5GB | < 5GB |
| Errores en logs (30min) | 0 ERROR/CRITICAL | Cualquier Traceback |
| Puertos (8000,3000,5432,80) | Todos abiertos | Cualquiera cerrado |
| Reinicios recientes | 0 en últimas 2h | Reinicios inesperados |

---

### CAPA 2: Conectividad de Datos
**Script:** `scripts/qa/test_connectivity.sh`

| Test | Criterio PASS | Criterio FAIL |
|------|--------------|---------------|
| DB local PostgreSQL 16 | Conexión OK | Connection refused |
| iDempiere 192.168.1.73:5432 | Conexión read-only OK | Timeout / auth error |
| Schema adempiere local | Existe con tablas | No existe |
| Registros en tablas clave | > 0 en c_invoice, c_bpartner | 0 registros = datos no cargados |
| Routing histórico (2025) | Usa DB local | Usa iDempiere (error config) |
| Routing actual (2026) | Usa iDempiere | Usa DB local (error config) |
| Latencia query simple | < 2s | > 2s |
| API keys configuradas | No vacías | Vacías o placeholder |
| Alembic migraciones | head = current | Migraciones pendientes |
| ChromaDB | Responde en :8000 | No responde |

---

### CAPA 3: Agentes IA (CORE — el test más importante)
**Script:** `scripts/qa/test_agents.sh`

**Preguntas de prueba:**

| Agente | Pregunta | Respuesta esperada contiene |
|--------|----------|-----------------------------|
| Ventas | "Top 10 clientes por facturación en 2025" | Tabla con nombres y montos |
| Ventas follow-up | "¿Y en dólares?" | Hereda 2025, muestra USD |
| Finanzas | "Saldos bancarios actuales" | Tabla con bancos y saldos |
| Contabilidad | "Balance general diciembre 2025" | Activos, pasivos, patrimonio |
| RRHH | "Cuántos empleados activos hay" | Número > 0 |
| Producción | "Órdenes de producción enero 2026" | Lista de órdenes o "no hay datos" |
| Compras Insumos | "Compras de empaque en 2025" | Montos por proveedor |
| Compras Insumos org | "Compras de empaque en INPROA SANTONI" | Filtrado por org |
| Compras Productores | "Productores registrados" | Lista de productores |

**Criterios por respuesta:**

| Métrica | PASS | WARN | FAIL |
|---------|------|------|------|
| Latencia | < 10s | 10-30s | > 30s |
| "no tengo acceso" | Ausente | - | Presente |
| Datos numéricos | Presentes | - | Ausentes cuando se esperan |
| Confidence score | Presente | - | Ausente |
| Error/Traceback | Ausente | - | Presente |

---

### CAPA 4: Frontend + Auth (manual + curl)
Checklist manual en navegador + validación automatizada de endpoints auth.

---

### CAPA 5: Resiliencia y Edge Cases
**Script:** `scripts/qa/test_resilience.sh`

| Test | Input | Resultado esperado |
|------|-------|--------------------|
| Mensaje sin sentido | "asdfghjkl" | Respuesta amigable, no crash |
| Inyección SQL | "'; DROP TABLE users;--" | Bloqueado, sin ejecución |
| Mensaje vacío | "" | Respuesta controlada |
| Mensaje largo | 5000+ chars | No crash, manejo controlado |
| Rate limit | 31 requests/min | Request #31 → HTTP 429 |
| Concurrencia | 5 requests simultáneos | Respuestas correctas sin mezcla |
| Período sin datos | "ventas marzo 2020" | Fallback o mensaje informativo |

---

### Bugs Conocidos (verificar en cada QA para evitar regresiones)

> **Registro formal completo:** `docs/BUGS_REGISTRY.md` (~1,300 líneas, 39+ tickets con
> causa raíz, cross-agent review, y proceso obligatorio documentado).

| Bug | Fix date | Verificación |
|-----|----------|-------------|
| docstatus='CO' excluía facturas pagadas | 11/Mar/2026 | Query con facturas pagadas → resultados |
| "no tengo acceso" en capabilities | 10/Mar/2026 | Ningún agente dice "no tengo acceso" |
| org_name no se extraía en compras | 11/Mar/2026 | "compras en INPROA SANTONI" filtra OK |
| Herencia temporal rota | Mar/2026 | Follow-up sin fecha hereda período |
| Latencia severa | Mar/2026 | Ningún agente > 30s consistente |
| Default mezclaba VES + USD como "Bs" | 08/Abr/2026 | Consulta sin moneda → solo VES, nunca mezcla |
| Vendedores duplicados (ROJAS vs RENEE) | 08/Abr/2026 | Tokens ordenados → una sola fila consolidada |
| Org ambigua ("inproa") se adivinaba | 08/Abr/2026 | Bot pide clarificación SANTONI/InproMaiz/AGROINPROA |
| LLM reordenaba tabla de vendedores | 08/Abr/2026 | Pre-format en backend, LLM solo copia verbatim |
| `grandtotal` incluía IVA en totales ventas | 08/Abr/2026 | Ventas usan `totallines` (sin IVA), compras sí `grandtotal` |
| TypeError en 4 wrappers query_service (COMP-100/103/104/105) | 09/Abr/2026 | Cross-agent review cazó 3 extras |
| "cumplen años" no matcheaba rrhh (RRHH-101) | 09/Abr/2026 | Variantes verbales en keywords |
| "empaque" ruteaba a produccion (COMP-101) | 09/Abr/2026 | Removido de keywords produccion |
| "Compras de maíz" → compras_insumos (AGRI-103) | 09/Abr/2026 | Plurales en compras_productores |
| EXTRACT() en filtros impedía uso de índices (PERF-100) | 09/Abr/2026 | Rangos BETWEEN + _ALLOC_JOIN 3 años |
| "no tengo acceso" en agente general | 09/Abr/2026 | Frase prohibida en _handle_general + _stream_general |
| **Empleados activos 3x inflados (RRHH-200)** | **10/Abr/2026** | **Migrado a `lve_empleadosactivos`. INPROA: 258 no 457** |
| **Cobranza respondía facturación (VENT-300)** | **10/Abr/2026** | **"cobró" con acento → keywords cobranza. Bs 12,105M no 2,646M** |
| **"divisas" no matcheaba USD (VENT-400)** | **10/Abr/2026** | **Regex USD incluye `divisas?`. Anti-alucinación en prompt** |

---

### Procedimiento de Cierre

1. `./run_full_qa.sh` → genera `qa_report_FECHA.txt`
2. Corregir cada ❌ FAIL con commit documentado
3. Re-testear capa afectada
4. Actualizar `docs/ESTATUS_PROYECTO.md`
5. `git tag v1.0-qa-passed`
6. Backup DB + presentar reporte al cliente
