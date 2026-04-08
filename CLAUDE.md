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
- **Golden tests framework (Abr 2026)** — ver sección completa abajo.

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

## Golden Tests Framework — Bot vs iDempiere (Abr 2026, EN CURSO)

### Contexto y motivación
Después del trabajo de verificación contra Darwin/Excel (docs/DATOS_VERIFICACION_IDEMPIERE.md, 3334 líneas),
quedó claro que validar contra Excel tiene dos problemas: (1) el Excel puede tener errores, (2) los
scripts SQL del repo habían drifteado del bot (docstatus='CO' solo, grandtotal en lugar de totallines).

**Decisión arquitectónica del usuario (3 pasos):**
1. Fixear scripts SQL existentes para alinear con el bot.
2. Construir un framework de golden tests que ataque el bot por HTTP y compare contra
   queries SQL directas a iDempiere (no Excel).
3. Solo validar meses **históricos cerrados** (enero, febrero, diciembre). La lógica es:
   "como estaría consultando al mismo lugar, no debería fallar."

### Commits de este trabajo
- `85203a3` — fix ground truth bugs: 24 `docstatus='CO'` → `IN ('CO','CL')`, 17
  `grandtotal` → `totallines` en `scripts/verificar_35_preguntas_idempiere.sql` y
  `backend/tests/verify_bot_answers.py`; 3 CxC/CxP migradas a `_OPEN_EXPR`
- `c710f91` — framework inicial (`backend/tests/golden/`): cases.yaml + runner.py + __init__.py;
  pyyaml==6.0.2 agregado a requirements.txt
- `adca5a9` — parser improvements: top-3 candidatos + snippet + filtro de años (1900-2100)
- `128ec06` — parser ISO + venezolano híbrido (detecta último separador con rfind);
  2 casos alineados (facturas bolívares explícito + compras arroz paddy reescrito a c_order)

### Ubicación
```
backend/tests/golden/
├── __init__.py
├── cases.yaml      # 5 casos seed, YAML-driven
└── runner.py       # ~530 líneas, self-contained
```

### Arquitectura del runner
- **BotClient**: login HTTP a `/api/auth/login` (admin/SantoniAdmin2026!) → JWT → POST a `/api/chat/`
- **IdempiereRunner**: psycopg2 con `SET default_transaction_read_only = ON` apuntando a 192.168.1.73
- **Parsers**:
  - `parse_number()`: heurística ISO vs venezolano usando `rfind` del último separador.
    Maneja ISO `15,040,439.64`, venezolano `1.234.567,89`, y formato híbrido que genera el LLM
    con todas comas `2,646,020,028,92`. Validado con 14 edge cases.
  - `extract_all_numbers(text, exclude_years=True)`: filtra enteros 1900-2100 para evitar
    que "2026" del texto contamine la comparación.
  - `parse_markdown_tables()`: pipe tables básicas.
  - `normalize_label()`: lower + sin acentos + whitespace colapsado.
- **Comparadores**: `compare_scalar_exact`, `compare_count_exact`, `compare_ordered_table`.
  Todos imprimen top-3 candidatos + snippet de 280 chars en fail para diagnóstico.
- **CLI**: `--only <id>` y `-v` para verbose.

### Tipos de validación (cases.yaml)
- **valor_exacto**: ground_truth escalar, buscar número en respuesta con tolerancia (default 0.5%)
- **tabla_ordenada**: ground_truth lista ordenada top-N, parsear tabla markdown, comparar
  etiqueta + valor + posición (posicion_estricta opcional)
- **conteo_exacto**: entero, match exacto sin tolerancia

### Casos actuales (5)
| # | id | Validación | Estado |
|---|----|-----------|--------|
| 1 | `ventas_total_neto_ves_feb_2026` | valor_exacto 1% | ✅ ALINEADO |
| 2 | `top_10_vendedores_inproa_usd_feb_2026` | tabla_ordenada 1% | ⚠️ PASSED por suerte — bot hace `_dedupe_salesrep_rows` (tokens ordenados), mi SQL no |
| 3 | `facturas_venta_bolivares_feb_2026` | conteo_exacto | ✅ ALINEADO (reformulado explícito "en bolívares" + `c_currency_id=205`) |
| 4 | `empleados_activos_inproa_santoni` | conteo_exacto | ⚠️ Pendiente: verificar cómo rrhh.py traduce "INPROA SANTONI" → `org_id` via `build_employee_summary(org_ids=...)` |
| 5 | `compras_arroz_paddy_2026_total_kg` | valor_exacto 0.5% | ✅ ALINEADO (reescrito a `c_order` + `qtyordered` + `dateordered`) |

### Comando para correr
```bash
docker compose exec \
  -e BOT_USERNAME=admin \
  -e BOT_PASSWORD='SantoniAdmin2026!' \
  -e IDEMPIERE_PASSWORD='ova2026*' \
  backend python -m tests.golden.runner
```
Flags opcionales: `--only compras_arroz_paddy_2026_total_kg`, `-v`.

Credenciales necesarias:
- **Bot**: `admin` / `SantoniAdmin2026!` (rol administrador, pasa RBAC de todos los agentes)
- **iDempiere**: `ova` / `ova2026*` @ `192.168.1.73:5432` / db `idempiere_produccion`

