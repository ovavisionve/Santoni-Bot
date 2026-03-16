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
│   │   │   ├── cache.py         # Cache de queries
│   │   │   ├── idempiere_permissions.py # Permisos desde roles iDempiere
│   │   │   └── window_capability_map.py # Mapeo ventanas→agentes (31 capabilities)
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
- **INPROA SANTONI C.A.** (principal — procesadora de arroz)
- **InproMaiz C.A** (procesadora de maíz)
- **Santoni Service C.A** (servicios)
- **AGROPECUARIA R.R. C.A.** (agropecuaria)
- **AGA AGRICOLA C.A** (agrícola)
- **AGROINPROA C.A** (agroindustrial)
- **INVERSIONES AGA C.A** (inversiones)
- **Agro Import** (importaciones)

Los agentes filtran por organización cuando el usuario lo especifica.

---

## Monedas en iDempiere

**IMPORTANTE**: En iDempiere de Santoni, cada organización registró su propia entrada de moneda USD
con iso_code diferente. NO son monedas distintas — **todas representan dólares americanos**.

| c_currency_id | iso_code | Organización |
|---------------|----------|-------------|
| 205 | VES | Bolívares (todas las organizaciones) |
| 100 | USD | Dólares (registro base) |
| (varios) | DOL | INPROA SANTONI |
| (varios) | DoL | InproMaiz |
| (varios) | Dol | INVERSIONES AGA |
| (varios) | USA | AGROINPROA |
| (varios) | dol | AGROPECUARIA R.R. |
| (varios) | DLA | Santoni Service |
| (varios) | Dla | Santoni Service (variante) |
| (varios) | US. | Otros |
| (varios) | EUR | Euros (marginal) |

**Cómo se maneja en el código**:
- `_currency_label()` en `idempiere_queries.py` agrupa TODOS los IDs de dólar en una sola etiqueta "USD"
  usando `c_currency_id IN (100,1000000,1000003,1000006,1000008,1000009,1000011,1000013,1000017)`
- `c_currency_id = 205` → "Bs." (VES/Bolívares)
- Cualquier otro → "Otro"
- Los agentes NUNCA deben presentar las monedas por iso_code, siempre usar el CASE de `_currency_label`

---

## Seguridad

- **RBAC**: Roles (usuario, supervisor, administrador) + departamentos (7)
- **Permisos iDempiere**: Ventanas asignadas en iDempiere → capabilities → agentes permitidos
  - `window_capability_map.py`: 31 capabilities mapeadas a 7 agentes
  - `idempiere_permissions.py`: Consulta roles/ventanas del usuario en iDempiere
  - Importación masiva de usuarios con `scripts/import_idempiere_users.py`
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

## Selector de Agentes (reemplaza al Orquestador desde Mar 2026)

El orquestador (clasificador de intención LLM) fue **eliminado** del flujo principal de chat.
Ahora el usuario selecciona el agente directamente desde pestañas en el UI.

### Flujo actual:
1. Usuario ve pestañas de agentes según sus permisos (GET `/api/chat/agents`)
2. Selecciona un agente (ej: "Ventas")
3. Escribe su pregunta
4. El campo `agent_name` en `ChatRequest` envía el agente directamente
5. El backend llama al agente sin pasar por el orquestador
6. Si `agent_name` no viene (API externa), se usa el orquestador como fallback

### Código relevante:
- Backend: `chat.py` → `_VALID_AGENTS`, `_AGENT_INFO`, endpoint `GET /api/chat/agents`
- Frontend: `ChatWindow.tsx` → pestañas de agentes, `page.tsx` → `loadAgents()`
- API: `api.ts` → `getAgents()`, `sendMessage(content, convId, fileId, agentName)`

### Permisos:
- El endpoint `/api/chat/agents` filtra agentes por `user.allowed_departments`
- Si el usuario intenta usar un agente no permitido, retorna 403

---

## Dataset de Entrenamiento

Se mantiene un dataset de escenarios de entrenamiento/validación:
- **Archivo**: `backend/data/training_dataset.json`
- **356+ escenarios** (v2.5+) cubriendo los 7 agentes
- Incluye: pregunta, agente esperado, tipo de consulta, follow-ups
- 78 escenarios de follow-up con herencia de contexto
- Tipos de error rastreados: routing, herencia temporal, fallback sin datos, errores DB,
  docstatus_incompleto, org_name_no_extraido, no_access_text
- Usado para medir confidence score y validación de respuestas

---

## Cuestionarios de Validación

Se crearon cuestionarios para que cada departamento valide las respuestas del bot contra datos reales:
- Archivo: `docs/cuestionario_validacion_agentes.md`
- También existe versión Word: `docs/CUESTIONARIO DE LEVANTAMIENTO Alimentos santoni.docx`
- Los responsables de cada área llenan las preguntas exactas y respuestas esperadas
- Esto permite verificar precisión antes de puesta en producción

