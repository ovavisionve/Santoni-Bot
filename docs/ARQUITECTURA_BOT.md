# Arquitectura SantoniBot — Mapa Completo del Código

> Documento vivo. Actualizar cada vez que se modifique el flujo.
> Última actualización: 21/Abr/2026

---

## FASE 1: Flujo General (Pregunta → Respuesta)

### Pipeline completo

```
┌─────────────────────────────────────────────────────────────────┐
│                        USUARIO                                  │
│  "¿Cuántos supervisores tiene INPROA SANTONI?"                 │
└─────────────────────┬───────────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────────┐
│  1. FRONTEND (Next.js)                                          │
│     app/chat/page.tsx → ChatWindow.tsx                          │
│     - Usuario selecciona agente (pestaña: RRHH)                │
│     - Envía: POST /api/chat/ {message, agent_name: "rrhh"}    │
└─────────────────────┬───────────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────────┐
│  2. API ENDPOINT                                                │
│     backend/app/api/routes/chat.py                              │
│                                                                 │
│     @router.post("/")  → send_message()                        │
│     @router.post("/stream") → stream_message()                 │
│                                                                 │
│     ┌─ Validación ──────────────────────────────────────┐      │
│     │ • agent_name REQUERIDO (si no → 400)              │      │
│     │ • agent_name in _VALID_AGENTS (7 agentes)         │      │
│     │ • agent_name in user.allowed_departments (RBAC)   │      │
│     └───────────────────────────────────────────────────┘      │
│                                                                 │
│     Guarda mensaje en DB → obtiene historial → llama agente    │
└─────────────────────┬───────────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────────┐
│  3. AGENTE (ej: RRHHAgent)                                      │
│     backend/app/agents/rrhh.py                                  │
│     Hereda de: base_agent.py → BaseAgent                       │
│                                                                 │
│     ┌─ BaseAgent.process() ─────────────────────────────┐      │
│     │                                                    │      │
│     │  a) _build_messages(message, history, org_ids)     │      │
│     │     ├─ Construye system prompt (instrucciones)     │      │
│     │     ├─ Llama fetch_data() del agente               │      │
│     │     ├─ Si fetch_data retorna datos:                │      │
│     │     │   → Arma bloque "DATOS REALES DE LA BD"     │      │
│     │     │   → has_data = True                          │      │
│     │     └─ Si fetch_data retorna None:                 │      │
│     │         → has_data = False                         │      │
│     │         → Intenta sql_direct fallback              │      │
│     │                                                    │      │
│     │  b) Si has_data = False Y sql_direct falla:        │      │
│     │     → Retorna HALLUCINATION_REPLACEMENT            │      │
│     │     → NO llama al LLM                             │      │
│     │                                                    │      │
│     │  c) Si has_data = True:                            │      │
│     │     → Envía messages[] al LLM                     │      │
│     │     → LLM formatea la respuesta                   │      │
│     │     → Post-check: detect_hallucination()          │      │
│     │     → Retorna response dict                       │      │
│     └────────────────────────────────────────────────────┘      │
└─────────────────────┬───────────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────────┐
│  4. FETCH_DATA (dentro del agente)                              │
│     Cada agente implementa su propio fetch_data()               │
│                                                                 │
│     ┌─ Extracción de parámetros ────────────────────────┐      │
│     │  • mes, anio    ← date_utils.extract_month_year() │      │
│     │  • date_from/to ← date_utils.extract_date_range() │      │
│     │  • org_name     ← _extract_org_name()             │      │
│     │  • currency_ids ← detect_currency()               │      │
│     │  • cargo_search ← _extract_cargo_search() [RRHH]  │      │
│     │  • name_search  ← _extract_name_search() [RRHH]   │      │
│     │  • product_search ← keywords [Ventas]             │      │
│     │  • account_code ← regex [Contabilidad]            │      │
│     │  • zona         ← _extract_zona() [Ventas]        │      │
│     └───────────────────────────────────────────────────┘      │
│                                                                 │
│     ┌─ Routing por query_type ──────────────────────────┐      │
│     │  Basado en keywords.py:                           │      │
│     │  "top clientes"    → build_top_clients()          │      │
│     │  "cobranza"        → build_collection_summary()   │      │
│     │  "ausentismo"      → build_attendance_summary()   │      │
│     │  etc.                                              │      │
│     └───────────────────────────────────────────────────┘      │
│                                                                 │
│     ┌─ Llamada a query_service ─────────────────────────┐      │
│     │  query_service.build_X(params)                    │      │
│     │    → Si APP_ENV=production:                       │      │
│     │        idempiere_queries.build_X(params)          │      │
│     │          → IdempiereSession() (192.168.1.73)      │      │
│     │          → SQL contra adempiere schema            │      │
│     │          → Retorna dict con datos reales          │      │
│     │    → Si APP_ENV=development:                      │      │
│     │        demo tables (datos fake)                   │      │
│     └───────────────────────────────────────────────────┘      │
│                                                                 │
│     Retorna: string con secciones markdown formateadas          │
│     (## Título\n### Totales\n| tabla | datos |)                │
└─────────────────────┬───────────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────────┐
│  5. LLM (DeepSeek vía OpenRouter)                               │
│     backend/app/services/llm_factory.py                         │
│                                                                 │
│     Recibe:                                                     │
│     ┌─ SystemMessage ──────────────────────────────────┐       │
│     │ • Prompt del agente (quién soy, qué hago)        │       │
│     │ • Fecha/hora actual                               │       │
│     │ • Instrucciones anti-invención                    │       │
│     │ • Reglas de conteo y totales                      │       │
│     ├─ SystemMessage ──────────────────────────────────┤       │
│     │ • "DATOS REALES DE LA BASE DE DATOS"             │       │
│     │ • "DEBES presentar TODAS las secciones"          │       │
│     │ • Datos de fetch_data (tablas, totales, listas)  │       │
│     ├─ Historial (HumanMessage/AIMessage × 20)  ──────┤       │
│     ├─ HumanMessage (pregunta actual del usuario) ─────┤       │
│     └──────────────────────────────────────────────────┘       │
│                                                                 │
│     Responde: texto formateado en markdown                     │
└─────────────────────┬───────────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────────┐
│  6. RESPUESTA AL USUARIO                                        │
│                                                                 │
│     chat.py guarda en DB → retorna JSON:                       │
│     {                                                           │
│       "message": "## Supervisores\n| Nombre | Cargo |...",     │
│       "message_id": 123,                                       │
│       "conversation_id": 45                                    │
│     }                                                           │
│                                                                 │
│     Frontend renderiza markdown → tabla → usuario ve datos     │
└─────────────────────────────────────────────────────────────────┘
```

### Archivos clave por capa

