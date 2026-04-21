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

*Fase 2: Extracción de parámetros → pendiente*
*Fase 3: Mapa de agentes → pendiente*
*Fase 4: Mapa de queries → pendiente*
*Fase 5: Transformaciones → pendiente*
*Fase 6: Prompt y LLM → pendiente*
*Fase 7: Keywords y routing → pendiente*