---

## Estado Actual del Proyecto (16/Mar/2026)

### Branch de desarrollo: `claude/general-session-YZXaU`
### Tag de seguridad: `pre-keywords-integration` → commit `69575e4` (estado antes de keywords.py)
### HEAD actual: `d7d8130` (incluye fix compras productores: outliers + deduplicación)

### Estado de Validación por Agente (verificado contra `docs/DATOS_VERIFICACION_IDEMPIERE.md` del 13/Mar)

| Agente | Estado | Verificado | Resultado | Notas |
|--------|--------|------------|-----------|-------|
| **Ventas** | ✅ Funcional | Sí | Datos correctos | Top clientes, facturación, cobranza, CxC vencidas |
| **Finanzas** | ✅ Funcional | Sí | Datos correctos | Saldos bancarios 100% exactos, CxC top morosos exactos |
| **RRHH** | ✅ Funcional | Sí | Datos correctos | 702 empleados exacto, nómina enero exacta |
| **Producción** | ✅ Funcional | Sí | Datos plausibles | Proporciones ene vs año cuadran (~40-47%) |
| **Contabilidad** | ❌ ROTO | Sí | 0 movimientos siempre | **BUG CRÍTICO**: ver sección abajo |
| **Compras Insumos** | ⚠️ Parcial | Parcial | Algunos datos, otros alucinados | Funciones con filtro de producto OK, funciones generales tienen problemas |
| **Compras Productores** | ⚠️ En corrección | Sí | Pendiente validar | Filtros ajustados para coincidir con datos verificación iDempiere |

---

### BUG CRÍTICO: Contabilidad devuelve 0 movimientos

**Síntoma**: Todas las consultas de detalle de cuentas (build_account_detail) devuelven 0 movimientos
para cualquier período de 2022-2026, aunque iDempiere tiene miles de movimientos.

**Causa raíz**: El routing de `_get_session()` envía consultas pre-cutoff a la DB LOCAL, pero
`fact_acct` en la DB local **solo tiene datos hasta 2021-09-30** (2.8M filas, rango 2014-06-01 a 2021-09-30).

**Detalle técnico**:
- `HISTORICAL_DATA_ENABLED=True` en producción
- `HISTORICAL_DATA_CUTOFF=2026-03-01`
- `_is_before_cutoff(mes=2, anio=2026)` → `month_end = date(2026,3,1)` → `2026-03-01 <= 2026-03-01` → `True`
- Resultado: Feb 2026 va a DB local → `fact_acct` local no tiene datos de feb 2026 → 0 movimientos
- **Mismo problema para CUALQUIER mes/año entre 2022-01 y 2026-02**

**Evidencia en iDempiere real** (consultada directamente en 192.168.1.73):
- Cuenta 1.01.08.01: **8,522 movimientos** en feb 2026 (iDempiere) vs **0** (bot)
- Cuenta 2.01.02.01: **5,585 movimientos** en 2026 (iDempiere) vs **0** (bot)
- Cuenta 4.01.03.15: **14,689 movimientos** en 2026 (iDempiere) vs **0** (bot)

**Datos de verificación de contabilidad** (SQL directo en iDempiere):
```
TOP 20 CUENTAS CON MÁS MOVIMIENTOS EN 2026:
1.01.08.01  Activo   24,382  CUENTAS POR COBRAR CLIENTES COMERCIALES
1.01.04.02  Activo   16,199  CHEQUES EN TRANSITO
4.01.03.15  Ingreso  14,689  INGRESOS POR VENTA CEREALES (SNACK)
1.01.08.01  Activo   13,192  CUENTAS POR COBRAR CLIENTES
1.01.08.02  Activo   11,686  ANTICIPOS RECIBIDOS POR CLIENTES
1.01.04.01  Activo    9,701  CHEQUES EN TRANSITO
1.02.03.04  Activo    7,775  INVENTARIO PT (EXTRUSORA-CEREAL)
2.01.04.01  Pasivo    7,087  ANTICIPOS RECIBIDOS POR CLIENTES
5.02.04.25  Gasto     7,056  C.V. CEREALES (SNACK)
1.01.08.03  Activo    6,365  DEPOSITOS NO IDENTIFICADOS
2.01.02.01  Pasivo    5,585  CUENTAS POR PAGAR PROVEEDORES
1.01.01.06  Activo    5,468  CAJA CHICA MONEDA EXTRANJERA (VENTAS)
```

**Solución propuesta** (NO implementada aún):
- Opción A: Forzar que `build_accounting_summary` y `build_account_detail` siempre usen
  `IdempiereSession()` directo (igual que `build_inventory_stock`)