| Capa | Archivo | Líneas | Función |
|------|---------|--------|---------|
| API | `api/routes/chat.py` | ~770 | Endpoint POST /, stream, validación |
| Base | `agents/base_agent.py` | ~730 | _build_messages, process, stream, hallucination |
| Agentes | `agents/ventas.py` | ~510 | fetch_data ventas |
| | `agents/rrhh.py` | ~560 | fetch_data RRHH |
| | `agents/contabilidad.py` | ~500 | fetch_data contabilidad |
| | `agents/finanzas.py` | ~280 | fetch_data finanzas |
| | `agents/produccion.py` | ~350 | fetch_data producción |
| | `agents/compras_insumos.py` | ~690 | fetch_data compras insumos |
| | `agents/compras_productores.py` | ~350 | fetch_data compras productores |
| Keywords | `agents/keywords.py` | ~1220 | 63 frozensets de keywords |
| Fechas | `agents/date_utils.py` | ~300 | extract_month_year, extract_date_range |
| Wrapper | `services/query_service.py` | ~1450 | Routing demo/producción |
| SQL | `services/idempiere_queries.py` | ~4200 | Queries SQL reales |
| LLM | `services/llm_factory.py` | ~200 | Crea instancia del LLM |
| SQL Direct | `services/sql_direct/` | ~800 | SQL dinámico (fallback) |
| DB | `database.py` | ~100 | IdempiereSession, SessionLocal |

### Flujo de decisión: ¿Qué pasa cuando no hay datos?

```
fetch_data() retorna datos?
  │
  ├─ SÍ (string > 50 chars) → has_data = True
  │   └─ LLM recibe datos → formatea → respuesta
  │
  └─ NO (None o vacío) → has_data = False
      │
      ├─ sql_direct fallback → ¿Genera SQL válido?
      │   ├─ SÍ → retorna resultado de sql_direct
      │   └─ NO → continúa
      │
      └─ Retorna HALLUCINATION_REPLACEMENT
          "No se encontraron datos para tu consulta..."
          (NO llama al LLM — evita inventar datos)
```

---

---

## FASE 2: Extracción de Parámetros

Cada pregunta del usuario se descompone en parámetros que filtran las queries SQL.
Todo vive en `agents/date_utils.py` + métodos de cada agente.

### Mapa completo de extracción

```
"¿Cuántos supervisores tiene INPROA SANTONI en enero 2026?"
     │           │              │              │     │
     │           │              │              │     └─── anio=2026
     │           │              │              └───────── mes=1
     │           │              └──────────────────────── org_name="INPROA"
     │           └─────────────────────────────────────── cargo_search="supervisor"
     └─────────────────────────────────────────────────── query_type="cargo"
```

### 1. FECHAS (todos los agentes)

**Archivo:** `agents/date_utils.py`
**Funciones:** `extract_month_year()`, `extract_date_range()`

```
extract_month_year("nómina de febrero 2026")
  → mes=2, anio=2026

extract_date_range("ventas del 15 de diciembre 2024 al 15 de enero 2025")
  → ('2024-12-15', '2025-01-15')
```

**Patrones soportados (en orden de evaluación):**

| # | Patrón | Ejemplo | Resultado |
|---|--------|---------|-----------|
| 1 | `desde [MES] [AÑO] a la fecha` | "desde enero 2025 hasta hoy" | 2025-01-01 → hoy |
| 2 | `desde [AÑO] a la fecha` | "desde 2024 hasta hoy" | 2024-01-01 → hoy |
| 3 | `del [AÑO] al [AÑO]` | "del 2024 al 2026" | 2024-01-01 → 2026-12-31 |
| 4 | `[MES] [AÑO] a [MES] [AÑO]` | "junio 2025 a enero 2026" | 2025-06-01 → 2026-01-31 |
| 5 | `[DD] de [MES] [AÑO] al [DD] de [MES] [AÑO]` | "15 de dic 2024 al 15 de ene 2025" | 2024-12-15 → 2025-01-15 |
| 6 | `[MES], [MES] y [MES] [AÑO]` (listado) | "sept, oct y nov 2025" | 2025-09-01 → 2025-11-30 |
| 7 | `[DD/MM/YYYY] al [DD/MM/YYYY]` | "01/03/2026 al 09/03/2026" | 2026-03-01 → 2026-03-09 |
| 8 | `hoy` | "ventas de hoy" | hoy → hoy |
| 9 | `mes actual` / `este mes` | "cobranza del mes actual" | 1er día mes → hoy |
| 10 | `mes pasado` | "nómina del mes pasado" | mes anterior completo |

**Palabras clave de meses:**
```
MESES_MAP = {
    "enero":1, "febrero":2, "marzo":3, "abril":4, "mayo":5,
    "junio":6, "julio":7, "agosto":8, "septiembre":9, "setiembre":9,
    "octubre":10, "noviembre":11, "diciembre":12
}
```

**⚠️ Regla importante:** Si "al" está en el mensaje, el patrón #6 (listado de meses) NO aplica — se asume que es un rango, no una lista.

### 2. ORGANIZACIÓN (todos los agentes)

**Función:** `_extract_org_name()` en cada agente
**Método:** Busca substrings de las 7 organizaciones de Santoni

```python
_ORG_PATTERNS = [
    ("inproa", "INPROA"),      # matchea "inproa santoni", "INPROA"
    ("inpromaiz", "InproMaiz"),
    ("santoni service", "Santoni Service"),
    ("agropecuaria", "AGROPECUARIA R.R."),
    ("agroinproa", "AGROINPROA"),
    ("inversiones aga", "INVERSIONES AGA"),
    ("agro import", "Agro Import"),
]
```

**Cómo se usa en SQL:**
```sql
-- _add_org_name_filter() en idempiere_queries.py
WHERE i.ad_org_id IN (
    SELECT ad_org_id FROM adempiere.ad_org
    WHERE name ILIKE '%INPROA%'
)
```

### 3. CARGO / PUESTO (RRHH)

**Función:** `_extract_cargo_search()` en `agents/rrhh.py`
**Método:** Extrae de la ESTRUCTURA de la oración (no keywords hardcoded)

```
Patrones:
  "cuántos [CARGO] hay/tiene"     → extract CARGO
  "quiénes son los [CARGO]"       → extract CARGO
  "lista de [CARGO]"              → extract CARGO
  "cargo de [X]" / "puesto de [X]" → extract X
```

**Transformaciones aplicadas:**
1. De-pluralización española: `supervisores → supervisor`, `gerentes → gerente`
2. Strip acentos: `mecánico → mecanico` (iDempiere no tiene tildes)

**Cómo se usa en SQL:**
```sql
-- build_employee_list(cargo_search='supervisor')
WHERE j.name ILIKE '%supervisor%'  -- j = hr_job
```

### 4. NOMBRE DE EMPLEADO (RRHH)

**Función:** `_extract_name_search()` en `agents/rrhh.py`
**Triggers:** "apellido X", "nombre X", "se llama X", "buscar X"

```
"Buscar empleado de apellido Rodríguez"
  → name_search = "Rodriguez"  (acentos removidos)
```

**Transformaciones:**
- Strip acentos: `á→a, é→e, í→i, ó→o, ú→u, ñ→n`

**Cómo se usa en SQL:**
```sql
-- build_employee_list(name_search='Rodriguez')
WHERE bp.name ILIKE '%Rodriguez%'
```

### 5. MONEDA (Ventas, Compras)

**Función:** `detect_currency()` en `agents/date_utils.py`
**Detección:**

| Palabra clave | currency_ids resultado |
|---------------|----------------------|
| "dólares", "USD", "en dólares" | [100,1000000,1000003,1000006,1000008,1000009,1000011,1000013,1000017] |
| "bolívares", "Bs", "en bolívares" | [205] |
| (nada) | None → todas las monedas |

