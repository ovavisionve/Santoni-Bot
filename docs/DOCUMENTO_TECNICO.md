# SantoniBot - Documento Tecnico Completo

**Sistema Inteligente de Analisis de Datos Empresariales**

| Campo | Detalle |
|---|---|
| **Cliente** | Alimentos Santoni, C.A. |
| **Desarrollador** | OVA Agency |
| **Version** | 1.0.0 |
| **Fecha** | 2025 |
| **Tipo** | Sistema de IA empresarial multi-agente |

---

## Tabla de Contenido

1. [Informacion General](#1-informacion-general)
2. [Arquitectura del Sistema](#2-arquitectura-del-sistema)
3. [Stack Tecnologico](#3-stack-tecnologico)
4. [Base de Datos](#4-base-de-datos)
5. [Autenticacion y Autorizacion](#5-autenticacion-y-autorizacion)
6. [Seguridad Completa](#6-seguridad-completa)
7. [Agentes de IA](#7-agentes-de-ia)
8. [API Endpoints](#8-api-endpoints)
9. [Frontend](#9-frontend)
10. [Panel de Administracion](#10-panel-de-administracion)
11. [Funcionalidades](#11-funcionalidades)
12. [Lo que NO Hace](#12-lo-que-no-hace)
13. [Despliegue](#13-despliegue)
14. [Backups](#14-backups)
15. [Monitoreo](#15-monitoreo)
16. [Mantenimiento](#16-mantenimiento)

---

## 1. Informacion General

### 1.1 Que es SantoniBot

SantoniBot es un sistema de inteligencia artificial empresarial disenado especificamente para **Alimentos Santoni, C.A.**, una empresa agroindustrial venezolana ubicada en Agua Blanca, Estado Portuguesa. El sistema permite a los empleados de la empresa realizar consultas en lenguaje natural sobre datos operativos de 7 departamentos distintos, y obtener respuestas con datos reales extraidos de la base de datos del ERP iDempiere.

El sistema utiliza una **arquitectura multi-agente** donde un orquestador central clasifica la intencion del usuario y delega la consulta al agente especializado del departamento correspondiente. Cada agente tiene conocimiento especifico de las tablas, metricas y terminologia de su departamento.

### 1.2 Cliente: Alimentos Santoni, C.A.

- **Sector**: Agroindustrial (procesamiento de arroz y maiz)
- **Ubicacion**: Agua Blanca, Estado Portuguesa, Venezuela
- **Plantas**: 2 plantas de produccion en Agua Blanca, oficinas administrativas en Araure
- **ERP**: iDempiere sobre PostgreSQL 13 (IP interna: 192.168.1.73:5432)
- **Productos principales**: Arroz Santoni Premium, Harina de Maiz Santoni
- **Idioma operativo**: Espanol (todo el sistema esta en espanol)

### 1.3 Desarrollador: OVA Agency

OVA Agency es la agencia de desarrollo responsable del diseno, implementacion y soporte de SantoniBot. El sistema fue construido como solucion a medida para las necesidades especificas de analisis de datos de Alimentos Santoni.

### 1.4 Infraestructura del Cliente

| Recurso | Especificacion |
|---|---|
| **Servidor VM** | Ubuntu Server 25.10 |
| **IP Interna** | 192.168.1.26 |
| **IP Publica** | 201.249.55.198 |
| **RAM** | 16 GB |
| **CPU** | 8 vCPU |
| **Almacenamiento** | 512 GB SSD |
| **Red** | 1 Gbps |
| **ERP iDempiere** | 192.168.1.73:5432 (PostgreSQL 13) |

---

## 2. Arquitectura del Sistema

### 2.1 Vision General

SantoniBot sigue una arquitectura de microservicios orquestada con Docker Compose. El sistema se compone de 6 servicios principales mas 2 servicios utilitarios (backup y certbot).

```
Internet/LAN
     |
  [Nginx :80/:443]  <-- Proxy inverso, rate limiting, security headers
     |
     +---> [Frontend :3000]  <-- Next.js 14 (React + TypeScript)
     |
     +---> [Backend :8000]   <-- FastAPI (Python)
              |
              +---> [PostgreSQL :5432]   <-- BD interna SantoniBot
              |
              +---> [ChromaDB :8001]     <-- Base de datos vectorial (RAG)
              |
              +---> [iDempiere :5432]    <-- BD ERP (solo lectura, red interna)
              |
              +---> [Groq API / Claude API]  <-- Proveedores de IA
```

### 2.2 Servicios Docker

El archivo `docker-compose.yml` define los siguientes servicios:

#### 2.2.1 Servicio `db` - PostgreSQL 16 (Base de datos interna)

- **Imagen**: `postgres:16-alpine`
- **Puerto expuesto**: `5433:5432` (mapeado a 5433 en el host para evitar conflicto)
- **Volumen**: `postgres_data:/var/lib/postgresql/data`
- **Healthcheck**: `pg_isready` cada 10 segundos, 5 reintentos
- **Politica de reinicio**: `unless-stopped`
- **Proposito**: Almacena usuarios, conversaciones, mensajes, logs de auditoria y datos demo

#### 2.2.2 Servicio `chromadb` - Base de Datos Vectorial

- **Imagen**: `chromadb/chroma:latest`
- **Puerto expuesto**: `8001:8000`
- **Volumen**: `chroma_data:/chroma/chroma`
- **Telemetria**: Deshabilitada (`ANONYMIZED_TELEMETRY=false`)
- **Proposito**: Almacena embeddings para el sistema RAG (base de conocimiento interna)

#### 2.2.3 Servicio `backend` - FastAPI

- **Build**: `./backend/Dockerfile`
- **Puerto expuesto**: `8000:8000`
- **Dependencias**: `db` (healthy), `chromadb` (started)
- **Volumen**: `./backend:/app` (montado para desarrollo con hot-reload)
- **Comando**: `uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload`
- **Env file**: `.env`
- **Proposito**: API REST, logica de negocio, orquestacion de agentes IA

#### 2.2.4 Servicio `frontend` - Next.js 14

- **Build**: `./frontend/Dockerfile`
- **Puerto expuesto**: `3000:3000`
- **Dependencias**: `backend`
- **Volumenes**: `./frontend:/app`, exclusiones para `node_modules` y `.next`
- **Proposito**: Interfaz de usuario (chat, login, panel de administracion)

#### 2.2.5 Servicio `nginx` - Proxy Inverso

- **Imagen**: `nginx:alpine`
- **Puertos expuestos**: `80:80`, `443:443`
- **Volumenes**: Configuracion nginx (read-only), certificados SSL, logs, webroot certbot
- **Dependencias**: `frontend`, `backend`
- **Proposito**: Proxy inverso, rate limiting, security headers, terminacion SSL

#### 2.2.6 Servicio `certbot` - Certificados SSL

- **Imagen**: `certbot/certbot:latest`
- **Profile**: `ssl` (no se ejecuta por defecto, solo bajo demanda)
- **Proposito**: Generacion y renovacion de certificados Let's Encrypt

#### 2.2.7 Servicio `backup` - Backup de PostgreSQL

- **Imagen**: `postgres:16-alpine`
- **Profile**: `backup` (no se ejecuta por defecto)
- **Proposito**: Backup diario automatizado de la base de datos interna

### 2.3 Volumenes Docker

| Volumen | Proposito |
|---|---|
| `postgres_data` | Datos persistentes de PostgreSQL 16 |
| `chroma_data` | Datos persistentes de ChromaDB |
| `nginx_certs` | Certificados SSL (Let's Encrypt) |
| `nginx_logs` | Logs de acceso y error de Nginx |
| `certbot_webroot` | Directorio para el challenge ACME |
| `db_backups` | Archivos de backup comprimidos (.sql.gz) |

### 2.4 Flujo de Red Interno

1. **Peticiones HTTP/HTTPS** llegan a Nginx en el puerto 80/443
2. Nginx aplica **rate limiting** y **security headers**
3. Rutas `/api/*` se proxy-pasan al **backend** (FastAPI) en el puerto 8000
4. Rutas `/ws/*` se proxy-pasan al backend con upgrade a **WebSocket**
5. Todas las demas rutas se proxy-pasan al **frontend** (Next.js) en el puerto 3000
6. El backend se conecta a **PostgreSQL** internamente por Docker DNS (`db:5432`)
7. El backend se conecta a **ChromaDB** por Docker DNS (`chromadb:8000`, mapeado internamente como puerto 8001)
8. El backend se conecta al **ERP iDempiere** por la red interna de Santoni (`192.168.1.73:5432`)
9. El backend hace llamadas externas a **Groq API** o **Anthropic Claude API**

---

## 3. Stack Tecnologico

### 3.1 Frontend

| Tecnologia | Version | Proposito |
|---|---|---|
| **Next.js** | 14.2.21 | Framework React con SSR y enrutamiento |
| **React** | 18.3.1 | Biblioteca de interfaz de usuario |
| **TypeScript** | 5.7.3 | Tipado estatico para JavaScript |
| **Tailwind CSS** | 3.4.17 | Framework de estilos utility-first |
| **Recharts** | 2.15.0 | Graficas interactivas (bar, line, pie, area) |
| **React Markdown** | 9.0.1 | Renderizado de Markdown en respuestas del chat |
| **remark-gfm** | 4.0.0 | Soporte GitHub Flavored Markdown (tablas) |
| **Lucide React** | 0.468.0 | Biblioteca de iconos |
| **html-to-image** | 1.11.11 | Exportacion de graficas a PNG |
| **@sentry/nextjs** | 8.45.0 | Monitoreo de errores frontend |
| **Jest** | 29.7.0 | Framework de testing |
| **@testing-library/react** | 16.1.0 | Testing de componentes React |
| **ESLint** | 9.17.0 | Linting de codigo |
| **PostCSS** | 8.4.49 | Procesamiento de CSS |
| **Autoprefixer** | 10.4.20 | Prefijos CSS automaticos |

### 3.2 Backend

| Tecnologia | Version | Proposito |
|---|---|---|
| **Python** | 3.11+ | Lenguaje de programacion del backend |
| **FastAPI** | - | Framework web asincrono de alto rendimiento |
| **SQLAlchemy** | 2.0+ | ORM para PostgreSQL (mapped_column syntax) |
| **Pydantic** | 2.0+ | Validacion de datos y esquemas |
| **pydantic-settings** | - | Gestion de configuracion desde .env |
| **Alembic** | - | Migraciones de base de datos |
| **python-jose** | - | Codificacion/decodificacion JWT |
| **passlib[bcrypt]** | - | Hashing de contrasenas con bcrypt |
| **pyotp** | - | Generacion y verificacion TOTP (2FA) |
| **LangChain** | - | Orquestacion de modelos de IA |
| **langchain-groq** | - | Integacion con Groq API |
| **langchain-anthropic** | - | Integracion con Claude API |
| **ChromaDB** | - | Cliente para base de datos vectorial |
| **openpyxl** | - | Generacion de archivos Excel (.xlsx) |
| **reportlab** | - | Generacion de archivos PDF |
| **sentry-sdk** | - | Monitoreo de errores backend |
| **uvicorn** | - | Servidor ASGI para FastAPI |
| **pytest** | - | Framework de testing |

### 3.3 Bases de Datos

| Tecnologia | Version | Proposito |
|---|---|---|
| **PostgreSQL** | 16 (Alpine) | Base de datos interna de SantoniBot |
| **PostgreSQL** | 13 | Base de datos iDempiere ERP (solo lectura) |
| **ChromaDB** | latest | Base de datos vectorial para RAG |

### 3.4 Infraestructura

| Tecnologia | Version | Proposito |
|---|---|---|
| **Docker** | - | Contenedorizacion de servicios |
| **Docker Compose** | 3.8 | Orquestacion de contenedores |
| **Nginx** | Alpine | Proxy inverso, rate limiting, SSL |
| **Certbot** | latest | Certificados SSL Let's Encrypt |
| **Coolify** | - | Plataforma de despliegue (alternativa) |

### 3.5 Proveedores de IA

| Proveedor | Modelo | Tipo | Proposito |
|---|---|---|---|
| **Groq** | Llama 3.3 70B Versatile | Primario (gratuito) | Procesamiento de consultas, clasificacion |
| **Anthropic** | Claude Sonnet 4.5 | Secundario (pago) | Analisis de documentos, vision, calidad superior |

La seleccion del proveedor se controla via la variable `AI_PROVIDER`. Cuando se configura `anthropic` pero no hay API key, el sistema hace fallback automatico a Groq.

---

## 4. Base de Datos

### 4.1 PostgreSQL 16 - Base de Datos Interna

Esta es la base de datos propia de SantoniBot donde se almacenan usuarios, conversaciones, auditoria y datos demo.

#### 4.1.1 Tabla `users` - Usuarios del Sistema

| Columna | Tipo | Descripcion |
|---|---|---|
| `id` | INTEGER PK | Identificador auto-incremental |
| `email` | VARCHAR(255) UNIQUE | Correo electronico |
| `username` | VARCHAR(100) UNIQUE | Nombre de usuario para login |
| `full_name` | VARCHAR(255) | Nombre completo |
| `hashed_password` | VARCHAR(255) | Contrasena hasheada con bcrypt |
| `role` | ENUM | Rol: `usuario`, `supervisor`, `administrador` |
| `department` | ENUM | Departamento principal |
| `extra_departments` | VARCHAR(500) NULL | Departamentos adicionales (CSV) |
| `is_active` | BOOLEAN | Estado activo/inactivo |
| `totp_secret` | VARCHAR(64) NULL | Secreto TOTP para 2FA |
| `totp_enabled` | BOOLEAN | 2FA habilitado/deshabilitado |
| `failed_login_attempts` | INTEGER | Contador de intentos fallidos |
| `locked_until` | TIMESTAMP WITH TZ NULL | Fecha/hora de desbloqueo |
| `created_at` | TIMESTAMP WITH TZ | Fecha de creacion |
| `updated_at` | TIMESTAMP WITH TZ | Fecha de ultima actualizacion |

**Departamentos disponibles**: `finanzas`, `contabilidad`, `ventas`, `rrhh`, `produccion`, `compras_insumos`, `compras_productores`

**Roles disponibles**: `usuario`, `supervisor`, `administrador`

#### 4.1.2 Tabla `conversations` - Conversaciones

| Columna | Tipo | Descripcion |
|---|---|---|
| `id` | INTEGER PK | Identificador auto-incremental |
| `user_id` | INTEGER FK | Referencia a `users.id` (CASCADE) |
| `title` | VARCHAR(255) | Titulo de la conversacion |
| `created_at` | TIMESTAMP WITH TZ | Fecha de creacion |
| `updated_at` | TIMESTAMP WITH TZ | Ultima actualizacion |

#### 4.1.3 Tabla `messages` - Mensajes

| Columna | Tipo | Descripcion |
|---|---|---|
| `id` | INTEGER PK | Identificador auto-incremental |
| `conversation_id` | INTEGER FK | Referencia a `conversations.id` (CASCADE) |
| `role` | ENUM | `user`, `assistant`, `system` |
| `content` | TEXT | Contenido del mensaje |
| `agent_used` | VARCHAR(100) NULL | Agente que proceso la consulta |
| `metadata_json` | TEXT NULL | Metadatos adicionales en JSON |
| `created_at` | TIMESTAMP WITH TZ | Fecha de creacion |

#### 4.1.4 Tabla `audit_logs` - Logs de Auditoria

| Columna | Tipo | Descripcion |
|---|---|---|
| `id` | INTEGER PK | Identificador auto-incremental |
| `user_id` | INTEGER FK NULL | Referencia a `users.id` (SET NULL) |
| `action` | VARCHAR(100) | Tipo de accion |
| `resource` | VARCHAR(100) | Recurso afectado |
| `detail` | TEXT NULL | Detalle de la accion |
| `agent_used` | VARCHAR(100) NULL | Agente involucrado |
| `ip_address` | VARCHAR(45) NULL | Direccion IP del cliente |
| `created_at` | TIMESTAMP WITH TZ | Fecha de creacion |

**Acciones registradas**: `login`, `login_failed`, `login_blocked`, `account_locked`, `account_unlocked`, `totp_setup`, `totp_enabled`, `totp_disabled`, `totp_failed`, `password_changed`, `chat_query`, `access_denied`

#### 4.1.5 Tablas Demo (Simulacion de iDempiere)

Estas tablas simulan la estructura del ERP iDempiere para desarrollo y demostracion. Cuando la conexion real a iDempiere este disponible, las consultas se redirigiran a la base de datos del ERP.

**Ventas:**
- `demo_clientes` - Clientes (simula C_BPartner): codigo, nombre, RIF, zona, vendedor, tipologia, limite de credito
- `demo_facturas_venta` - Facturas de venta (simula C_Invoice): numero, cliente, vendedor, zona, montos, estado, vencimiento
- `demo_lineas_factura_venta` - Lineas de factura (simula C_InvoiceLine): producto, categoria, cantidad, precio, monto
- `demo_cobranzas` - Cobranzas (simula C_Payment): recibo, cliente, factura, vendedor, zona, monto, metodo de pago
- `demo_metas_venta` - Metas de venta: vendedor, zona, mes, meta de venta, meta de cobranza

**Finanzas:**
- `demo_cuentas_bancarias` - Cuentas bancarias: banco, numero, tipo, moneda, saldo
- `demo_movimientos_bancarios` - Movimientos bancarios: cuenta, fecha, descripcion, referencia, tipo, monto, saldo
- `demo_cuentas_por_pagar` - Cuentas por pagar: proveedor, factura, fechas, montos, estado

**Contabilidad:**
- `demo_asientos_contables` - Asientos contables: numero, fecha, cuenta, descripcion, debe, haber, periodo
- `demo_balance_general` - Balance general: periodo, tipo de cuenta, grupo, cuenta, saldo

**Recursos Humanos:**
- `demo_empleados` - Empleados: cedula, nombre, cargo, departamento, ubicacion, salario, turno
- `demo_nominas` - Nominas: empleado, periodo, tipo, salario, asignaciones, deducciones, neto
- `demo_asistencias` - Asistencias: empleado, fecha, hora entrada/salida, tipo

**Produccion:**
- `demo_produccion_diaria` - Produccion diaria: fecha, planta, linea, turno, producto, cantidad, desperdicio, horas
- `demo_ordenes_produccion` - Ordenes de produccion: numero, fecha, producto, cantidades, estado, planta

**Compras de Insumos:**
- `demo_proveedores_insumos` - Proveedores: codigo, nombre, RIF, contacto, tipo insumo, calificacion
- `demo_ordenes_compra_insumos` - Ordenes de compra: numero, proveedor, fecha, insumo, cantidad, monto, estado

**Compras a Productores:**
- `demo_productores` - Productores agricolas: codigo, nombre, cedula, estado, municipio, tipo producto, hectareas
- `demo_compras_productores` - Compras: numero guia, productor, fecha, producto, peso, humedad, impureza, precio, monto, estado pago

### 4.2 PostgreSQL 13 - iDempiere ERP (Solo Lectura)

- **Host**: 192.168.1.73 (red interna de Santoni)
- **Puerto**: 5432
- **Base de datos**: `idempiere_produccion`
- **Usuario**: `ova`
- **Acceso**: Solo lectura (SELECT)
- **Proposito**: Fuente real de datos empresariales

**IMPORTANTE**: Todas las consultas a iDempiere son de solo lectura. El sistema nunca escribe, modifica ni elimina datos del ERP. El servicio `query_service.py` valida que solo se ejecuten sentencias `SELECT`.

### 4.3 ChromaDB - Base de Datos Vectorial

- **Host Docker**: `chromadb`
- **Puerto**: 8000 (interno), 8001 (host)
- **Proposito**: Almacenar embeddings de documentos para el sistema RAG
- **Colecciones**: Una por departamento con prefijo `santonibot_` (ej: `santonibot_ventas`, `santonibot_general`)
- **Chunking**: 500 caracteres con 50 de overlap
- **Opcional**: Si ChromaDB no esta disponible, el sistema continua funcionando sin RAG

---

## 5. Autenticacion y Autorizacion

### 5.1 Autenticacion JWT

El sistema utiliza **JSON Web Tokens (JWT)** para la autenticacion de API.

**Flujo de autenticacion:**

1. El usuario envia `username` y `password` al endpoint `POST /api/auth/login`
2. El sistema verifica las credenciales contra la base de datos (bcrypt)
3. Si el usuario tiene 2FA habilitado, se requiere un `totp_code` adicional
4. Al autenticarse exitosamente, se genera un JWT con los siguientes claims:
   - `sub`: ID del usuario
   - `username`: Nombre de usuario
   - `role`: Rol del usuario
   - `department`: Departamento principal
   - `exp`: Tiempo de expiracion
5. El JWT se retorna al frontend y se almacena en `localStorage` como `santonibot_token`
6. Todas las peticiones posteriores incluyen el token en el header `Authorization: Bearer <token>`

**Configuracion JWT:**

| Parametro | Valor por Defecto | Descripcion |
|---|---|---|
| `JWT_ALGORITHM` | HS256 | Algoritmo de firma |
| `JWT_EXPIRATION_MINUTES` | 30 | Minutos de validez del token |
| `SECRET_KEY` | (debe configurarse) | Clave secreta para firma (minimo 32 caracteres) |

### 5.2 RBAC - Control de Acceso Basado en Roles

El sistema implementa tres niveles de roles:

#### 5.2.1 Rol `usuario`

- Acceso al chat con su departamento asignado
- Si tiene `extra_departments`, puede consultar esos departamentos adicionales
- No tiene acceso al panel de administracion
- Puede cambiar su propia contrasena
- Puede configurar/desconfigurar 2FA en su cuenta

#### 5.2.2 Rol `supervisor`

- Todo lo del rol `usuario`
- Acceso a los logs de auditoria (`GET /api/admin/audit-logs`)
- Puede ver actividad del sistema

#### 5.2.3 Rol `administrador`

- Acceso total al sistema
- Acceso a **todos** los departamentos (sin restriccion)
- Panel de administracion completo:
  - Estadisticas del sistema
  - Gestion de usuarios (crear, editar, eliminar)
  - Logs de auditoria completos
  - Panel de seguridad (cuentas bloqueadas, IPs sospechosas)
  - Desbloqueo de cuentas
- Metricas de uso avanzadas
- Gestion de la base de conocimiento (RAG)

### 5.3 Aislamiento por Departamento

La seguridad por departamento se implementa en multiples capas:

1. **Orquestador**: Antes de enviar la consulta a un agente, verifica que el usuario tenga acceso al departamento correspondiente
2. **Propiedad `allowed_departments`**: Calcula dinamicamente los departamentos accesibles:
   - Usuarios normales: su departamento + `extra_departments`
   - Administradores: todos los departamentos
3. **Clasificacion del orquestador**: Si detecta que la consulta es sobre un departamento sin acceso, retorna `NO_ACCESS`
4. **Doble verificacion**: Incluso despues de la clasificacion, se verifica que el agente seleccionado corresponda a un departamento permitido
5. **Log de auditoria**: Intentos de acceso denegado se registran con accion `access_denied`

### 5.4 Middleware de Autenticacion

El archivo `backend/app/middleware/auth.py` define tres dependencias de FastAPI:

- **`get_current_user`**: Extrae y valida el JWT, retorna el usuario activo. Usado en todas las rutas protegidas.
- **`require_admin`**: Requiere rol `administrador`. Retorna HTTP 403 si no cumple.
- **`require_supervisor_or_admin`**: Requiere rol `supervisor` o `administrador`. Retorna HTTP 403 si no cumple.

---

## 6. Seguridad Completa

### 6.1 Contrasenas

#### 6.1.1 Hashing

- **Algoritmo**: bcrypt (via passlib)
- **Esquema**: `CryptContext(schemes=["bcrypt"], deprecated="auto")`
- Las contrasenas nunca se almacenan en texto plano

#### 6.1.2 Politica de Contrasenas

Toda contrasena nueva (creacion de usuario o cambio) debe cumplir:

- Minimo **8 caracteres**
- Al menos **1 letra mayuscula**
- Al menos **1 letra minuscula**
- Al menos **1 numero**
- Al menos **1 caracter especial** (`!@#$%^&*()_+-=[]{};':"\\|,.<>/?`)

La validacion se implementa con regex en `backend/app/schemas/user.py`:
```
^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[!@#$%^&*()_+\-=\[\]{};':"\\|,.<>\/?]).{8,}$
```

### 6.2 Autenticacion de Dos Factores (2FA / TOTP)

- **Protocolo**: TOTP (Time-based One-Time Password) - RFC 6238
- **Libreria**: pyotp
- **Aplicaciones compatibles**: Google Authenticator, Authy, Microsoft Authenticator
- **Ventana de validacion**: 1 paso (30 segundos de tolerancia)
- **Issuer**: "SantoniBot"

**Flujo de configuracion:**
1. Usuario llama `POST /api/auth/totp/setup` -> recibe `secret` y `qr_uri`
2. Escanea el QR con su aplicacion autenticadora
3. Ingresa el codigo de 6 digitos en `POST /api/auth/totp/enable`
4. A partir de entonces, cada login requiere el codigo TOTP

**Flujo de desactivacion:**
1. Usuario proporciona su codigo TOTP actual en `POST /api/auth/totp/disable`
2. Se limpia `totp_secret` y `totp_enabled`

### 6.3 Bloqueo de Cuentas (Account Lockout)

| Parametro | Valor |
|---|---|
| **Intentos maximos** | 5 intentos fallidos |
| **Duracion del bloqueo** | 15 minutos |
| **Codigo HTTP** | 423 Locked |

**Funcionamiento:**
1. Cada intento fallido incrementa `failed_login_attempts` en el usuario
2. Al alcanzar 5 intentos, se establece `locked_until` a 15 minutos en el futuro
3. Durante el bloqueo, cualquier intento retorna HTTP 423 con tiempo restante
4. Al expirar el bloqueo, se resetean automaticamente los contadores
5. Un login exitoso siempre resetea `failed_login_attempts` y `locked_until`
6. Un administrador puede desbloquear manualmente via `POST /api/admin/security/unlock-user/{user_id}`

### 6.4 Rate Limiting (Nginx)

Se definen 3 zonas de limitacion de velocidad en Nginx:

| Zona | Rate | Burst | Aplicacion |
|---|---|---|---|
| `api` | 30 req/min | 20 | Todas las rutas `/api/` |
| `login` | 5 req/min | 5 | Rutas `/api/auth/` |
| `export` | 10 req/min | 5 | Rutas `/api/export/` |

La memoria compartida para cada zona es de **10 MB** (`$binary_remote_addr`), suficiente para rastrear aproximadamente 160,000 direcciones IP.

### 6.5 Security Headers (Nginx)

Nginx inyecta los siguientes headers de seguridad en todas las respuestas:

| Header | Valor | Proposito |
|---|---|---|
| `X-Frame-Options` | `SAMEORIGIN` | Previene clickjacking |
| `X-Content-Type-Options` | `nosniff` | Previene MIME type sniffing |
| `X-XSS-Protection` | `1; mode=block` | Proteccion XSS del navegador |
| `Referrer-Policy` | `strict-origin-when-cross-origin` | Control de referrer |
| `X-Permitted-Cross-Domain-Policies` | `none` | Bloquea politicas cross-domain |
| `Permissions-Policy` | `camera=(), microphone=(), geolocation=(), payment=()` | Deshabilita APIs sensibles |
| `X-DNS-Prefetch-Control` | `off` | Previene DNS prefetching |
| `X-Download-Options` | `noopen` | Previene apertura automatica de descargas |
| `Content-Security-Policy` | (ver abajo) | Politica de seguridad de contenido |
| `Strict-Transport-Security` | (comentado, para HTTPS) | HSTS con preload |

**Content-Security-Policy detallado:**
```
default-src 'self';
script-src 'self' 'unsafe-inline' 'unsafe-eval';
style-src 'self' 'unsafe-inline';
img-src 'self' data: https:;
font-src 'self' data:;
connect-src 'self' http://localhost:* https://localhost:* https://*.ingest.sentry.io;
```

### 6.6 HTTPS/SSL

El sistema esta preparado para HTTPS con Let's Encrypt:

- **Certbot** integrado como servicio Docker (profile `ssl`)
- Configuracion SSL comentada pero lista en `nginx.conf`
- Soporte para TLSv1.2 y TLSv1.3
- Ciphers seguros preconfigurados (ECDHE-ECDSA/RSA con AES-GCM)
- SSL session cache de 10 MB
- SSL stapling habilitado
- HSTS preparado (max-age=31536000, includeSubDomains, preload)
- Redireccion HTTP -> HTTPS preparada (comentada)

**Comando para generar certificado:**
```bash
docker compose run --rm certbot certonly --webroot -w /var/www/certbot -d tudominio.com
```

**Comando para renovar:**
```bash
docker compose run --rm certbot renew
```

### 6.7 Validacion de SECRET_KEY

La configuracion implementa validacion en dos niveles:

1. **En produccion** (`APP_ENV=production`): Si la SECRET_KEY es el valor por defecto, el sistema **no arranca** y lanza un `ValueError` con instrucciones para generar una clave segura
2. **En cualquier entorno**: Si la SECRET_KEY tiene menos de 32 caracteres, se emite un **warning** en los logs

**Comando para generar clave segura:**
```python
python -c "import secrets; print(secrets.token_urlsafe(64))"
```

### 6.8 CORS

El middleware CORS se configura segun el entorno:

- **Desarrollo**: Permite `http://localhost:3000`, `http://localhost`, `https://localhost`
- **Produccion**: Solo permite `https://{DOMAIN}` y `http://{DOMAIN}`
- **Metodos**: GET, POST, PUT, PATCH, DELETE, OPTIONS
- **Headers**: Content-Type, Authorization
- **Credenciales**: Permitidas

### 6.9 Sentry (Monitoreo de Errores)

- **Opcional**: Solo se activa si `SENTRY_DSN` esta configurado
- **Backend**: `sentry-sdk` con traces sample rate configurable (default 0.2)
- **Frontend**: `@sentry/nextjs`
- **Configuracion**: `send_default_pii=False` (no envia informacion personal)
- **Entorno**: Se reporta `APP_ENV` y release `santonibot@1.0.0`

### 6.10 Auditoria

Cada accion relevante se registra en la tabla `audit_logs` con:
- ID del usuario (o NULL si no autenticado)
- Accion realizada
- Recurso afectado
- Detalle textual
- Agente de IA utilizado (si aplica)
- Direccion IP del cliente
- Timestamp

### 6.11 Auto-logout por Inactividad (Frontend)

El hook `useAuth` implementa deteccion de inactividad:

| Parametro | Valor |
|---|---|
| **Tiempo limite** | 30 minutos de inactividad |
| **Advertencia** | 5 minutos antes del cierre |
| **Verificacion** | Cada 30 segundos |
| **Eventos rastreados** | mousedown, keydown, scroll, touchstart, mousemove |

**Funcionamiento:**
1. Se registra la ultima actividad del usuario
2. Cada 30 segundos se verifica el tiempo transcurrido
3. A los 25 minutos sin actividad: se muestra banner amarillo de advertencia
4. A los 30 minutos: se ejecuta logout automatico y se redirige a `/login`
5. El usuario puede hacer clic en "Continuar sesion" para resetear el temporizador

### 6.12 Protecciones Adicionales de Nginx

- `server_tokens off`: Oculta la version de Nginx
- `proxy_hide_header X-Powered-By`: Oculta headers del backend
- `client_max_body_size 10m`: Limite de tamano de cuerpo de peticion
- Bloqueo de archivos ocultos: `location ~ /\. { deny all; }`
- Compresion Gzip habilitada (nivel 6) para text/css, JSON, JS, XML, SVG

---

## 7. Agentes de IA

### 7.1 Arquitectura Multi-Agente

SantoniBot implementa un patron de **orquestador + agentes especializados**:

```
Usuario
  |
  v
[Orquestador]  --> Clasifica la intencion del usuario
  |
  +---> [Agente Finanzas]
  +---> [Agente Contabilidad]
  +---> [Agente Ventas]
  +---> [Agente RRHH]
  +---> [Agente Produccion]
  +---> [Agente Compras Insumos]
  +---> [Agente Compras Productores]
  +---> [Handler General] (saludos, preguntas genericas)
```

### 7.2 Orquestador (`orchestrator.py`)

**Proposito**: Clasificar la intencion del usuario y dirigir la consulta al agente apropiado.

**Funcionamiento:**
1. Recibe el mensaje del usuario y la lista de departamentos permitidos
2. Usa el LLM con temperatura 0 y max_tokens 50 (respuesta rapida) para clasificar
3. El prompt de clasificacion incluye la descripcion de cada agente y los departamentos del usuario
4. El LLM responde con una sola palabra: el nombre del agente destino
5. Si la respuesta es `no_access`, se deniega el acceso
6. Si es `general`, se maneja como consulta generica
7. De lo contrario, se delega al agente especializado

**Verificacion de acceso**: El orquestador hace doble verificacion. Primero en la clasificacion (el prompt dice al LLM que responda `NO_ACCESS` si el departamento no esta en la lista del usuario), y luego programaticamente verificando que el `agent.department` este en `user.allowed_departments`.

### 7.3 Clase Base (`base_agent.py`)

Todos los agentes heredan de `BaseAgent` que proporciona:

- **LLM compartido**: Creado via `create_llm()` con temperatura 0.1 y max_tokens 4096
- **System prompt**: Cada agente define su propio prompt de sistema
- **Contexto de datos**: Metodo `fetch_data()` que obtiene datos reales de la BD
- **Contexto RAG**: Automaticamente busca en ChromaDB documentos relevantes
- **Historial**: Incluye las ultimas 10 interacciones de la conversacion
- **Formateo**: Metodos `_format_table()` y `_format_summary()` para datos
- **Instrucciones de graficas**: Instrucciones obligatorias para que el LLM genere bloques `chart` cuando hay tablas con 3+ filas

**Flujo de procesamiento de un agente:**
1. Construye el system prompt del agente
2. Busca contexto RAG en ChromaDB (departamento + general)
3. Ejecuta `fetch_data()` para obtener datos reales de la BD
4. Si hay datos: los incluye como contexto + instrucciones de graficas
5. Si no hay datos: incluye el esquema SQL como referencia
6. Agrega historial de conversacion (ultimos 10 mensajes)
7. Envia todo al LLM y retorna la respuesta

### 7.4 Agente de Finanzas (`finanzas.py`)

| Propiedad | Valor |
|---|---|
| **Nombre** | `finanzas` |
| **Departamento** | `finanzas` |
| **Tablas** | `demo_cuentas_bancarias`, `demo_movimientos_bancarios`, `demo_cuentas_por_pagar` |

**Capacidades:**
- Flujo de caja y posicion de tesoreria
- Cuentas por cobrar y por pagar
- Estado de cuentas bancarias (saldos)
- Indicadores financieros
- Alertas de morosidad y vencimientos

**Datos que obtiene:**
- Resumen financiero completo (saldos bancarios, CxC, CxP)
- Detalle de cuentas bancarias
- Cuentas por pagar pendientes
- Cuentas por cobrar vencidas

**Filtros soportados:** Ano, mes (detecta nombres de meses en espanol)

### 7.5 Agente de Contabilidad (`contabilidad.py`)

| Propiedad | Valor |
|---|---|
| **Nombre** | `contabilidad` |
| **Departamento** | `contabilidad` |
| **Tablas** | `demo_asientos_contables`, `demo_balance_general` |

**Capacidades:**
- Balance general y estructura patrimonial (activo, pasivo, patrimonio)
- Estado de resultados
- Libro diario y libro mayor
- Balanza de comprobacion
- Comparativas entre periodos contables

**Datos que obtiene:**
- Balance general por periodo (activo, pasivo, patrimonio desglosados)
- Asientos contables con totales de debe y haber
- Resumen de balance general

### 7.6 Agente de Ventas (`ventas.py`) - AGENTE PRIORITARIO

| Propiedad | Valor |
|---|---|
| **Nombre** | `ventas` |
| **Departamento** | `ventas` |
| **Tablas** | `demo_clientes`, `demo_facturas_venta`, `demo_lineas_factura_venta`, `demo_cobranzas`, `demo_metas_venta` |

**Capacidades (las mas extensas del sistema):**
1. Ranking de ventas por zona, vendedor, tipologia del cliente
2. Identificacion de zonas desatendidas
3. Pareto de clientes (analisis 80/20)
4. Top N mejores clientes (por zona, categoria, vendedor, general)
5. Activacion y apertura de clientes
6. Ranking de cobranza por zona, vendedor, tipologia
7. Deteccion de cuentas por cobrar atrasadas
8. Cobranza diaria/semanal y comparativo vs metas

**Datos que obtiene:**
- Top N clientes por ventas (con filtros de zona, vendedor)
- Resumen de cobranza (por metodo de pago, por vendedor)
- Cuentas por cobrar vencidas
- Metas vs ventas reales (con % de cumplimiento)
- Resumen de ventas (totales, por zona, por vendedor, por mes)

**Filtros soportados:** Ano, mes, vendedor especifico, zona especifica

### 7.7 Agente de RRHH (`rrhh.py`)

| Propiedad | Valor |
|---|---|
| **Nombre** | `rrhh` |
| **Departamento** | `rrhh` |
| **Tablas** | `demo_empleados`, `demo_nominas`, `demo_asistencias` |

**Capacidades:**
- Consulta de datos de empleados
- Resumen de nomina por periodo
- Reporte de asistencia, faltas, permisos
- Conteo por departamento, ubicacion, turno

**Nota de sensibilidad**: El system prompt indica que los datos de RRHH son ALTAMENTE SENSIBLES.

**Contexto especifico:**
- Ubicaciones: Agua Blanca (2 plantas), Araure (oficinas administrativas)
- Turnos: Oficina diurno, Planta rotativo
- Horario oficina: 7:30am a 5pm

### 7.8 Agente de Produccion (`produccion.py`)

| Propiedad | Valor |
|---|---|
| **Nombre** | `produccion` |
| **Departamento** | `produccion` |
| **Tablas** | `demo_produccion_diaria`, `demo_ordenes_produccion` |

**Capacidades:**
- Produccion diaria por planta/linea/turno
- Ordenes de produccion y tasa de completacion
- Analisis de desperdicios (merma, scrap)
- Eficiencia OEE por planta/linea/turno (horas operacion vs parada)

**Contexto especifico:**
- 2 plantas en Agua Blanca, Portuguesa
- Productos: Arroz Santoni Premium, Harina de Maiz Santoni
- Turnos rotativos en planta

### 7.9 Agente de Compras de Insumos (`compras_insumos.py`)

| Propiedad | Valor |
|---|---|
| **Nombre** | `compras_insumos` |
| **Departamento** | `compras_insumos` |
| **Tablas** | `demo_proveedores_insumos`, `demo_ordenes_compra_insumos` |

**Capacidades:**
- Listado y calificacion de proveedores
- Ordenes de compra (por estado, totales)
- Resumen de compras por tipo de insumo
- Ordenes pendientes

**Contexto especifico:**
- Responsables: Onofrio Gueccia, Jorge Chahine

### 7.10 Agente de Compras a Productores (`compras_productores.py`)

| Propiedad | Valor |
|---|---|
| **Nombre** | `compras_productores` |
| **Departamento** | `compras_productores` |
| **Tablas** | `demo_productores`, `demo_compras_productores` |

**Capacidades:**
- Resumen de compras por producto (Arroz Paddy Humedo, Maiz)
- Productores registrados por estado y tipo de producto
- Pagos pendientes a productores
- Analisis de precios (min, promedio, max por producto)
- Top 20 productores por volumen/monto

**Contexto especifico:**
- Responsable: Marlenis Figueredo
- Productos: Arroz Paddy Humedo, Maiz
- Zonas productoras: Portuguesa, Barinas, Apure, Lara, Cojedes

### 7.11 LLM Factory (`llm_factory.py`)

El modulo `llm_factory.py` centraliza la creacion de instancias LLM:

| Proveedor | Clase LangChain | Modelo Default |
|---|---|---|
| **Groq** | `ChatGroq` | `llama-3.3-70b-versatile` |
| **Anthropic** | `ChatAnthropic` | `claude-sonnet-4-5-20250929` |

**Logica de seleccion:**
1. Lee `AI_PROVIDER` de la configuracion
2. Si es `anthropic` pero no hay `ANTHROPIC_API_KEY`: fallback a Groq con warning
3. Crea la instancia LangChain correspondiente con los parametros dados

**Parametros de creacion:**
- `temperature`: 0 para clasificador, 0.1 para agentes
- `max_tokens`: 50 para clasificador, 4096 para agentes
- `purpose`: "classifier" o "agent" (para logging)

---

## 8. API Endpoints

### 8.1 Autenticacion (`/api/auth`)

| Metodo | Ruta | Auth | Descripcion |
|---|---|---|---|
| `POST` | `/api/auth/login` | No | Iniciar sesion (username, password, totp_code opcional) |
| `GET` | `/api/auth/me` | Si | Obtener datos del usuario actual |
| `POST` | `/api/auth/totp/setup` | Si | Generar secreto y URI para 2FA |
| `POST` | `/api/auth/totp/enable` | Si | Activar 2FA con codigo de verificacion |
| `POST` | `/api/auth/totp/disable` | Si | Desactivar 2FA (requiere codigo actual) |
| `POST` | `/api/auth/change-password` | Si | Cambiar contrasena (requiere contrasena actual) |

### 8.2 Chat (`/api/chat`)

| Metodo | Ruta | Auth | Descripcion |
|---|---|---|---|
| `POST` | `/api/chat/` | Si | Enviar mensaje y recibir respuesta del agente IA |
| `GET` | `/api/chat/conversations` | Si | Listar conversaciones del usuario (max 50) |
| `GET` | `/api/chat/conversations/{id}` | Si | Obtener conversacion completa con mensajes |
| `PATCH` | `/api/chat/conversations/{id}` | Si | Actualizar titulo de conversacion |
| `DELETE` | `/api/chat/conversations/{id}` | Si | Eliminar conversacion |

### 8.3 Usuarios (`/api/users`)

| Metodo | Ruta | Auth | Descripcion |
|---|---|---|---|
| `GET` | `/api/users/` | Admin | Listar todos los usuarios |
| `POST` | `/api/users/` | Admin | Crear nuevo usuario |
| `GET` | `/api/users/{id}` | Admin | Obtener detalle de usuario |
| `PATCH` | `/api/users/{id}` | Admin | Actualizar usuario |
| `DELETE` | `/api/users/{id}` | Admin | Eliminar usuario (no puede eliminarse a si mismo) |

### 8.4 Administracion (`/api/admin`)

| Metodo | Ruta | Auth | Descripcion |
|---|---|---|---|
| `GET` | `/api/admin/stats` | Admin | Estadisticas del sistema (usuarios, conversaciones, mensajes, uso de agentes) |
| `GET` | `/api/admin/audit-logs` | Supervisor+ | Logs de auditoria paginados (con filtros por user_id y accion) |
| `GET` | `/api/admin/metrics` | Admin | Metricas de uso (mensajes diarios, top usuarios, departamentos, promedio mensajes/conversacion) |
| `GET` | `/api/admin/security/locked-users` | Admin | Listar cuentas bloqueadas actualmente |
| `POST` | `/api/admin/security/unlock-user/{id}` | Admin | Desbloquear cuenta de usuario |
| `GET` | `/api/admin/security/overview` | Admin | Dashboard de seguridad (logins fallidos 24h, bloqueos 7d, cobertura 2FA, IPs sospechosas) |

### 8.5 Exportacion (`/api/export`)

| Metodo | Ruta | Auth | Descripcion |
|---|---|---|---|
| `GET` | `/api/export/message/{id}?format=csv` | Si | Exportar respuesta a CSV |
| `GET` | `/api/export/message/{id}?format=excel` | Si | Exportar respuesta a Excel (.xlsx) |
| `GET` | `/api/export/message/{id}?format=pdf` | Si | Exportar respuesta a PDF |

### 8.6 Base de Conocimiento / RAG (`/api/knowledge`)

| Metodo | Ruta | Auth | Descripcion |
|---|---|---|---|
| `POST` | `/api/knowledge/upload` | Admin | Subir documento de texto a la base de conocimiento de un departamento |
| `GET` | `/api/knowledge/collections` | Admin | Listar colecciones y conteo de documentos |
| `DELETE` | `/api/knowledge/collection/{dept}` | Admin | Limpiar todos los documentos de un departamento |
| `POST` | `/api/knowledge/query` | Admin | Buscar en la base de conocimiento (para testing) |

### 8.7 Documentos (`/api/documents`)

| Metodo | Ruta | Auth | Descripcion |
|---|---|---|---|
| `POST` | `/api/documents/upload` | Si | Subir documento para analisis en chat (max 10MB) |
| `GET` | `/api/documents/capabilities` | Si | Consultar capacidades de analisis segun proveedor IA |

**Formatos soportados:** PDF, XLSX, XLS, CSV, TXT, DOC, DOCX, PNG, JPG, JPEG, GIF, WEBP

**Nota:** El analisis completo de documentos (vision, PDF parsing avanzado) solo esta disponible con Claude API (`AI_PROVIDER=anthropic`). Con Groq solo se dispone de extraccion basica de texto.

### 8.8 Health Check (`/api/health`)

| Metodo | Ruta | Auth | Descripcion |
|---|---|---|---|
| `GET` | `/api/health` | No | Health check basico (status, app name, version) |
| `GET` | `/api/health/detailed` | Si | Health check detallado (DB, AI provider, iDempiere) |

---

## 9. Frontend

### 9.1 Paginas

#### 9.1.1 Pagina Raiz (`/`)

- Redireccion automatica: si hay token valido va a `/chat`, sino a `/login`
- Muestra spinner de carga durante la verificacion

#### 9.1.2 Login (`/login`)

- Formulario de username y contrasena
- Boton de mostrar/ocultar contrasena (icono de ojo)
- Soporte completo de 2FA/TOTP:
  - Si el servidor responde `totp_required=true`, se muestra el campo de codigo 6 digitos
  - Input numerico con tracking visual (font mono, spacing)
  - Boton "Volver al inicio de sesion" para regresar al formulario normal
- Mensajes de error visibles
- Footer: "Alimentos Santoni, C.A. -- Desarrollado por OVA Agency"
- Diseno: gradiente naranja Santoni, tarjeta blanca centrada con sombra

#### 9.1.3 Chat (`/chat`)

La pagina principal del sistema. Compuesta por:

- **Sidebar izquierdo** (colapsable):
  - Logo y nombre "SantoniBot"
  - Boton "Nueva conversacion"
  - Barra de busqueda de conversaciones
  - Lista de conversaciones con titulo, timestamp relativo, preview del ultimo mensaje
  - Cada conversacion tiene boton de eliminar (visible al hover)
  - Link al panel de administracion (solo para administradores)
  - Info del usuario: avatar con inicial, nombre, departamento
  - Boton de cerrar sesion

- **Area de chat central**:
  - Header con logo y nombre "SantoniBot - Asistente inteligente de Alimentos Santoni"
  - Pantalla de bienvenida (cuando no hay mensajes):
    - Logo grande
    - "Bienvenido a SantoniBot"
    - Sugerencias de consulta personalizadas por departamento
  - Mensajes del chat:
    - Mensajes del usuario: burbuja naranja a la derecha
    - Mensajes del asistente: burbuja blanca a la izquierda con badge del agente
    - Soporte Markdown completo con tablas estilizadas
    - Graficas automaticas de Recharts cuando hay datos tabulares
    - Botones de exportacion (CSV, Excel, PDF) en mensajes con tablas
    - Boton de copiar respuesta
    - Boton de toggle de grafica
    - Timestamps relativos en espanol
  - Indicador de "escribiendo" con animacion de dots
  - Campo de entrada de texto:
    - Textarea expandible
    - Limite de 2000 caracteres con contador visual
    - Enter para enviar, Shift+Enter para nueva linea
    - Disclaimer: "SantoniBot puede cometer errores. Verifica la informacion."

- **Banner de inactividad** (cuando aplica):
  - Banner amarillo animado en la parte superior
  - Mensaje: "Tu sesion se cerrara en 5 minutos por inactividad"
  - Boton "Continuar sesion" para resetear el temporizador

#### 9.1.4 Panel de Administracion (`/admin`)

- Acceso exclusivo para rol `administrador`
- Header con enlace de regreso al chat
- 4 pestanas: Estadisticas, Usuarios, Auditoria, Seguridad

(Ver seccion 10 para detalle completo)

### 9.2 Componentes

#### 9.2.1 `ChatWindow.tsx`

- Manejo de envio de mensajes con estado optimista
- Auto-scroll al recibir mensajes
- Sugerencias de consulta por departamento (finanzas, contabilidad, ventas, rrhh, produccion, compras_insumos, compras_productores)
- Labels de agentes traducidos al espanol
- Indicador de carga con animacion de puntos

#### 9.2.2 `ChatMessage.tsx`

- Renderizado de Markdown con `react-markdown` + `remark-gfm`
- Tablas Markdown con estilos personalizados (header naranja Santoni, hover en filas)
- **Deteccion automatica de graficas desde tablas**: Si una tabla tiene 3+ filas y al menos 1 columna numerica, se genera automaticamente un `ChartData`
- **Graficas del LLM**: Parseo de bloques ` ```chart ` con JSON para graficas explicitas
- **Deteccion de tipo de grafica**: Time series -> `line`, rankings -> `bar`
- **Parseo numerico inteligente**: Soporta formatos venezolano (1.234,56), US (1,234.56), monedas (Bs.), porcentajes
- Botones de exportacion que llaman directamente al API con el token Bearer
- Boton de copiar al portapapeles
- Timestamps relativos en espanol ("ahora", "hace 5 min", "ayer", etc.)

#### 9.2.3 `ChartRenderer.tsx`

Renderiza graficas interactivas usando Recharts. Soporta 4 tipos:

| Tipo | Componente Recharts | Uso |
|---|---|---|
| `bar` | `BarChart` + `Bar` | Rankings, comparativas |
| `line` | `LineChart` + `Line` | Tendencias temporales |
| `area` | `AreaChart` + `Area` | Acumulados |
| `pie` | `PieChart` + `Pie` | Distribuciones porcentuales |

**Caracteristicas:**
- Responsive (ancho 100%, alto 280px)
- Tooltip personalizado con formato venezolano
- Paleta de 10 colores (naranja Santoni primario)
- Truncado de labels largos (15 caracteres)
- Exportacion a PNG via `html-to-image` (2x pixel ratio)
- Soporte multi-yKey (hasta 2 series)
- Rotacion automatica de labels del eje X cuando hay 8+ elementos

#### 9.2.4 `Sidebar.tsx`

- Lista de conversaciones con busqueda
- Timestamps relativos cortos ("5m", "2h", "ayer", "3d")
- Preview del ultimo mensaje
- Boton de eliminar por conversacion
- Link condicional a admin (solo si rol=administrador)
- Tema oscuro (bg-gray-900)

### 9.3 Hook `useAuth`

Manejo centralizado de autenticacion con:
- Estado del usuario
- Login/logout
- Verificacion de token al montar
- Deteccion de inactividad (30 min) con warning a los 25 min
- Reset de actividad en eventos del usuario

---

## 10. Panel de Administracion

### 10.1 Pestana: Estadisticas

Muestra 4 tarjetas resumen:
- **Usuarios Activos**: N / Total
- **Conversaciones**: Total
- **Mensajes Totales**: Total
- **Agentes Activos**: N / 7

Grafico de barras con **uso por agente** (cuantas consultas proceso cada agente), con barras proporcionales en color naranja Santoni.

Endpoint: `GET /api/admin/stats`

### 10.2 Pestana: Usuarios

- Lista de todos los usuarios en tabla:
  - Nombre, Usuario, Departamento, Rol (badge de color), Estado (punto verde/gris)
  - Boton eliminar por usuario
- Formulario "Crear Usuario":
  - Campos: nombre completo, username, email, contrasena, rol (select), departamento (select)
  - Validacion de politica de contrasenas en el backend

Endpoints: `GET /api/users/`, `POST /api/users/`, `DELETE /api/users/{id}`

### 10.3 Pestana: Auditoria

Tabla de logs de auditoria con:
- Fecha (formato venezolano)
- Usuario (nombre + @username)
- Accion (con badge de color segun tipo)
- Detalle (truncado)
- Agente utilizado
- Direccion IP

Las filas de `access_denied` y `login_failed` se resaltan con fondo rojo.

Endpoint: `GET /api/admin/audit-logs`

### 10.4 Pestana: Seguridad (Panel TI)

Esta pestana esta disenada especificamente para el **equipo de TI de Santoni**.

#### 10.4.1 Dashboard de Seguridad

4 metricas clave:
- **Logins fallidos (24h)**: fondo rojo
- **Bloqueos (7 dias)**: fondo naranja
- **Cuentas bloqueadas**: fondo rojo si >0, verde si 0
- **Cobertura 2FA**: porcentaje de usuarios con 2FA habilitado

Seccion de **IPs sospechosas**: Lista de IPs con mas intentos fallidos en los ultimos 7 dias, cada una con badge de conteo.

Endpoint: `GET /api/admin/security/overview`

#### 10.4.2 Gestion de Cuentas Bloqueadas

Lista de cuentas bloqueadas con:
- Nombre completo + username
- Intentos fallidos y minutos restantes
- Boton "Desbloquear" por cada cuenta

Endpoints: `GET /api/admin/security/locked-users`, `POST /api/admin/security/unlock-user/{id}`

#### 10.4.3 Configuracion 2FA

Seccion para que el administrador configure/desconfigure su propio 2FA:
- Si 2FA esta inactivo: boton "Configurar 2FA"
- Muestra codigo QR + secreto manual
- Campo para verificar codigo de 6 digitos
- Si 2FA esta activo: campo para desactivar con codigo actual

#### 10.4.4 Cambio de Contrasena

Formulario con:
- Contrasena actual
- Nueva contrasena
- Confirmacion de nueva contrasena
- Validacion de coincidencia en frontend
- Validacion de politica en backend

---

## 11. Funcionalidades

### 11.1 Chat con IA

- Interfaz conversacional en lenguaje natural
- Respuestas en espanol con datos reales de la empresa
- Historial de conversacion (ultimos 10 mensajes como contexto)
- Creacion automatica de conversaciones
- Auto-titulo basado en el primer mensaje del usuario (max 50 caracteres)
- Sugerencias de consulta por departamento
- Indicador de agente que respondio

### 11.2 Exportacion de Reportes

Los usuarios pueden exportar cualquier respuesta del asistente que contenga tablas en 3 formatos:

#### 11.2.1 CSV
- Extraccion de tablas Markdown
- Encoding UTF-8 con BOM para compatibilidad con Excel
- Incluye titulo de tabla si existe

#### 11.2.2 Excel (.xlsx)
- Estilo profesional con branding Santoni (naranja #E06400)
- Header con titulo "SantoniBot - Reporte", agente, fecha
- Headers de tabla con fondo naranja y texto blanco
- Conversion automatica de valores numericos
- Formato de numeros con separadores de miles
- Auto-ajuste de ancho de columnas
- Bordes finos en todas las celdas

#### 11.2.3 PDF
- Layout carta (letter) con margenes de 0.75"
- Titulo naranja Santoni
- Tablas con headers naranja, filas alternas (blanco/naranja claro)
- Estilos profesionales via ReportLab

### 11.3 Graficas Interactivas

El sistema genera graficas de dos formas:

1. **Generacion por el LLM**: El agente incluye un bloque ` ```chart ` con JSON que define tipo, titulo, ejes y datos
2. **Deteccion automatica**: El frontend parsea tablas Markdown y genera graficas automaticamente si tienen 3+ filas con datos numericos

**Tipos soportados:**
- **Bar**: Rankings, comparativas (default)
- **Line**: Series temporales (detecta nombres de meses/dias)
- **Pie**: Distribuciones porcentuales
- **Area**: Acumulados

**Funcionalidades:**
- Tooltip interactivo con valores formateados
- Leyenda cuando hay multiples series
- Exportacion a PNG (2x resolucion)
- Toggle para mostrar/ocultar grafica auto-detectada
- Maximo 15 elementos en graficas del LLM

### 11.4 Historial de Conversaciones

- Las ultimas 50 conversaciones se listan en el sidebar
- Busqueda por titulo de conversacion
- Preview del ultimo mensaje
- Timestamps relativos
- Eliminacion individual de conversaciones
- Carga completa de mensajes al seleccionar una conversacion

### 11.5 Carga de Documentos

- Endpoint para subir archivos (max 10 MB)
- Formatos: PDF, Excel, CSV, TXT, Word, imagenes
- Almacenamiento temporal en `/tmp/santonibot_uploads`
- Con Claude API: analisis completo (vision, parsing avanzado)
- Con Groq: solo extraccion basica de texto

### 11.6 RAG (Retrieval-Augmented Generation)

Sistema de base de conocimiento interna:

- **Almacenamiento**: ChromaDB con una coleccion por departamento
- **Chunking**: Textos divididos en fragmentos de 500 caracteres con 50 de overlap
- **Busqueda**: Semantica via embeddings de ChromaDB
- **Contexto dual**: Cada consulta busca en la coleccion del departamento + coleccion general
- **Inyeccion**: El contexto encontrado se agrega al prompt del agente como referencia
- **Administracion**: Solo administradores pueden subir/eliminar documentos
- **Resiliencia**: Si ChromaDB no esta disponible, el sistema funciona sin RAG

### 11.7 Auditoria Completa

Todas las acciones criticas se registran:
- Login exitoso/fallido
- Bloqueo/desbloqueo de cuentas
- Configuracion/desactivacion de 2FA
- Codigo TOTP incorrecto
- Cambio de contrasena
- Consultas al chat (con agente usado)
- Intentos de acceso a departamentos no autorizados
- Direccion IP del cliente en todas las acciones

---

## 12. Lo que NO Hace

Es importante documentar claramente las limitaciones del sistema:

### 12.1 NO Importa Datos desde Excel

SantoniBot **no importa datos desde archivos Excel ni ningun otro archivo**. Toda la informacion proviene exclusivamente de la base de datos del ERP iDempiere. La carga de documentos solo sirve para analisis/consulta, no para importacion de datos.

### 12.2 NO Escribe en el ERP

El acceso a la base de datos de iDempiere es **estrictamente de solo lectura**. El servicio `query_service.py` valida que solo se ejecuten sentencias `SELECT`. SantoniBot nunca crea, modifica ni elimina registros en iDempiere.

### 12.3 NO Opera en Tiempo Real

Las consultas se ejecutan al momento de la peticion. No hay streaming en tiempo real, no hay WebSockets activos para actualizacion automatica de datos, y no hay notificaciones push. El usuario debe hacer una nueva consulta para obtener datos actualizados.

### 12.4 NO Ejecuta SQL Arbitrario

Los agentes NO generan SQL dinamicamente basado en la entrada del usuario. Cada agente tiene consultas SQL pre-construidas y parametrizadas que se seleccionan segun la intencion detectada. Esto previene inyeccion SQL y asegura consultas optimizadas.

### 12.5 NO Tiene Multilingue

El sistema esta disenado exclusivamente para operar en **espanol**. Todos los prompts, respuestas, interfaz de usuario, mensajes de error y documentacion estan en espanol.

### 12.6 NO Tiene Integracion con Otros Sistemas

Actualmente solo se integra con:
- iDempiere (PostgreSQL) para datos
- Groq/Claude para IA
- ChromaDB para RAG
- Sentry para monitoreo

No hay integracion con email, Slack, WhatsApp, Teams, calendarios, ni otros sistemas de terceros.

### 12.7 NO Tiene Modo Offline

El sistema requiere conexion a internet para las llamadas al proveedor de IA (Groq o Claude). Sin conexion a internet, las consultas al chat no funcionan.

### 12.8 NO Genera Documentos Formales

Las exportaciones (CSV, Excel, PDF) son reportes basicos extraidos de las respuestas del chat. No genera documentos contables formales, no tiene membretes certificados, ni firma digital.

### 12.9 NO Modifica Datos Internos via Chat

Los usuarios no pueden crear, modificar ni eliminar usuarios, contrasenas u otros datos del sistema a traves del chat. La gestion de usuarios solo es posible a traves del panel de administracion.

---

## 13. Despliegue

### 13.1 Requisitos Previos

- Docker y Docker Compose instalados
- Acceso a la red interna de Santoni (para iDempiere)
- Conexion a internet (para Groq/Claude API)
- Puerto 80 (y 443 para HTTPS) disponibles

### 13.2 Archivo `.env`

A continuacion se listan todas las variables de entorno con su descripcion:

#### Variables Generales

| Variable | Default | Descripcion |
|---|---|---|
| `APP_NAME` | `SantoniBot` | Nombre de la aplicacion |
| `APP_ENV` | `development` | Entorno: `development` o `production` |
| `DEBUG` | `true` | Habilita docs Swagger en `/api/docs` |
| `DOMAIN` | `localhost` | Dominio del servidor (para CORS en produccion) |

#### Variables de Admin

| Variable | Default | Descripcion |
|---|---|---|
| `ADMIN_DEFAULT_PASSWORD` | (auto-generada) | Contrasena del admin inicial. Si no se configura, se genera aleatoriamente y se imprime en los logs al iniciar |

#### Variables de Backend

| Variable | Default | Descripcion |
|---|---|---|
| `BACKEND_PORT` | `8000` | Puerto del backend |
| `SECRET_KEY` | (DEBE CAMBIARSE) | Clave secreta para JWT (minimo 32 caracteres) |
| `JWT_ALGORITHM` | `HS256` | Algoritmo de firma JWT |
| `JWT_EXPIRATION_MINUTES` | `480` | Minutos de validez del token JWT |

#### Variables de Base de Datos Interna

| Variable | Default | Descripcion |
|---|---|---|
| `POSTGRES_HOST` | `db` | Host de PostgreSQL (nombre del servicio Docker) |
| `POSTGRES_PORT` | `5432` | Puerto de PostgreSQL |
| `POSTGRES_DB` | `santonibot` | Nombre de la base de datos |
| `POSTGRES_USER` | `santonibot` | Usuario de PostgreSQL |
| `POSTGRES_PASSWORD` | (DEBE CAMBIARSE) | Contrasena de PostgreSQL |

#### Variables de iDempiere

| Variable | Default | Descripcion |
|---|---|---|
| `IDEMPIERE_DB_HOST` | `192.168.1.73` | Host de la BD iDempiere |
| `IDEMPIERE_DB_PORT` | `5432` | Puerto de la BD iDempiere |
| `IDEMPIERE_DB_NAME` | `idempiere_produccion` | Nombre de la BD |
| `IDEMPIERE_DB_USER` | `ova` | Usuario de solo lectura |
| `IDEMPIERE_DB_PASSWORD` | (DEBE CAMBIARSE) | Contrasena |

#### Variables de IA

| Variable | Default | Descripcion |
|---|---|---|
| `AI_PROVIDER` | `groq` | Proveedor: `groq` (gratuito) o `anthropic` (pago) |
| `GROQ_API_KEY` | (vacio) | API key de Groq |
| `GROQ_MODEL` | `llama-3.3-70b-versatile` | Modelo de Groq |
| `ANTHROPIC_API_KEY` | (vacio) | API key de Anthropic Claude |
| `ANTHROPIC_MODEL` | `claude-sonnet-4-5-20250929` | Modelo de Claude |

#### Variables de ChromaDB

| Variable | Default | Descripcion |
|---|---|---|
| `CHROMA_HOST` | `chromadb` | Host de ChromaDB (nombre del servicio Docker) |
| `CHROMA_PORT` | `8001` | Puerto de ChromaDB |

#### Variables de Sentry

| Variable | Default | Descripcion |
|---|---|---|
| `SENTRY_DSN` | (vacio) | DSN de Sentry (vacio = deshabilitado) |
| `SENTRY_TRACES_SAMPLE_RATE` | `0.2` | Tasa de muestreo de trazas (0.0 a 1.0) |
| `NEXT_PUBLIC_SENTRY_DSN` | (vacio) | DSN de Sentry para el frontend |

#### Variables de Frontend

| Variable | Default | Descripcion |
|---|---|---|
| `NEXT_PUBLIC_API_URL` | `http://localhost:8000` | URL del backend para el frontend |
| `NEXT_PUBLIC_APP_NAME` | `SantoniBot` | Nombre mostrado en el frontend |

### 13.3 Procedimiento de Despliegue

#### 13.3.1 Primer Despliegue

```bash
# 1. Clonar el repositorio
git clone <repo-url> /opt/santonibot
cd /opt/santonibot

# 2. Crear archivo de configuracion
cp .env.example .env

# 3. Editar las variables (OBLIGATORIO cambiar SECRET_KEY y passwords)
nano .env

# 4. Generar una SECRET_KEY segura
python3 -c "import secrets; print(secrets.token_urlsafe(64))"

# 5. Levantar los servicios
docker-compose up -d

# 6. Verificar que todos los servicios estan corriendo
docker-compose ps

# 7. Ver logs del backend (para obtener la contrasena de admin si no se configuro)
docker-compose logs backend | grep -i "admin\|password"

# 8. Verificar health check
curl http://localhost/api/health
```

#### 13.3.2 Actualizaciones

```bash
cd /opt/santonibot

# 1. Hacer backup antes de actualizar
docker compose run --rm backup

# 2. Obtener cambios
git pull

# 3. Reconstruir imagenes
docker-compose build

# 4. Reiniciar servicios
docker-compose up -d

# 5. Ejecutar migraciones (si hay)
docker-compose exec backend alembic upgrade head

# 6. Verificar
curl http://localhost/api/health
```

### 13.4 Coolify

El sistema esta preparado para despliegue via **Coolify**, una plataforma self-hosted de CI/CD. Coolify puede gestionar los contenedores Docker directamente desde el repositorio Git.

### 13.5 Nginx como Proxy Inverso

Nginx maneja:
- Proxy reverso de todas las peticiones
- Rate limiting en 3 zonas
- Security headers
- Compresion Gzip
- WebSocket para chat (upgrade de conexion)
- SSL/TLS (cuando se configure)
- Logs de acceso con formato personalizado (incluye tiempos de respuesta del upstream)
- Bloqueo de archivos ocultos
- Soporte HMR para desarrollo de Next.js

---

## 14. Backups

### 14.1 Configuracion

El servicio de backup esta definido en `docker-compose.yml` con el profile `backup`, lo que significa que no se ejecuta automaticamente.

### 14.2 Ejecucion Manual

```bash
docker compose run --rm backup
```

### 14.3 Ejecucion Automatica (Cron)

Para backups automaticos diarios a las 2:00 AM:

```bash
# Editar crontab del servidor
crontab -e

# Agregar la siguiente linea:
0 2 * * * cd /opt/santonibot && docker compose run --rm backup
```

### 14.4 Que Hace el Backup

1. Genera un timestamp (`YYYYMMDD_HHMMSS`)
2. Ejecuta `pg_dump` de la base de datos SantoniBot
3. Comprime el dump con gzip (`santonibot_TIMESTAMP.sql.gz`)
4. Almacena en el volumen `db_backups` en `/backups/`
5. Reporta el tamano del archivo generado
6. **Limpieza automatica**: Elimina backups con mas de 30 dias de antiguedad
7. Reporta la cantidad total de backups disponibles

### 14.5 Retencion

- **Duracion**: 30 dias
- **Limpieza**: Automatica al ejecutar el backup (`find -mtime +30 -delete`)

### 14.6 Restauracion

```bash
# 1. Listar backups disponibles
docker run --rm -v santoni-bot_db_backups:/backups alpine ls -la /backups/

# 2. Restaurar un backup especifico
docker compose exec -T db psql -U santonibot -d santonibot < <(
  docker run --rm -v santoni-bot_db_backups:/backups alpine \
    zcat /backups/santonibot_20250601_020000.sql.gz
)

# Alternativa: copiar el backup al host primero
docker run --rm -v santoni-bot_db_backups:/backups -v $(pwd):/host alpine \
  cp /backups/santonibot_20250601_020000.sql.gz /host/

# Descomprimir y restaurar
gunzip santonibot_20250601_020000.sql.gz
docker compose exec -T db psql -U santonibot -d santonibot < santonibot_20250601_020000.sql
```

### 14.7 Lo que NO se Respalda

- **Datos de iDempiere**: El ERP tiene su propio sistema de backups
- **ChromaDB**: Los embeddings se regeneran automaticamente. Si se pierde, solo se pierden los documentos subidos a la base de conocimiento
- **Archivos temporales** (`/tmp/santonibot_uploads`): Se limpian periodicamente

---

## 15. Monitoreo

### 15.1 Sentry

Si `SENTRY_DSN` esta configurado:

- **Backend**: Captura excepciones no manejadas, con trazas de performance
- **Frontend**: Captura errores de JavaScript del lado del cliente
- **Configuracion**:
  - `traces_sample_rate`: 0.2 (20% de peticiones tienen traza completa)
  - `send_default_pii`: false (no envia datos personales)
  - `environment`: Segun `APP_ENV`
  - `release`: `santonibot@1.0.0`

### 15.2 Logs de Nginx

Nginx escribe logs con formato personalizado `santoni` que incluye:
- IP remota y usuario
- Timestamp
- Request (metodo, URL, protocolo)
- Status code y bytes enviados
- Referer y User-Agent
- **Tiempos de respuesta**: `rt` (request time), `uct` (upstream connect time), `uht` (upstream header time), `urt` (upstream response time)

Los logs se almacenan en el volumen `nginx_logs`:
- `access.log`: Todas las peticiones
- `error.log`: Errores (nivel warn y superior)

**Acceder a los logs:**
```bash
# Logs en tiempo real
docker compose logs -f nginx

# Acceder al volumen de logs
docker run --rm -v santoni-bot_nginx_logs:/logs alpine tail -100 /logs/access.log
```

### 15.3 Logs del Backend

El backend usa el sistema de logging de Python con el logger `santonibot`:
- **HTTP logger** (`santonibot.http`): Registra todas las peticiones (excepto `/api/health`) con metodo, ruta, status code y duracion en ms
- **Agent logger** (`santonibot.agents`): Actividad de los agentes de IA
- **LLM logger** (`santonibot.llm`): Seleccion de proveedor de IA
- **RAG logger** (`santonibot.rag`): Actividad de ChromaDB
- **Chat logger** (`santonibot.chat`): Errores en procesamiento de mensajes
- **Config logger** (`santonibot.config`): Warnings de configuracion

**Acceder a los logs:**
```bash
docker compose logs -f backend
```

### 15.4 Logs de Auditoria (Base de Datos)

Tabla `audit_logs` con registro permanente de:
- Intentos de login (exitosos y fallidos)
- Bloqueos y desbloqueos de cuentas
- Configuracion de 2FA
- Consultas al chat
- Intentos de acceso no autorizado
- Cambios de contrasena
- IP del cliente en cada accion

**Acceso**: Via panel de administracion (pestana Auditoria) o directamente via API `GET /api/admin/audit-logs`

### 15.5 Health Endpoints

#### Health Check Basico (sin autenticacion)
```
GET /api/health
```
Respuesta:
```json
{
  "status": "ok",
  "app": "SantoniBot",
  "version": "1.0.0"
}
```

#### Health Check Detallado (requiere autenticacion)
```
GET /api/health/detailed
```
Respuesta:
```json
{
  "status": "ok",
  "app": "SantoniBot",
  "version": "1.0.0",
  "checks": {
    "database": {"status": "ok"},
    "ai_provider": {
      "active": "groq",
      "groq": "ok",
      "anthropic": "not_configured"
    },
    "idempiere": {"status": "configured"}
  }
}
```

---

## 16. Mantenimiento

Esta seccion esta dirigida al **equipo de TI de Alimentos Santoni** que administra el sistema en el dia a dia.

### 16.1 Desbloquear Usuarios

Cuando un usuario reporta que no puede acceder al sistema:

**Via Panel de Administracion:**
1. Ir a `/admin`
2. Seleccionar pestana "Seguridad"
3. En la seccion "Cuentas Bloqueadas", hacer clic en "Desbloquear" junto al usuario

**Via API:**
```bash
# Obtener token de admin
TOKEN=$(curl -s -X POST http://localhost/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"..."}' | jq -r '.access_token')

# Listar usuarios bloqueados
curl -s http://localhost/api/admin/security/locked-users \
  -H "Authorization: Bearer $TOKEN"

# Desbloquear usuario (reemplazar ID)
curl -s -X POST http://localhost/api/admin/security/unlock-user/5 \
  -H "Authorization: Bearer $TOKEN"
```

**Nota:** Las cuentas se desbloquean automaticamente despues de 15 minutos.

### 16.2 Revisar IPs Sospechosas

**Via Panel de Administracion:**
1. Ir a `/admin`
2. Seleccionar pestana "Seguridad"
3. Revisar seccion "IPs sospechosas (ultimos 7 dias)"

**Via API:**
```bash
curl -s http://localhost/api/admin/security/overview \
  -H "Authorization: Bearer $TOKEN" | jq '.suspicious_ips'
```

Si se detecta una IP sospechosa repetida, se puede bloquear a nivel de firewall del servidor:
```bash
# Bloquear IP en el firewall (ejemplo con ufw)
sudo ufw deny from <IP_SOSPECHOSA>
```

### 16.3 Renovacion de Certificados SSL

Los certificados Let's Encrypt expiran cada 90 dias. Para renovar:

```bash
cd /opt/santonibot

# Renovar certificado
docker compose run --rm certbot renew

# Reiniciar Nginx para cargar el nuevo certificado
docker compose restart nginx
```

**Automatizacion con cron:**
```bash
# Renovar automaticamente cada semana (solo renueva si faltan menos de 30 dias)
0 3 * * 0 cd /opt/santonibot && docker compose run --rm certbot renew && docker compose restart nginx
```

### 16.4 Verificacion de Backups

```bash
# Listar backups existentes
docker run --rm -v santoni-bot_db_backups:/backups alpine ls -lh /backups/

# Verificar integridad del ultimo backup
docker run --rm -v santoni-bot_db_backups:/backups alpine sh -c \
  'LATEST=$(ls -t /backups/santonibot_*.sql.gz | head -1); \
   echo "Ultimo backup: $LATEST"; \
   echo "Tamano: $(du -h $LATEST | cut -f1)"; \
   zcat $LATEST | head -5'
```

### 16.5 Crear Usuarios Nuevos

**Via Panel de Administracion:**
1. Ir a `/admin`
2. Seleccionar pestana "Usuarios"
3. Hacer clic en "Nuevo Usuario"
4. Completar: nombre, username, email, contrasena, rol, departamento
5. Hacer clic en "Crear"

**Requisitos de contrasena para comunicar al usuario:**
- Minimo 8 caracteres
- Al menos 1 mayuscula, 1 minuscula, 1 numero
- Al menos 1 caracter especial (!@#$%^&*)

### 16.6 Reiniciar Servicios

```bash
cd /opt/santonibot

# Reiniciar todo
docker-compose restart

# Reiniciar solo el backend
docker-compose restart backend

# Reiniciar solo el frontend
docker-compose restart frontend

# Ver estado de todos los servicios
docker-compose ps

# Ver logs en tiempo real
docker-compose logs -f
```

### 16.7 Verificar Estado del Sistema

```bash
# Health check basico
curl http://localhost/api/health

# Health check detallado (requiere token)
curl http://localhost/api/health/detailed \
  -H "Authorization: Bearer $TOKEN"

# Estado de contenedores Docker
docker-compose ps

# Uso de recursos
docker stats --no-stream
```

### 16.8 Problemas Comunes y Soluciones

| Problema | Posible Causa | Solucion |
|---|---|---|
| "Token invalido o expirado" | JWT expirado | El usuario debe volver a iniciar sesion |
| "Cuenta bloqueada" | 5 intentos fallidos | Esperar 15 min o desbloquear desde admin |
| Error 502 en chat | Groq API no disponible | Verificar GROQ_API_KEY y conexion a internet |
| Graficas no aparecen | Tabla con <3 filas | Normal: se requieren 3+ filas para generar grafica |
| Frontend no carga | Contenedor frontend caido | `docker-compose restart frontend` |
| BD interna no responde | Contenedor db caido | `docker-compose restart db` |
| RAG no funciona | ChromaDB no disponible | `docker-compose restart chromadb` (el sistema funciona sin RAG) |
| "Error al consultar el modelo de IA" | API key invalida o servicio caido | Verificar API keys en `.env` y reiniciar backend |

### 16.9 Actualizacion del Sistema

Cuando OVA Agency entrega una nueva version:

```bash
cd /opt/santonibot

# 1. Backup de seguridad
docker compose run --rm backup

# 2. Obtener nueva version
git pull origin main

# 3. Reconstruir
docker-compose build --no-cache

# 4. Reiniciar
docker-compose up -d

# 5. Migraciones (si las hay)
docker-compose exec backend alembic upgrade head

# 6. Verificar
curl http://localhost/api/health
docker-compose logs --tail=50 backend
```

### 16.10 Contacto de Soporte

Para problemas que no se puedan resolver con esta guia, contactar a **OVA Agency** proporcionando:
- Descripcion del problema
- Capturas de pantalla (si aplica)
- Logs relevantes (`docker-compose logs --tail=200 backend`)
- Fecha y hora del incidente
- Usuario afectado

---

## Apendice A: Estructura de Directorios

```
Santoni-Bot/
|-- docker-compose.yml          # Orquestacion de servicios
|-- .env.example                # Plantilla de variables de entorno
|-- CLAUDE.md                   # Instrucciones del proyecto
|-- nginx/
|   |-- nginx.conf              # Configuracion de Nginx
|-- backend/
|   |-- Dockerfile
|   |-- app/
|   |   |-- main.py             # Punto de entrada FastAPI
|   |   |-- config.py           # Configuracion (pydantic-settings)
|   |   |-- database.py         # Conexion a base de datos
|   |   |-- api/
|   |   |   |-- routes/
|   |   |       |-- auth.py     # Autenticacion, 2FA, cambio contrasena
|   |   |       |-- chat.py     # Chat con agentes IA
|   |   |       |-- users.py    # CRUD de usuarios (admin)
|   |   |       |-- admin.py    # Estadisticas, auditoria, seguridad
|   |   |       |-- export.py   # Exportacion CSV/Excel/PDF
|   |   |       |-- knowledge.py # Base de conocimiento RAG
|   |   |       |-- documents.py # Carga de documentos
|   |   |-- agents/
|   |   |   |-- base_agent.py   # Clase base para todos los agentes
|   |   |   |-- orchestrator.py # Orquestador (clasificacion de intenciones)
|   |   |   |-- finanzas.py     # Agente de Finanzas
|   |   |   |-- contabilidad.py # Agente de Contabilidad
|   |   |   |-- ventas.py       # Agente de Ventas
|   |   |   |-- rrhh.py         # Agente de RRHH
|   |   |   |-- produccion.py   # Agente de Produccion
|   |   |   |-- compras_insumos.py      # Agente Compras Insumos
|   |   |   |-- compras_productores.py  # Agente Compras Productores
|   |   |-- models/
|   |   |   |-- user.py         # Modelo User (roles, departamentos)
|   |   |   |-- conversation.py # Modelos Conversation y Message
|   |   |   |-- audit.py        # Modelo AuditLog
|   |   |   |-- demo_data.py    # 16 tablas demo (simulacion iDempiere)
|   |   |-- schemas/
|   |   |   |-- user.py         # Schemas Pydantic (login, TOTP, password)
|   |   |   |-- chat.py         # Schemas de chat
|   |   |-- services/
|   |   |   |-- auth.py         # JWT, bcrypt, autenticacion
|   |   |   |-- audit.py        # Servicio de auditoria
|   |   |   |-- query_service.py # Consultas SQL pre-construidas
|   |   |   |-- export_service.py # Generacion CSV/Excel/PDF
|   |   |   |-- rag_service.py  # Servicio RAG con ChromaDB
|   |   |   |-- llm_factory.py  # Factory de instancias LLM
|   |   |-- middleware/
|   |   |   |-- auth.py         # Middleware de autenticacion JWT
|   |   |-- utils/
|   |       |-- seed.py         # Creacion de usuario admin inicial
|   |       |-- seed_demo.py    # Carga de datos demo
|   |       |-- logger.py       # Configuracion de logging
|-- frontend/
|   |-- Dockerfile
|   |-- package.json
|   |-- src/
|   |   |-- app/
|   |   |   |-- page.tsx        # Pagina raiz (redirect)
|   |   |   |-- login/page.tsx  # Pagina de login
|   |   |   |-- chat/page.tsx   # Pagina principal de chat
|   |   |   |-- admin/page.tsx  # Panel de administracion
|   |   |-- components/
|   |   |   |-- chat/
|   |   |   |   |-- ChatWindow.tsx    # Ventana de chat
|   |   |   |   |-- ChatMessage.tsx   # Mensaje individual
|   |   |   |   |-- ChartRenderer.tsx # Graficas Recharts
|   |   |   |-- layout/
|   |   |       |-- Sidebar.tsx       # Sidebar con conversaciones
|   |   |-- hooks/
|   |   |   |-- useAuth.ts     # Hook de autenticacion + inactividad
|   |   |-- lib/
|   |   |   |-- api.ts         # Cliente API (fetch wrapper)
|   |   |-- types/
|   |       |-- index.ts       # Tipos TypeScript
|-- docs/
    |-- DOCUMENTO_TECNICO.md   # Este documento
```

---

## Apendice B: Comandos Utiles

```bash
# ---- Desarrollo ----
cd backend && uvicorn app.main:app --reload       # Backend en modo desarrollo
cd frontend && npm run dev                         # Frontend en modo desarrollo
cd backend && pytest                               # Tests backend
cd frontend && npm test                            # Tests frontend
cd backend && alembic upgrade head                 # Migraciones

# ---- Docker ----
docker-compose up -d                               # Levantar todo
docker-compose down                                # Detener todo
docker-compose build --no-cache                    # Reconstruir imagenes
docker-compose logs -f backend                     # Logs del backend
docker-compose logs -f frontend                    # Logs del frontend
docker-compose ps                                  # Estado de servicios
docker-compose exec backend bash                   # Shell en el backend
docker stats --no-stream                           # Uso de recursos

# ---- Backup ----
docker compose run --rm backup                     # Ejecutar backup
docker run --rm -v santoni-bot_db_backups:/b alpine ls -lh /b/  # Listar backups

# ---- SSL ----
docker compose run --rm certbot certonly --webroot -w /var/www/certbot -d dominio.com
docker compose run --rm certbot renew
docker compose restart nginx

# ---- Base de Datos ----
docker-compose exec db psql -U santonibot -d santonibot  # Shell PostgreSQL
docker-compose exec db pg_dump -U santonibot santonibot > backup.sql  # Dump manual

# ---- Seguridad ----
python3 -c "import secrets; print(secrets.token_urlsafe(64))"  # Generar SECRET_KEY
```

---

*Documento generado para SantoniBot v1.0.0 - Alimentos Santoni, C.A. - Desarrollado por OVA Agency*