- Opción B: Cambiar `<=` por `<` en `_is_before_cutoff` línea 101: `month_end <= cutoff_date` → `month_end < cutoff_date`
  (pero solo arregla feb 2026, no 2022-2025)
- Opción C: Extraer `fact_acct` completo hasta feb 2026 a DB local (pesado, millones de filas)
- **Opción recomendada: A** — es la más simple y segura

---

### Estado de la DB LOCAL (schema `adempiere` en PostgreSQL 16)

| Tabla | Filas | Rango fechas | Estado |
|-------|-------|-------------|--------|
| c_invoice | 449,740 | hasta 2026-02-28 | ✅ OK |
| c_payment | 802,311 | hasta 2026-02-28 | ✅ OK |
| c_order | 278,870 | hasta 2026-02-28 | ✅ OK |
| **fact_acct** | **2,800,000** | **2014-06-01 a 2021-09-30** | **❌ INCOMPLETO** — falta 2022-2026 |
| hr_movement | ? | columna validfrom no existe | ⚠️ Error de esquema |
| m_inout | ? | No verificado | ⚠️ |
| m_production | ? | No verificado | ⚠️ |

---

### Problemas conocidos en Compras Insumos (pendiente de fix)

1. **"Top 10 productos" sin filtro de producto**: Los códigos de producto que muestra el LLM
   a veces son inventados (PMX-VIT-0022, AG-FERT-1120). La query `build_supply_purchases`
   retorna datos reales pero el LLM los reinterpreta/inventa detalles.

2. **"Órdenes de compra pendientes"**: `build_pending_purchase_orders` incluía `docstatus IN ('DR','IP','CO')`
   — las CO son completadas, no pendientes. **Fix aplicado en commit 69575e4**: ahora solo DR/IP.

3. **"Comparación de precios entre proveedores"**: El LLM inventa proveedores que no existen
   (EMPAQUES DEL CARIBE, FLEXOPACK VENEZUELA). Probablemente `build_supplier_price_comparison`
   retorna datos reales pero el LLM los ignora y fabrica.

4. **"Facturas pagadas vs pendientes"**: Routing confuso — "pendientes" matcheaba con
   `_ORDER_KEYWORDS` y ruteaba a órdenes de compra en vez de estado de pago.
   **Fix aplicado en commit 69575e4**: `is_payment` ahora se evalúa antes que `is_orders`.

5. **"Compras en dólares del 2025"**: El LLM dice 1,892 facturas / $8.7M cuando el dato real
   es 14,056 facturas / $33.7M. La query probablemente retorna datos correctos pero el LLM
   los resume incorrectamente. Causa posible: `_format_summary` muestra listas anidadas
   (como `por_moneda`) como blob JSON ilegible para el LLM.

6. **"Proveedores que venden azúcar"**: El LLM inventa proveedores inexistentes
   ("ALIMENTOS AGRÍCOLAS SANTA FE", "DISTRIBUIDORA LA ESTRELLA").

### Correcciones en Compras Productores

1. **Exclusión de empresas internas**: `_add_exclude_internal_orgs_filter()` con 8 empresas del grupo.
2. **Filtro `codigoproductor` eliminado**: Se mantiene solo en `build_registered_producers`.
3. **Filtro `ol.qtyordered > 1`**: Excluye líneas de resumen/total de iDempiere.
4. **Deduplicación de productores**: LATERAL subquery + GROUP BY `bp.c_bpartner_id`.
5. **Diagnóstico detallado**: Ver `DATOS_VERIFICACION_IDEMPIERE.md` §19.

### Módulo de Keywords (`backend/app/agents/keywords.py`) — commit d6eb13f

Se creó un módulo centralizado con 2,200+ keywords en 63 frozensets para detectar
el tipo de consulta del usuario (inventario, órdenes pendientes, comparación de precios, etc.).
Integrado en los 7 agentes. Si causa problemas, revertir con:
```bash
git reset --hard pre-keywords-integration  # Vuelve a commit 69575e4
```

### Pendiente:
- **URGENTE**: Fix contabilidad (fact_acct routing a DB local sin datos)
- **ALTO**: Validar y corregir compras_insumos (alucinaciones del LLM con datos generales)
- **MEDIO**: Compras productores — validar que ~76 guías externas es el número correcto
- Mapeo completo de tablas iDempiere
- Tests E2E
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
- **Transaccionales** (filtradas por fecha < corte): c_invoice, c_payment, c_order, etc.
- **Snapshots** (estado actual): m_storageonhand, c_bankaccount
- **⚠️ fact_acct**: Solo tiene datos 2014-2021. NO tiene datos 2022-2026.
  Esto rompe contabilidad para cualquier consulta post-2021. Ver sección "BUG CRÍTICO" arriba.

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
- `build_inventory_stock` - stock actual (usa `IdempiereSession()` directo)
- `build_registered_producers` - productores registrados
- `build_producer_pending_payments` - pagos pendientes actuales