**Cómo se usa en SQL:**
```sql
-- _add_currency_filter()
WHERE i.c_currency_id IN (100, 1000000, ...)  -- USD
WHERE i.c_currency_id = 205                    -- VES
```

### 6. PRODUCTO (Ventas)

**Función:** Detección en `_detect_query_type()` de `agents/ventas.py`
**Keywords:** "harina", "arroz", "cereal", "avena", "empaque", "producto", "categoría"

```
"¿Cuánto se vendió de harinas en febrero 2026?"
  → query_type = "producto"
  → product_search = "harina"
```

**⚠️ Cuidado:** "maíz" como keyword standalone usa `\b` word boundary para no matchear dentro de "InproMaiz" (nombre de org).

**Cómo se usa en SQL:**
```sql
-- _add_product_search_filter() en idempiere_queries.py
-- De-pluraliza y normaliza: "harinas" → "harina"
WHERE (p.name ILIKE '%harina%' OR p.value ILIKE '%harina%')
```

### 7. CUENTA CONTABLE (Contabilidad)

**Función:** Regex en `agents/contabilidad.py`
**Formatos aceptados:**

| Input del usuario | Normalización | SQL |
|-------------------|--------------|-----|
| `1.01.01.01` | tal cual | `WHERE ev.value = '1.01.01.01'` |
| `5.01` | tal cual | `WHERE ev.value = '5.01'` |
| `1101` (sin puntos) | `→ '1%1%01'` | `WHERE ev.value LIKE '1%1%01'` |

**Regex principal:** `r'\b(\d\.\d{2}(?:\.\d{2}){1,3})\b'`
**Regex compacto:** `r'\bcuenta\s+(\d{4,6})\b'`

### 8. ZONA / REGIÓN (Ventas)

**Función:** `_extract_zona()` en `agents/ventas.py`
**Keywords:** Matchea nombres de zonas de iDempiere (c_salesregion)

```
"Ventas en la zona de los Llanos"
  → zona = "Llanos"
```

**Cómo se usa en SQL:**
```sql
-- En build_sales_summary
WHERE cz.zona_name ILIKE '%Llanos%'
```

### 9. VENDEDOR / DISTRIBUIDOR (Ventas)

**Función:** `_extract_vendedor()` en `agents/ventas.py`

```
"Ventas del distribuidor Carlos Matias"
  → vendedor = "Carlos Matias"
```

**Cómo se usa en SQL:**
```sql
WHERE sr.name ILIKE '%Carlos Matias%'  -- sr = c_bpartner (salesrep)
```

### 10. TIPO DE DOCUMENTO (Ventas)

**Función:** `_extract_doctype()` en `agents/ventas.py`
**Detección:** Letra de serie → nombre de doctype en iDempiere

| Usuario dice | doctype_name |
|-------------|-------------|
| "serie A", "factura A" | "Factura Serie A" |
| "serie B" | "Factura Serie B" |
| "nota de crédito" | "Nota de Crédito" |

### Diagrama resumen de extracción

```
                    PREGUNTA DEL USUARIO
                           │
          ┌────────────────┼────────────────┐
          │                │                │
     date_utils.py    agente.py      keywords.py
          │                │                │
    ┌─────┴─────┐    ┌────┴────┐     ┌────┴────┐
    │ mes/anio  │    │org_name │     │query_   │
    │ date_from │    │cargo    │     │type     │
    │ date_to   │    │nombre   │     │(cuál    │
    │ currency  │    │zona     │     │build_*  │
    └─────┬─────┘    │vendedor │     │llamar)  │
          │          │producto │     └────┬────┘
          │          │cuenta   │          │
          │          │doctype  │          │
          │          └────┬────┘          │
          │               │               │
          └───────┬───────┘               │
                  │                       │
                  ▼                       ▼
          query_service.build_*(params)
                  │
                  ▼
          idempiere_queries.build_*(params)
                  │
                  ▼
              SQL → iDempiere
```

---

---

## FASE 3: Mapa de Agentes (7 agentes × funciones)

### Resumen de capacidades

| Agente | Archivo | query_types | build_* que llama | Parámetros que extrae |
|--------|---------|-------------|-------------------|-----------------------|
| **Ventas** | ventas.py (510L) | 8 | 11 funciones | fecha, org, moneda, zona, vendedor, producto, doctype |
| **RRHH** | rrhh.py (560L) | 6 | 10 funciones | fecha, org, cargo, nombre |
| **Contabilidad** | contabilidad.py (500L) | 2 | 2 funciones | fecha, org, cuenta, moneda, tipo_cuenta |
| **Finanzas** | finanzas.py (280L) | 3 | 4 funciones | fecha, org |
| **Producción** | produccion.py (350L) | 3 | 5 funciones | fecha, org, producto |
| **Compras Insumos** | compras_insumos.py (690L) | 5 | 6 funciones | fecha, org, moneda, producto, proveedor |
| **Compras Productores** | compras_productores.py (350L) | 4 | 4 funciones | fecha, org, producto |

---

### VENTAS (ventas.py)

```
_detect_query_type(message) → query_type:
  ┌──────────────────────────────────────────────────────────────┐
  │ VENTAS_CLIENTES  → "top"              (ranking clientes)    │
  │ "activo/inactivo" → "cliente_status"   (clientes act/inact) │
  │ "producto/harina" → "producto"         (ventas por producto) │
  │ VENTAS_COBRANZA  → "cobranza"         (cobros recibidos)    │
  │ VENTAS_CXC       → "vencidas"         (CxC morosos)         │
  │ "visita"         → "visitas"          (visitas a clientes)   │
  │ "meta/presupuesto" → "metas"          (metas vs real)       │
  │ "produjo+vendió" → "ventas_vs_prod"   (cruce ventas/prod)   │
  │ VENTAS_FACTURACION → "ventas"         (resumen general)      │
  │ VENTAS_ZONAS     → "region"           (por zona/región)      │
  │ (ninguno)        → "ventas"           (default: resumen)     │
  └──────────────────────────────────────────────────────────────┘
```

**Flujo fetch_data:**
```
query_type?
  │
  ├─ "producto"        → build_sales_by_product(product_search, mes, anio, org)
  ├─ "visitas"         → build_client_visits(mes, anio, org)
  ├─ "metas"           → build_budget_comparison(mes, anio)
  ├─ "ventas_vs_prod"  → build_production_vs_sales(mes, anio)
  ├─ "cliente_status"  → build_client_status(org_name, anio)
  ├─ "top"             → build_top_clients(limit, zona, vendedor, mes, anio, org, currency, doctype)
  │                      + fallback año completo si período vacío
  ├─ "cobranza"        → build_collection_summary(zona, vendedor, mes, anio, org)
  ├─ "vencidas"        → build_top_delinquent_clients(org) + build_overdue_receivables(org)
  └─ "ventas"/"region" → build_sales_summary(zona, vendedor, mes, anio, org, currency, doctype)
                          + fallback año completo si período vacío
                          + build_top_clients si doctype especificado
```

**⚠️ Orden importa en _detect_query_type:**
1. `VENTAS_CLIENTES` se evalúa ANTES de `producto` (para que "Top clientes InproMaiz" no matchee "maiz")
2. `producto` standalone keywords usan `\b` word boundary
3. `VENTAS_FACTURACION` es el default fallback

---

### RRHH (rrhh.py)