### Estado de los runs
- **Run 1**: 401 Unauthorized (usuario pasó `<tu_password>` literal).
- **Run 2**: 2/5 PASS, 3/5 FAIL con "2026" como candidato más cercano (bug de años en parser).
- **Run 3**: 2/5 PASS, 3/5 FAIL revelados por top-3 + snippet:
  - Caso 1: parser leía `2,646,020,028,92` como 264,602,002,892 (×100)
  - Caso 3: bot dice 1730 (Bs.), ground truth pedía 3408 (Bs.+USD) — ambigüedad de la pregunta
  - Caso 5: bot dice 12.5M kg, ground truth pedía 15M — el bot usa `c_order`, no `c_invoice`
- **Pendiente**: correr después de los 3 fixes del commit `128ec06` y alinear caso 2 dedup.

### Hallazgo crítico que valida el approach
El framework cazó un error real de modelado en el ground truth: en Santoni, las compras a
productores son **guías de recepción (`c_order`)**, no facturas (`c_invoice`). La guía es
el documento primario; la factura puede tardar o nunca llegar. Este bug existía en los
scripts viejos del repo y nadie lo había detectado. El runner lo encontró en el primer run.

### Auditoría sistemática (interrumpida por context limit)
Pregunta del usuario: **"¿verificaste todas las estructuras de consultas? ¿O lo hiciste por mera intuición?"**

Respuesta honesta: solo se verificó el caso #5 (después de que el framework lo cazó).
Los otros 4 se escribieron por intuición → anti-patrón exacto que estamos tratando de cazar en el bot.

Arrancó auditoría caso por caso leyendo `idempiere_queries.py` y los agentes directamente.
**Completado hasta ahora:**
- `build_sales_summary` (queries.py:506-733): confirma casos 1 y 3 alineados
- `_dedupe_salesrep_rows` (queries.py:455-503): normaliza vendedores por tokens ordenados,
  consolida "ROJAS OBANDO RENEE DE JESUS" vs "RENEE DE JESUS ROJAS OBANDO" → caso 2 necesita mismo dedup
- `build_employee_summary` (queries.py:1784-1867): recibe `org_ids` (NO org_name), usa
  `COUNT(DISTINCT CASE WHEN e.isactive='Y' THEN e.c_bpartner_id END)`
- `ventas.py:490-725`: currency default `[205]`, dispatch logic OK
- `rrhh.py:252`: `summary = build_employee_summary(org_ids=org_ids)` — solo org_ids
- `build_producer_purchases` (queries.py:2582-2684): `c_order` + `qtyordered` + `dateordered`
  con filtro `LOWER(p.name) LIKE :producto`

### Próximos pasos (al retomar)
1. Alinear caso 2: agregar dedup de vendedores en el SQL ground truth (usar mismo algoritmo
   de tokens ordenados que `_dedupe_salesrep_rows` — probablemente con una CTE que normalice
   nombres y haga GROUP BY por el nombre normalizado).
2. Auditar caso 4: verificar cómo `rrhh.py` traduce "INPROA SANTONI" del mensaje del usuario
   al `org_ids` que pasa a `build_employee_summary`. Si usa `ad_org.name ILIKE ...` para
   resolver el id, mi SQL con `o.name ILIKE '%INPROA SANTONI%'` debería matchear.
3. Correr el runner completo (5 casos) y verificar 5/5 PASS.
4. Agregar más casos (siguientes candidatos: CxC por org, cobros por cliente, producción por mes,
   compras insumos por proveedor, saldos bancarios por fecha específica).
5. Agregar doc comment en cada caso de `cases.yaml` que enlace al build_X() específico
   del bot y describa en 1 línea qué rama del código valida (ya está para casos 2, 3, 5).

### Conceptos clave para el próximo chat
- **Currency IDs**: VES=205; USD set=(100, 1000000, 1000003, 1000006, 1000008, 1000009, 1000011, 1000013, 1000017); EUR=1000004 (no mapeado)
- **docstatus**: `IN ('CO', 'CL')` — CO=Completed, CL=Closed (facturas pagadas transicionan a CL)
- **totallines vs grandtotal**: Santoni reporta ventas **sin IVA** (`totallines`); `grandtotal` incluye 16% IVA. Migración hecha en commit de Mar/2026.
- **_OPEN_EXPR**: `(i.grandtotal - COALESCE(alloc.paid, 0))` con LEFT JOIN a `c_allocationline` agregado por invoice — usado para saldos reales de CxC/CxP.
- **Formato numérico venezolano**: `1.234.567,89` (punto=miles, coma=decimal). El LLM a veces escribe con todas comas `2,646,020,028,92` y el parser híbrido lo maneja.

---

## Convenciones de Código

- **Idioma del código**: Variables y funciones en inglés, comentarios y mensajes al usuario en español
- **Commits**: En español, formato `tipo: descripción` (feat, fix, test, docs, data, diag)
- **SQL**: Queries parametrizadas, nunca concatenación de strings
- **Agentes**: Heredan de `base_agent.py`, implementan `fetch_data()` y `format_response()`
- **Frontend**: Componentes funcionales React, hooks personalizados, Tailwind para estilos
