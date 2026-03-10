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
| 6 | **Compras Insumos** | `compras_insumos.py` | Compras por producto/proveedor, historial, precios, separación por moneda |
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
- **300 escenarios** (v2.2) cubriendo los 7 agentes
- Incluye: pregunta, agente esperado, tipo de consulta, follow-ups
- 70 escenarios de follow-up con herencia de contexto
- Tipos de error rastreados: routing, herencia temporal, fallback sin datos, errores DB
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
- Conexión exitosa a iDempiere real (queries de nómina, ventas, compras)
- Follow-ups inteligentes con herencia de contexto temporal
- Confidence score + dataset de 300 escenarios (v2.2)
- Separación de compras por moneda (VES/USD)
- Inventario desde m_storageonhand
- Corrección de múltiples bugs reportados por usuarios reales
- Script de pruebas en vivo (65 preguntas, 7 agentes)
- Diagnóstico de nómina iDempiere
- **Fix crítico (Mar 2026)**: Herencia temporal + manejo de errores en los 7 agentes (ver sección abajo)

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

## Convenciones de Código

- **Idioma del código**: Variables y funciones en inglés, comentarios y mensajes al usuario en español
- **Commits**: En español, formato `tipo: descripción` (feat, fix, test, docs, data, diag)
- **SQL**: Queries parametrizadas, nunca concatenación de strings
- **Agentes**: Heredan de `base_agent.py`, implementan `fetch_data()` y `format_response()`
- **Frontend**: Componentes funcionales React, hooks personalizados, Tailwind para estilos