```
Routing por keywords (NO usa _detect_query_type, usa matches_any directo):
  ┌──────────────────────────────────────────────────────────────┐
  │ PRIORIDAD: cargo_search / name_search (if/elif)              │
  │                                                              │
  │ name_search?    → build_employee_list(name_search)           │
  │ cargo_search?   → build_employee_list(cargo_search)          │
  │ RRHH_EMPLEADOS  → build_employee_list() (general)            │
  │                                                              │
  │ SECCIONES ADICIONALES (if, no elif — pueden combinarse):     │
  │ RRHH_CUMPLEANOS → build_birthday_list(mes, org)              │
  │ RRHH_NOMINA     → build_payroll_summary(mes, anio)           │
  │ RRHH_AUSENTISMO → build_attendance_summary(mes, anio)        │
  │                   O build_daily_attendance() si "hoy"        │
  │ RRHH_VACACIONES → build_vacation_summary(mes, anio, org)     │
  │ RRHH_ROTACION   → build_turnover_summary(anio)               │
  │                   O build_new_hires() si "ingresaron"        │
  │ "provisiones"   → build_payroll_provisions(mes, anio)        │
  │ "calidad contrat" → build_new_hires(anio, mes)               │
  └──────────────────────────────────────────────────────────────┘
```

**⚠️ Orden de secciones en respuesta:**
- Para cumpleaños/ausentismo/nómina: datos específicos VAN PRIMERO, employee summary al final como contexto
- Para queries generales de empleados: employee summary va primero
- Razón: el LLM ignora secciones que van después de 2000+ chars

**⚠️ Transformaciones en RRHH:**
- `cargo_search`: de-pluralización (`supervisores→supervisor`) + strip acentos (`mecánico→mecanico`)
- `name_search`: strip acentos (`Rodríguez→Rodriguez`)

---

### CONTABILIDAD (contabilidad.py)

```
Routing:
  ┌──────────────────────────────────────────────────────────────┐
  │ account_code detectado?                                      │
  │  ├─ SÍ (ej: "1.01.01" o "1101")                            │
  │  │   → build_account_detail(code, mes/anio o date_range)    │
  │  │                                                           │
  │  └─ NO → Resumen general                                    │
  │      → _detect_account_types(message):                       │
  │         "gastos"      → account_types=['E']                  │
  │         "ingresos"    → account_types=['R']                  │
  │         "activos"     → account_types=['A']                  │
  │         "pasivos"     → account_types=['L']                  │
  │         "patrimonio"  → account_types=['O']                  │
  │         "estado resultados" → account_types=['R','E']        │
  │      → build_accounting_summary(mes, anio, account_types)    │
  └──────────────────────────────────────────────────────────────┘
```

**⚠️ Cuenta compacta:** "1101" → `_normalize_account_code()` → "1%1%01" → SQL LIKE

---

### FINANZAS (finanzas.py)

```
Routing por keywords:
  ┌──────────────────────────────────────────────────────────────┐
  │ FINANZAS_CXC     → build_overdue_receivables()              │
  │ "préstamo/loan"  → build_loan_balances(org)                 │
  │ "cobros y pagos" → build_cobros_pagos_summary(mes, anio)    │
  │ (default)        → build_financial_summary(mes, anio, org)   │
  │                    (saldos bancarios + CxC + CxP)            │
  └──────────────────────────────────────────────────────────────┘
```

---

### PRODUCCIÓN (produccion.py)

```
Routing por keywords:
  ┌──────────────────────────────────────────────────────────────┐
  │ "inventario/stock" → build_inventory_stock(org, producto)    │
  │ "BOM/receta"       → build_bom_info()                       │
  │ "movimiento"       → build_warehouse_movements(mes, anio)    │
  │ "producción/runs"  → build_production_runs(mes, anio) +      │
  │                      build_production_summary(mes, anio) +    │
  │                      build_production_orders(mes, anio)       │
  │ (default)          → build_production_summary(mes, anio)      │
  └──────────────────────────────────────────────────────────────┘
```

---

### COMPRAS INSUMOS (compras_insumos.py)

```
Routing por keywords:
  ┌──────────────────────────────────────────────────────────────┐
  │ "inventario"       → build_inventory_stock(producto)         │
  │ "pagos/estado pago" → build_purchase_payment_status(mes,anio)│
  │ "pendiente/orden"  → build_pending_purchase_orders(mes, anio)│
  │ "comparar precios" → build_supplier_price_comparison(prod)   │
  │ "proveedor+prod"   → build_product_purchase_history(prod)    │
  │ (default)          → build_supply_purchases(mes, anio, org)  │
  └──────────────────────────────────────────────────────────────┘
```

---

### COMPRAS PRODUCTORES (compras_productores.py)

```
Routing por _SECTION_KW_MAP:
  ┌──────────────────────────────────────────────────────────────┐
  │ "productores"      → build_registered_producers(org)         │
  │ "pendientes/pagos" → build_producer_pending_payments(org)    │
  │ "precios"          → build_producer_price_analysis(mes, anio)│
  │ (default)          → build_producer_purchases(mes, anio, org)│
  └──────────────────────────────────────────────────────────────┘
```

---

### Diagrama: qué agente llama qué función

```
VENTAS ─────┬─ build_sales_summary
            ├─ build_top_clients
            ├─ build_collection_summary
            ├─ build_overdue_receivables
            ├─ build_top_delinquent_clients
            ├─ build_sales_by_product ←── NUEVO
            ├─ build_client_status ←── NUEVO
            ├─ build_client_visits ←── NUEVO
            ├─ build_budget_comparison ←── NUEVO
            └─ build_production_vs_sales ←── NUEVO

RRHH ───────┬─ build_employee_summary
            ├─ build_employee_list
            ├─ build_birthday_list
            ├─ build_payroll_summary
            ├─ build_attendance_summary
            ├─ build_vacation_summary
            ├─ build_turnover_summary
            ├─ build_new_hires ←── NUEVO
            ├─ build_payroll_provisions ←── NUEVO
            └─ build_daily_attendance ←── NUEVO

CONTABILIDAD ┬─ build_accounting_summary
             └─ build_account_detail

FINANZAS ───┬─ build_financial_summary
            ├─ build_overdue_receivables (compartida con ventas)
            ├─ build_cobros_pagos_summary
            └─ build_loan_balances

PRODUCCIÓN ─┬─ build_production_summary
            ├─ build_production_orders
            ├─ build_production_runs
            ├─ build_bom_info
            ├─ build_warehouse_movements
            └─ build_inventory_stock (compartida con compras_insumos)

COMPRAS     ┬─ build_supply_purchases
INSUMOS     ├─ build_product_purchase_history
            ├─ build_pending_purchase_orders
            ├─ build_supplier_price_comparison
            ├─ build_purchase_payment_status
            └─ build_inventory_stock (compartida)

COMPRAS     ┬─ build_producer_purchases
PRODUCTORES ├─ build_registered_producers
            ├─ build_producer_pending_payments
            └─ build_producer_price_analysis
```

**Total: 35 funciones build_* distintas** (8 nuevas esta sesión)

---

---

## PREGUNTAS QUE EL BOT MANEJA (verificadas)

### ✅ RRHH (59 preguntas, 10 categorías)

