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

### Pendiente para cierre Fase 1:
- Mapeo completo de todas las tablas iDempiere (algunas queries aún en ajuste)
- Tests E2E ← **CUBIERTO POR PROTOCOLO QA**
- Script de migración datos demo → datos reales
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

| Bug | Fix date | Verificación |
|-----|----------|-------------|
| docstatus='CO' excluía facturas pagadas | 11/Mar/2026 | Query con facturas pagadas → resultados |
| "no tengo acceso" en capabilities | 10/Mar/2026 | Ningún agente dice "no tengo acceso" |
| org_name no se extraía en compras | 11/Mar/2026 | "compras en INPROA SANTONI" filtra OK |
| Herencia temporal rota | Mar/2026 | Follow-up sin fecha hereda período |
| Latencia severa | Mar/2026 | Ningún agente > 30s consistente |

---

### Procedimiento de Cierre

1. `./run_full_qa.sh` → genera `qa_report_FECHA.txt`
2. Corregir cada ❌ FAIL con commit documentado
3. Re-testear capa afectada
4. Actualizar `docs/ESTATUS_PROYECTO.md`
5. `git tag v1.0-qa-passed`
6. Backup DB + presentar reporte al cliente
