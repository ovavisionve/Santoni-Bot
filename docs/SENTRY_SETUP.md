# Sentry Setup - SantoniBot

Guia para configurar Sentry como plataforma de monitoreo de errores y rendimiento en SantoniBot.

## 1. Crear un proyecto en Sentry

1. Registrarse en [sentry.io](https://sentry.io) (hay plan gratuito).
2. Crear una **organizacion** (ej: `ova-agency` o `alimentos-santoni`).
3. Crear **dos proyectos**:
   - **santonibot-backend** - Plataforma: Python / FastAPI
   - **santonibot-frontend** - Plataforma: Next.js
4. Copiar el DSN de cada proyecto (se encuentra en **Settings > Projects > [proyecto] > Client Keys (DSN)**).

> **Nota:** Si se prefiere usar un solo DSN para ambos (backend + frontend), se puede, pero se recomienda
> separar para tener metricas independientes.

## 2. Variables de entorno requeridas

Agregar al archivo `.env` (o en la configuracion de Coolify/Docker):

```bash
# Backend (Python/FastAPI)
SENTRY_DSN=https://xxxxx@o123456.ingest.sentry.io/1234567

# Frontend (Next.js) - debe ser NEXT_PUBLIC_ para que este disponible en el cliente
NEXT_PUBLIC_SENTRY_DSN=https://yyyyy@o123456.ingest.sentry.io/7654321

# Opcional: tasa de muestreo de trazas (0.0 a 1.0, default 0.2 = 20%)
SENTRY_TRACES_SAMPLE_RATE=0.2

# Opcional: tasa de muestreo de profiling (default 0.1 = 10%)
SENTRY_PROFILES_SAMPLE_RATE=0.1

# Opcional: para subir source maps al build del frontend
# (se obtiene en sentry.io > Settings > Auth Tokens)
SENTRY_AUTH_TOKEN=sntrys_xxxxx
SENTRY_ORG=ova-agency
SENTRY_PROJECT=santonibot-frontend
```

### Comportamiento sin DSN

Si `SENTRY_DSN` esta vacio o no se define, **todo el sistema funciona normalmente** sin Sentry.
Todas las integraciones son condicionales y se desactivan automaticamente.

## 3. Que se monitorea

### Backend (Python/FastAPI)

| Tipo | Descripcion |
|------|-------------|
| **Excepciones** | Cualquier excepcion no capturada en endpoints FastAPI |
| **Errores de agentes** | Fallos en `fetch_data()` de los 7 agentes, con contexto del agente y consulta |
| **Errores de base de datos** | Fallos de conexion a PostgreSQL interno e iDempiere |
| **Rendimiento** | Trazas de cada request HTTP + spans para queries de agentes |
| **Profiling** | Perfiles de rendimiento de funciones Python (si esta habilitado) |
| **Contexto de usuario** | ID, username y departamento del usuario autenticado (sin PII sensible) |
| **Alucinaciones** | Breadcrumbs cuando se detecta que el LLM invento datos |

### Frontend (Next.js)

| Tipo | Descripcion |
|------|-------------|
| **Errores JavaScript** | Excepciones en el cliente (React, hooks, etc.) |
| **Errores de API** | Fallos en llamadas al backend |
| **Errores de chat** | Problemas especificos del chat con contexto (agente, conversacion) |
| **Rendimiento** | Web Vitals, navegacion de paginas |
| **Session Replay** | Grabacion de sesiones que tuvieron errores (100% de sesiones con error) |
| **Navegacion** | Breadcrumbs de cambios de pagina |

## 4. Archivos de integracion

### Backend

| Archivo | Rol |
|---------|-----|
| `backend/app/main.py` | Inicializa Sentry SDK, middleware de contexto de usuario |
| `backend/app/config.py` | Settings: `sentry_dsn`, `sentry_traces_sample_rate`, `sentry_profiles_sample_rate` |
| `backend/app/utils/sentry_utils.py` | Helpers: `capture_agent_error()`, `set_agent_context()`, `track_query_performance()`, `add_breadcrumb()` |
| `backend/app/agents/base_agent.py` | Usa sentry_utils en `fetch_data` try/except y deteccion de alucinaciones |

### Frontend

| Archivo | Rol |
|---------|-----|
| `frontend/sentry.client.config.ts` | Init del SDK en el navegador (client-side) |
| `frontend/sentry.server.config.ts` | Init del SDK en SSR (server-side) |
| `frontend/sentry.edge.config.ts` | Init del SDK en Edge runtime (middleware) |
| `frontend/next.config.js` | Wrapper `withSentryConfig` para webpack y source maps |
| `frontend/src/lib/sentry.ts` | Helpers: `setSentryUser()`, `clearSentryUser()`, `captureChatError()`, `trackNavigation()` |

## 5. Uso de los helpers

### Backend - En un agente o servicio

```python
# Capturar un error con contexto de agente
from app.utils.sentry_utils import capture_agent_error

try:
    data = execute_query(...)
except Exception as exc:
    capture_agent_error("ventas", exc, {"query": "top_clients", "mes": 3})
    raise

# Medir rendimiento de una query
from app.utils.sentry_utils import track_query_performance

with track_query_performance("finanzas", "fetch bank balances"):
    balances = get_bank_balances()
```

### Frontend - En componentes React

```typescript
import { setSentryUser, clearSentryUser, captureChatError } from '@/lib/sentry';

// Despues del login
await setSentryUser({ id: user.id, username: user.username, department: user.department });

// En logout
await clearSentryUser();

// Capturar error de chat
try {
  await sendMessage(message);
} catch (error) {
  await captureChatError(error, { message, agent: 'ventas', conversationId: 42 });
}
```

## 6. Dashboard de Sentry

Una vez configurado, se pueden ver los datos en:

- **Issues** - Errores agrupados por tipo, con stack traces completos
- **Performance** - Tiempos de respuesta por endpoint y transaccion
- **Profiles** - Flamegraphs de funciones Python lentas
- **Replays** - Grabaciones de sesiones frontend con errores
- **Alerts** - Configurar notificaciones por email/Slack cuando ocurran errores nuevos

### Alertas recomendadas

1. **Error nuevo en produccion** - Notificar cuando aparezca un tipo de error que no se habia visto antes
2. **Spike de errores** - Notificar si la tasa de errores supera el umbral normal
3. **Rendimiento degradado** - Alertar si el P95 de `/api/chat` supera 10 segundos

## 7. Consideraciones

- **PII**: `send_default_pii=False` en ambos SDKs. No se envian cookies, headers de auth ni datos personales a Sentry.
- **Venezuela**: Si Sentry esta bloqueado, se puede configurar un proxy (similar a `ANTHROPIC_BASE_URL`).
- **Costos**: El plan gratuito de Sentry incluye 5K errores/mes y 10K transacciones de rendimiento/mes. Suficiente para empezar.
- **Source maps**: Para stack traces legibles en produccion, configurar `SENTRY_AUTH_TOKEN` y las variables de org/project.