| Categoría | Ej. de pregunta | Variables | Estado |
|-----------|----------------|-----------|--------|
| **Empleados total** | "¿Cuántos empleados hay?" | org, depto | ✅ 100% |
| **Empleados por org** | "¿Cuántos en INPROA SANTONI?" | cualquier org | ✅ |
| **Empleados por depto** | "¿Cuántos en Talento Humano?" | cualquier depto | ✅ |
| **Búsqueda por cargo** | "¿Cuántos supervisores hay?" | cualquier cargo (dinámico) | ✅ |
| **Búsqueda por nombre** | "Buscar empleado apellido González" | cualquier nombre (sin tildes) | ✅ |
| **Cumpleañeros** | "Cumpleañeros de marzo 2026" | cualquier mes, org | ✅ |
| **Nómina** | "Nómina de enero 2026" | mes, año, org | ✅ |
| **Ausentismo** | "Índices de ausentismo enero 2026" | mes, año, org | ✅ |
| **Vacaciones** | "Reporte de vacaciones pendientes" | mes, año, org | ✅ |
| **Rotación** | "¿Cuántos se fueron en 2025?" | año, org | ✅ |
| **Ingresos personal** | "¿Cuántos ingresaron en 2025?" | año, mes, org | ✅ |
| **Provisiones laborales** | "Prestaciones sociales dic 2025" | mes, año | ✅ |
| **Asistencia del día** | "Asistencias de hoy" | — | ⚠️ depende de datos biométricos |

### ✅ VENTAS (58 preguntas, 15 categorías)

| Categoría | Ej. de pregunta | Variables | Estado |
|-----------|----------------|-----------|--------|
| **Resumen ventas** | "Ventas de enero 2026" | mes, año, org, moneda | ✅ 100% |
| **Ventas en USD** | "¿Cuánto se facturó en dólares?" | mes, año | ✅ |
| **Ventas por rango** | "Ventas del 15/dic al 15/ene" | DD/MM/YYYY, DD de MES | ✅ |
| **Top clientes** | "Top 20 clientes del 2025" | año, org, moneda, limit | ✅ |
| **Cobranza** | "Cobranza de enero 2026" | mes, año, org | ✅ |
| **Cobranza por método** | "Cobros por transferencia" | método de pago | ✅ |
| **CxC vencidas** | "Cuentas por cobrar vencidas" | org | ✅ |
| **Top morosos** | "Top 10 morosos" | org | ✅ |
| **Ventas por zona** | "Ranking por zona enero 2026" | mes, año, zona | ✅ |
| **Ventas por región** | "Ventas en los Llanos" | región | ✅ |
| **Vendedores/distribuidores** | "Top vendedores INPROA" | org | ✅ |
| **Ventas por producto** | "Ventas de harinas feb 2026" | producto, mes, año | ✅ NUEVO |
| **Clientes activos/inactivos** | "Clientes activos InproMaiz" | org | ✅ NUEVO |
| **Metas/presupuesto** | "Comparativo vs metas" | mes, año | ✅ NUEVO |
| **Ventas vs producción** | "¿Cuánto se vendió vs produjo?" | mes, año | ✅ NUEVO |
| **Visitas a clientes** | "Visitas enero 2026" | mes, año | ✅ NUEVO |

### ✅ CONTABILIDAD (18 preguntas, 7 categorías)

| Categoría | Ej. de pregunta | Variables | Estado |
|-----------|----------------|-----------|--------|
| **Balance general** | "Balance general enero 2026" | mes, año, org | ✅ |
| **Activos/Pasivos/Patrimonio** | "Activos fijos INPROA" | tipo cuenta, org | ✅ |
| **Estado de resultados** | "Estado resultados 2025" | año, org | ✅ |
| **Saldo cuenta (con puntos)** | "Saldo de la cuenta 1.01.01" | código, mes, año | ✅ |
| **Saldo cuenta (sin puntos)** | "Cuenta 1101 en febrero" | código compacto | ✅ NUEVO |
| **Libro mayor** | "Libro mayor cuenta 5.01" | código, año | ✅ |
| **Gastos** | "Gastos enero a marzo 2026" | rango fechas | ✅ |
| **Impuestos** | "Impuestos enero 2026" | mes, año | ✅ |

### ✅ FINANZAS (37 preguntas, 7 categorías)

| Categoría | Ej. de pregunta | Variables | Estado |
|-----------|----------------|-----------|--------|
| **Saldos bancarios** | "¿Cuál banco tiene más disponibilidad?" | org | ✅ |
| **CxC** | "Cuentas por cobrar vencidas" | org, moneda | ✅ |
| **CxP** | "¿Cuánto debemos a proveedores?" | org, moneda | ✅ |
| **Cobros y pagos** | "Cobros y pagos de enero 2026" | mes, año | ✅ |
| **Préstamos** | "Cuotas de préstamos que vencen" | — | ✅ |
| **Flujo de caja** | "Flujo de caja enero 2026" | mes, año | ✅ |
| **Presupuesto** | "Presupuesto vs ejecución" | mes, año | ⚠️ |

### ✅ PRODUCCIÓN (61 preguntas, 8 categorías)

| Categoría | Ej. de pregunta | Variables | Estado |
|-----------|----------------|-----------|--------|
| **Resumen producción** | "¿Cuánto se produjo en enero?" | mes, año, org | ✅ |
| **Órdenes producción** | "Órdenes del mes" | mes, año | ✅ |
| **Inventario** | "¿Cuánto hay en almacén?" | org, producto | ✅ |
| **Inventario por producto** | "Inventario de arroz" | producto | ✅ |
| **Recetas/BOM** | "Receta del arroz blanco" | producto | ✅ |
| **Movimientos almacén** | "Traslados de almacén feb 2026" | mes, año | ✅ |
| **Desperdicios** | "Desperdicio en empaque" | mes, año | ✅ |
| **Producción por producto** | "Producción de arroz enero 2026" | producto, mes, año | ✅ |

### ✅ COMPRAS INSUMOS (86 preguntas, 8 categorías)

| Categoría | Ej. de pregunta | Variables | Estado |
|-----------|----------------|-----------|--------|
| **Resumen compras** | "¿Cuánto se compró este mes?" | mes, año, org, moneda | ✅ |
| **Inventario** | "¿Cuántas cajas quedan?" | producto | ✅ |
| **Órdenes pendientes** | "Órdenes de compra pendientes" | mes, año | ✅ |
| **Proveedores** | "Proveedores de láminas" | producto | ✅ |
| **Historial compras** | "Historial de compras de harina" | producto, proveedor | ✅ |
| **Comparar precios** | "Comparar precios entre proveedores" | producto | ✅ |
| **Estado de pago** | "Facturas pendientes de pago" | mes, año | ✅ |
| **Código producto** | "Código de cajas de cartón" | producto | ✅ |

### ✅ COMPRAS PRODUCTORES (29 preguntas, 4 categorías)

| Categoría | Ej. de pregunta | Variables | Estado |
|-----------|----------------|-----------|--------|
| **Compras agrícolas** | "¿Cuánto arroz se compró en 2025?" | producto, mes, año, org | ✅ |
| **Productores registrados** | "¿Cuántos productores hay?" | org | ✅ |
| **Pagos pendientes** | "Pagos pendientes a productores" | org | ✅ |
| **Precios** | "Precio promedio del kilo de arroz" | producto, mes, año | ✅ |