### ⚠️ Funciones que DEBERÍAN ir a iDempiere pero van a DB local (BUG)
- `build_accounting_summary` - usa `_get_session()` → DB local tiene fact_acct solo hasta 2021
- `build_account_detail` - mismo problema
- **Fix necesario**: Cambiar a `IdempiereSession()` directo, igual que `build_inventory_stock`

---

## Auditoría de Agentes (13/Mar 2026)

Auditoría completa de los 7 agentes + orchestrator + base_agent.

### Resumen por Agente

| Agente | Queries | Herencia temporal | Anti-alucinación | Error handling | org_name | Moneda |
|--------|---------|-------------------|------------------|----------------|----------|--------|
| Ventas | 4 funciones | ✅ Completa | ✅ Fuerte | ✅ try/except | ✅ | ✅ VES/USD |
| Finanzas | 2 funciones | ✅ Completa | ✅ Fuerte | ✅ try/except | ❌ No extrae | N/A (separado en query) |
| Contabilidad | 2 funciones | ✅ Completa + cuenta | ✅ + zero-movement | ✅ try/except | ❌ | ✅ currency_ids |
| RRHH | 7 funciones | ✅ Completa + cargo | ✅ Fuerte | ✅ try/except anidados | ❌ | N/A |
| Producción | 3 funciones | ✅ Completa | ✅ Fuerte | ✅ try/except | ❌ No extrae | N/A |
| Compras Insumos | 6 funciones | ✅ Completa | ✅ Fuerte | ✅ try/except | ✅ _extract_org_name | ✅ _detect_currency |
| Compras Productores | 4 funciones | ✅ Completa + producto | ✅ Fuerte | ✅ try/except anidados | ✅ _extract_org_name | ✅ detect_currency |

### Funciones de Query por Agente

- **Ventas**: `build_top_clients`, `build_sales_summary`, `build_collection_summary`, `build_overdue_receivables`
- **Finanzas**: `build_financial_summary`, `build_overdue_receivables`
- **Contabilidad**: `build_accounting_summary`, `build_account_detail`
- **RRHH**: `build_employee_summary`, `build_employee_list`, `build_birthday_list`, `build_payroll_summary`, `build_attendance_summary`, `build_turnover_summary`, `build_vacation_summary`
- **Producción**: `build_production_summary`, `build_production_orders`, `build_inventory_stock`
- **Compras Insumos**: `build_supply_purchases`, `build_product_purchase_history`, `build_inventory_stock`, `build_pending_purchase_orders`, `build_supplier_price_comparison`, `build_purchase_payment_status`
- **Compras Productores**: `build_producer_purchases`, `build_registered_producers`, `build_producer_pending_payments`, `build_producer_price_analysis`

### Hallazgos Conocidos (no críticos)

1. **`build_inventory_stock`** usa `IdempiereSession()` directo en vez de `_get_session()` — intencional porque inventario es siempre dato actual, nunca histórico
2. **Streaming**: La detección de alucinación post-stream solo logea, no puede reemplazar tokens ya enviados
3. **Conteo de filas** en `base_agent.py`: El filtro de headers es heurístico (busca palabras como "nombre", "codigo"); puede fallar si esas palabras aparecen en datos
4. **`_region_case_sql()`** en ventas: Usa string interpolation pero con datos hardcodeados (no es inyección SQL, pero no es parameterizado)
5. **Currency IDs hardcodeados**: 9 IDs para USD en `date_utils.py` y `compras_insumos.py` — si Santoni agrega nuevos, requiere actualización manual

### Routing del Orchestrator (orden de prioridad)

1. Greetings → `general` (si < 60 chars)
2. Código contable (`\d\.\d{2}\.\d{2}`) → `contabilidad`
3. Keywords en orden: `compras_productores` → `produccion` → `compras_insumos` → `contabilidad` → `finanzas` → `ventas` → `rrhh`
4. Fallback: `last_agent` (follow-up) → keywords genéricos → `general`

---

## Convenciones de Código

- **Idioma del código**: Variables y funciones en inglés, comentarios y mensajes al usuario en español
- **Commits**: En español, formato `tipo: descripción` (feat, fix, test, docs, data, diag)
- **SQL**: Queries parametrizadas, nunca concatenación de strings
- **Agentes**: Heredan de `base_agent.py`, implementan `fetch_data()` y `format_response()`
- **Frontend**: Componentes funcionales React, hooks personalizados, Tailwind para estilos