### Resumen total

| Agente | Categorías | Preguntas | Estado |
|--------|-----------|-----------|--------|
| RRHH | 13 | 59 | ✅ |
| Ventas | 15 | 58 | ✅ |
| Contabilidad | 7 | 18 | ✅ |
| Finanzas | 7 | 37 | ✅ |
| Producción | 8 | 61 | ✅ |
| Compras Insumos | 8 | 86 | ✅ |
| Compras Productores | 4 | 29 | ✅ |
| **TOTAL** | **62 categorías** | **348 preguntas** | **✅** |

**Variables dinámicas soportadas:** mes (12), año (2024-2026), org (7), moneda (VES/USD), producto (cualquiera vía ILIKE), cargo (cualquiera vía estructura), nombre (cualquiera sin tildes), cuenta contable (con/sin puntos), zona, región, vendedor, tipo documento.

---

---

## FASE 4: Mapa de Queries (build_* → tablas iDempiere)

### Tablas consultadas (43 total)

```
TABLAS PRINCIPALES (FROM):            TABLAS DE JOIN:
─────────────────────────             ─────────────────
ad_org                                ad_org
ad_user                               c_bank
btd_effectiveattenda                  c_bp_group
c_activity                            c_bpartner
c_allocationline                      c_bpartner_location
c_bankaccount                         c_city
c_bpartner                            c_currency
c_bpartner_location                   c_doctype
c_currency                            c_elementvalue
c_elementvalue                        c_invoice
c_invoice                             c_invoiceline
c_order                               c_location
c_orderline                           c_orderline
c_payment                             c_paymentterm
c_paymentterm                         c_region
fact_acct                             c_salesregion
hr_employee                           c_uom
hr_movement                           hr_concept
hr_process                            hr_department
m_inout                               hr_job
m_movement                            hr_movement
m_production                          hr_payroll
m_productionline                      hr_process
m_storageonhand                       m_inoutline
pa_goal                               m_locator
pp_product_bom                        m_movementline
pp_product_bomline                    m_product
                                      m_product_category
                                      m_productionline
                                      m_warehouse
```

### Mapa: build_* → tablas → campos clave

#### VENTAS

| Función | Tablas principales | JOIN | Campo fecha | Campo moneda |
|---------|--------------------|------|-------------|-------------|
| `build_sales_summary` | c_invoice | c_bpartner, ad_user, c_bpartner_location, c_salesregion, c_doctype | dateinvoiced | c_currency_id |
| `build_top_clients` | c_invoice | c_bpartner, c_bpartner_location, c_salesregion, c_doctype | dateinvoiced | c_currency_id |
| `build_collection_summary` | c_payment | c_allocationline, c_invoice | datetrx | c_currency_id |
| `build_overdue_receivables` | c_invoice | c_bpartner, c_paymentterm, c_doctype | dateinvoiced | c_currency_id |
| `build_top_delinquent_clients` | c_invoice | c_bpartner, c_paymentterm, c_doctype | dateinvoiced | c_currency_id |
| `build_sales_by_product` | c_invoice, c_invoiceline | m_product, m_product_category, c_doctype | dateinvoiced | c_currency_id |
| `build_client_status` | c_bpartner, c_invoice | ad_org | — | — |
| `build_client_visits` | c_activity | ad_org | created | — |
| `build_budget_comparison` | pa_goal | — | — | — |
| `build_production_vs_sales` | c_invoice, m_inout | m_inoutline | dateinvoiced, movementdate | — |

**Filtros comunes ventas:**
```sql
WHERE i.issotrx = 'Y'            -- ventas (no compras)
  AND i.docstatus IN ('CO','CL')  -- completadas/cerradas
  AND i.isactive = 'Y'
  AND dt.docbasetype = 'ARI'      -- factura (no NC)
```

#### RRHH

| Función | Tablas principales | JOIN | Campo fecha |
|---------|--------------------|------|-------------|
| `build_employee_summary` | hr_employee | c_bpartner, ad_org, hr_department, hr_job | — (siempre actual) |
| `build_employee_list` | hr_employee | c_bpartner, ad_org, hr_job | startdate (para ingresos) |
| `build_birthday_list` | hr_employee | c_bpartner, ad_user (LATERAL) | ad_user.birthday |
| `build_payroll_summary` | hr_movement | hr_process, hr_concept, hr_payroll | hp.dateacct |
| `build_attendance_summary` | hr_movement | hr_process, hr_concept | hp.dateacct |
| `build_vacation_summary` | hr_movement | hr_process, hr_concept | hp.dateacct |
| `build_turnover_summary` | hr_employee | c_bpartner, ad_org | enddate |
| `build_new_hires` | hr_employee | ad_org | startdate |
| `build_payroll_provisions` | hr_movement | hr_process, hr_concept | hp.dateacct |
| `build_daily_attendance` | btd_effectiveattenda | ad_org | created |

**Filtros comunes RRHH:**
```sql
WHERE e.isactive = 'Y'            -- empleado activo
  AND bp.isactive = 'Y'           -- tercero activo
-- Nómina:
  AND hp.docstatus IN ('CO','CL') -- proceso completado
```

**⚠️ birthday:** vive en `ad_user.birthday` (NO en c_bpartner). Se accede via LATERAL subquery.

#### CONTABILIDAD

| Función | Tablas principales | JOIN | Campo fecha |
|---------|--------------------|------|-------------|
| `build_accounting_summary` | fact_acct | c_elementvalue, ad_org | dateacct |
| `build_account_detail` | fact_acct | c_elementvalue | dateacct |

**Filtros:**
```sql
WHERE fa.isactive = 'Y'
-- Para cuenta específica:
  AND ev.value = :code             -- exacto (1.01.01)
  AND ev.value LIKE :code          -- flexible (1%1%01)
-- Para tipo de cuenta:
  AND ev.accounttype IN ('A','L','O','E','R')
```

**Tipos de cuenta:** A=Activo, L=Pasivo, O=Patrimonio, E=Gasto, R=Ingreso

#### FINANZAS

| Función | Tablas principales | JOIN | Campo fecha |
|---------|--------------------|------|-------------|
| `build_financial_summary` | c_bankaccount, c_invoice, c_payment | c_bank, c_currency, c_bpartner | datetrx, dateinvoiced |
| `build_cobros_pagos_summary` | c_payment | ad_org | datetrx |
| `build_loan_balances` | c_invoice | c_bpartner, c_doctype | dateinvoiced |

#### PRODUCCIÓN

| Función | Tablas principales | JOIN | Campo fecha |
|---------|--------------------|------|-------------|
| `build_production_summary` | m_inout | m_inoutline, m_product, ad_org | movementdate |
| `build_production_orders` | m_production | m_productionline, m_product | movementdate |
| `build_production_runs` | m_production | m_productionline, m_product | movementdate |
| `build_inventory_stock` | m_storageonhand | m_product, m_locator, m_warehouse | — (siempre actual) |
| `build_bom_info` | pp_product_bom | pp_product_bomline, m_product, c_uom | — |
| `build_warehouse_movements` | m_movement | m_movementline, m_product, m_locator | movementdate |

#### COMPRAS INSUMOS

| Función | Tablas principales | JOIN | Campo fecha |
|---------|--------------------|------|-------------|
| `build_supply_purchases` | c_invoice | c_bpartner, ad_org, c_doctype | dateinvoiced |
| `build_product_purchase_history` | c_invoiceline | c_invoice, m_product, c_bpartner | dateinvoiced |
| `build_pending_purchase_orders` | c_order | c_orderline, c_bpartner, m_product | dateordered |
| `build_supplier_price_comparison` | c_invoiceline | c_invoice, m_product, c_bpartner | dateinvoiced |
| `build_purchase_payment_status` | c_invoice | c_bpartner, c_allocationline | dateinvoiced |

**Filtros compras:**
```sql
WHERE i.issotrx = 'N'            -- compras (no ventas)
  AND i.docstatus IN ('CO','CL')
```

#### COMPRAS PRODUCTORES

| Función | Tablas principales | JOIN | Campo fecha |
|---------|--------------------|------|-------------|
| `build_producer_purchases` | c_order | c_orderline, c_bpartner, m_product, ad_org | dateordered |
| `build_registered_producers` | c_bpartner | ad_org | — |
| `build_producer_pending_payments` | c_order | c_orderline, c_bpartner | dateordered |
| `build_producer_price_analysis` | c_orderline | c_order, c_bpartner, m_product | dateordered |

**Filtros productores:**
```sql
WHERE o.issotrx = 'N'            -- compras
  AND bp.isagricultor = 'Y'       -- productores agrícolas
```

### Diagrama: tablas más usadas

```
                    ┌─────────────┐
                    │  c_invoice   │ ← Ventas, Compras, Finanzas
                    │ (449,740)    │
                    └──────┬──────┘
                           │
            ┌──────────────┼──────────────┐
            │              │              │
   ┌────────┴───┐  ┌──────┴──────┐ ┌─────┴──────┐
   │c_invoiceline│  │  c_payment  │ │ c_bpartner │
   │  (detalle)  │  │  (802,311)  │ │ (clientes) │
   └─────────────┘  └─────────────┘ └────────────┘

   ┌─────────────┐  ┌─────────────┐ ┌────────────┐
   │  c_order     │  │  fact_acct  │ │hr_employee │
   │  (278,870)   │  │(2,800,000) │ │  (RRHH)    │
   └─────────────┘  └─────────────┘ └────────────┘

   ┌─────────────┐  ┌─────────────┐ ┌────────────┐
   │  m_inout     │  │hr_movement  │ │m_storage   │
   │(producción)  │  │  (nómina)   │ │ onhand     │
   └─────────────┘  └─────────────┘ └────────────┘
```

---

## FASE 5: Transformaciones de Datos

Cuando el usuario escribe texto libre, el bot aplica transformaciones
para que matchee con iDempiere. Cada transformación tiene un PORQUÉ.

### 1. Acentos → sin acentos

**Problema:** iDempiere almacena "RODRIGUEZ", usuario escribe "Rodríguez".
**Dónde:** `agents/rrhh.py` → `_extract_name_search()` y `_extract_cargo_search()`

```
ANTES                    DESPUÉS               POR QUÉ
─────                    ───────               ──────
Rodríguez             →  Rodriguez             iDempiere no tiene tildes
mecánico              →  mecanico              hr_job guarda sin tildes
González              →  Gonzalez              c_bpartner guarda sin tildes
```

**Mapa:** `á→a, é→e, í→i, ó→o, ú→u, ñ→n` (y mayúsculas)

**⚠️ Solo aplica a:** nombres y cargos en RRHH.
Productos ya tienen `_normalize_search_word`. Cuentas son números. Orgs matchean por nombre conocido.

### 2. Plurales → singular

**Problema:** Usuario dice "supervisores", iDempiere tiene "SUPERVISOR".
**Dónde:** `agents/rrhh.py` → `_deplural()` y `idempiere_queries.py` → `_normalize_search_word()`

```
supervisores → supervisor     (-dores → -dor, consonante + es)
gerentes     → gerente        (-ntes → -nte, quitar solo s)
obreros      → obrero         (-os → -o, vocal + s)
analistas    → analista       (-as → -a, vocal + s)
choferes     → chofer         (-eres → -er, consonante + es)
```

**Reglas:** `tes+vocal antes → quitar s` | `es+consonante antes → quitar es` | `s+vocal antes → quitar s`

### 3. Código de cuenta → patrón LIKE

**Problema:** Usuario escribe "1101", iDempiere tiene "1.1.01" o "1.01.01".
**Dónde:** `agents/contabilidad.py` → `_normalize_account_code()`

```
1.01.01  →  tal cual  →  WHERE ev.value = '1.01.01'    (exacto)
1101     →  1%1%01    →  WHERE ev.value LIKE '1%1%01'  (flexible)
```

### 4. Moneda → IDs de iDempiere

**Problema:** 9 IDs diferentes para USD (cada org registró su propia entrada).
**Dónde:** `agents/date_utils.py` → `detect_currency()`

```
"dólares"/"USD"  →  c_currency_id IN (100,1000000,1000003,1000006,1000008,1000009,1000011,1000013,1000017)
"bolívares"/"Bs" →  c_currency_id = 205
(nada)           →  sin filtro (todas)
```

### 5. Fecha texto → rango SQL

**Dónde:** `agents/date_utils.py` → 10 patrones en orden

```
"enero 2026"                                → mes=1, anio=2026
"15 de diciembre 2024 al 15 de enero 2025"  → '2024-12-15', '2025-01-15'
"01/03/2026 al 09/03/2026"                  → '2026-03-01', '2026-03-09'
"hoy"                                       → fecha_actual, fecha_actual
"este mes" / "mes actual"                   → primer_dia_mes, hoy
"mes pasado"                                → mes_anterior completo
"desde enero 2025 hasta hoy"               → '2025-01-01', hoy
```

### 6. Organización texto → ILIKE

```
"INPROA"          →  WHERE ad_org.name ILIKE '%INPROA%'
"InproMaiz"       →  WHERE ad_org.name ILIKE '%InproMaiz%'
"santoni service"  →  WHERE ad_org.name ILIKE '%santoni service%'
```

### 7. Producto texto → búsqueda flexible

```
"harinas"         →  deplural "harina"  →  WHERE p.name ILIKE '%harina%'
"REP-LAMI-0037"   →  código exacto      →  WHERE p.value ILIKE '%REP-LAMI-0037%'
"arroz paddy"     →  AND cada palabra   →  WHERE p.name ILIKE '%arroz%' AND p.name ILIKE '%paddy%'
```

### 8. Zonas → regiones macro

```
ANZOATEGUI, SUCRE, MONAGAS  →  Oriente
APURE, BARINAS, PORTUGUESA  →  Llanos
CARABOBO, ARAGUA, MIRANDA   →  Centro
ZULIA, FALCON, LARA          →  Occidente
```

### Diagrama resumen

```
TEXTO DEL USUARIO
       │
       ├── Acentos ──→ á→a, ñ→n ──→ RRHH
       ├── Plurales ──→ supervisores→supervisor ──→ RRHH, Productos
       ├── Cuenta ──→ 1101→1%1%01 ──→ Contabilidad
       ├── Moneda ──→ "dólares"→9 IDs ──→ Ventas/Compras
       ├── Fecha ──→ 10 patrones ──→ Todos
       ├── Org ──→ ILIKE '%INPROA%' ──→ Todos
       ├── Producto ──→ deplural+ILIKE ──→ Ventas/Compras
       └── Zona ──→ 50 zonas→5 regiones ──→ Ventas
```

---

---

## FASE 6: Prompt y LLM

### Estructura de mensajes enviados al LLM

El LLM recibe una lista de mensajes en este orden exacto:

```
┌─ 1. SystemMessage: PROMPT DEL AGENTE ───────────────────────┐
│                                                               │
│  a) Prompt específico del agente (_system_prompt)             │
│     "Eres el Agente de RRHH de SantoniBot..."               │
│     - Qué tablas consulta                                     │
│     - Qué capacidades tiene                                   │
│     - Qué formato usar                                        │
│                                                               │
│  b) Fecha/hora actual                                         │
│     "Hoy es martes 21 de abril de 2026, 12:50 VET"          │
│                                                               │
│  c) Instrucciones adicionales                                 │
│     - Follow-ups contextuales                                 │
│     - Formato venezolano (punto=miles, coma=decimal)         │
│                                                               │
│  d) REGLAS ANTI-INVENCIÓN (17 reglas)                        │
│     - Presenta SOLO datos reales                              │
│     - NUNCA inventes nombres/montos/facturas                  │
│     - Copia totales EXACTOS                                   │
│     - Conteo de filas debe coincidir con encabezado          │
│                                                               │
│  e) REGLAS DE CONTEO (7 reglas)                              │
│     - "Total Empleados: 702" → tu resumen dice 702          │
│     - PROHIBIDO inventar totales                              │
└───────────────────────────────────────────────────────────────┘

┌─ 2. SystemMessage: DATA CATALOG (opcional) ──────────────────┐
│  Esquema de tablas de iDempiere para contexto                │
│  (generado por data_catalog_service si está activo)          │
└───────────────────────────────────────────────────────────────┘

┌─ 3. SystemMessage: RAG CONTEXT (opcional) ───────────────────┐
│  Conocimiento de base vectorial ChromaDB                      │
│  (si hay documentos indexados relevantes)                    │
└───────────────────────────────────────────────────────────────┘

┌─ 4. SystemMessage: DATOS REALES ─────────────────────────────┐
│                                                               │
│  SI hay datos (has_data = True):                             │
│  ╔══════════ DATOS REALES DE LA BASE DE DATOS ══════════╗   │
│  ║ ⚠️ INSTRUCCIÓN CRÍTICA:                              ║   │
│  ║ - DEBES presentar TODAS las secciones                ║   │
│  ║ - NO digas "no se encontraron" si hay datos abajo   ║   │
│  ║ - Lee TODO el bloque antes de responder              ║   │
│  ║ - SOLO di "no hay datos" si bloque VACÍO            ║   │
│  ╚══════════════════════════════════════════════════════╝   │
│                                                               │
│  ## Resumen de Personal                                       │
│  ### Totales                                                  │
│  - Total: 702                                                │
│  ### Por Organizacion [7 registros]                          │
│  | Organizacion | Total | Activos |                          │
│  | INPROA SANTONI | 319 | 319 |                             │
│  ...                                                          │
│                                                               │
│  SI NO hay datos (has_data = False):                         │
│  ⚠️ INSTRUCCIÓN OBLIGATORIA — NO ARROJÓ RESULTADOS          │
│  - Informa que no hay registros para ese filtro              │
│  - Sugiere alternativas                                       │
│  - NUNCA digas "no tengo acceso"                             │
│  - SÍ tienes acceso, solo no hay registros                   │
└───────────────────────────────────────────────────────────────┘

┌─ 5. Historial (máx 20 mensajes) ────────────────────────────┐
│  HumanMessage: "¿Cuántos empleados hay?"                     │
│  AIMessage: "Hay 702 empleados activos..." (tablas removidas)│
│  HumanMessage: "¿Y en INPROA?"                               │
│  AIMessage: "INPROA tiene 319..." (tablas removidas)         │
│  ...                                                          │
│                                                               │
│  ⚠️ Las tablas markdown se REMUEVEN del historial            │
│  (para que el LLM no copie datos viejos en respuesta nueva) │
└───────────────────────────────────────────────────────────────┘

┌─ 6. HumanMessage: PREGUNTA ACTUAL ──────────────────────────┐
│  "¿Cuántos supervisores tiene la empresa?"                   │
└───────────────────────────────────────────────────────────────┘
```

### Post-procesamiento de la respuesta

```
LLM genera respuesta
       │
       ▼
┌─ detect_hallucination() ─────────────────────────────────────┐
│  Busca patrones de datos inventados:                          │
│  - Números de factura falsos: FAC-\d{4,}, NC-\d{4,}         │
│  - Lotes falsos: Lote MA-XX-\d{3,}                          │
│  - Tablas con números cuando has_data=False                  │
│                                                               │
│  Si detecta → reemplaza toda la respuesta con                │
│  HALLUCINATION_REPLACEMENT (mensaje seguro)                  │
└──────────────────────────────────────────────────────────────┘
```

### Configuración del LLM

**Archivo:** `services/llm_factory.py`

```
┌─ Proveedor ─────────────────────────────────────────────────┐
│                                                               │
│  AI_PROVIDER=openrouter (producción)                         │
│  → OpenRouter API → DeepSeek Chat v3                         │
│  → Temperatura: 0.3 (agentes), 0.0 (SQL Direct)            │
│  → Max tokens: 2048                                          │
│                                                               │
│  AI_PROVIDER=groq (alternativa gratuita)                     │
│  → Groq API → Llama 3.3 70B                                 │
│                                                               │
│  AI_PROVIDER=anthropic (documentos/imágenes)                 │
│  → Claude API → claude-sonnet-4-5                             │
│                                                               │
│  SQL Direct:                                                  │
│  → USE_CLAUDE_FOR_SQL=false → usa AI_PROVIDER default        │
│  → USE_CLAUDE_FOR_SQL=true → Claude para SQL, default resto  │
└───────────────────────────────────────────────────────────────┘
```

### Reglas críticas del prompt (resumen)

| Regla | Propósito | Cuándo se agregó |
|-------|-----------|------------------|
| "DEBES presentar TODAS las secciones" | LLM ignoraba ausentismo/nómina detrás de employee summary | 21/Abr/2026 |
| "NO digas 'no se encontraron' si hay datos" | LLM decía "no hay datos" cuando sí había | 21/Abr/2026 |
| "Lee TODO el bloque antes de responder" | LLM leía primeras líneas y decidía sin ver el resto | 21/Abr/2026 |
| "Copia totales EXACTOS" | LLM cambiaba 702 por 1057 | Mar/2026 |
| "NUNCA inventes nombres" | LLM inventaba clientes/proveedores | Mar/2026 |
| "PROHIBIDO copiar del historial" | LLM reciclaba datos de pregunta anterior | Mar/2026 |
| Strip tablas del historial | Evita que LLM copie tabla vieja como respuesta nueva | Mar/2026 |
| "NUNCA digas 'no tengo acceso'" | LLM decía "no puedo consultar" cuando sí tenía datos | Mar/2026 |
| Formato venezolano | 1.234.567,89 (punto=miles, coma=decimal) | Feb/2026 |

---

*Fase 7: Keywords y routing → pendiente*
