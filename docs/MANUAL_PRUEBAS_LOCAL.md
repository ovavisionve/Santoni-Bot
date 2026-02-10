# Manual de Pruebas Locales - SantoniBot

## Requisitos Previos

### Software necesario
| Software | Versión mínima | Verificar con |
|----------|----------------|---------------|
| Docker Desktop | 24.x+ | `docker --version` |
| Docker Compose | 2.x+ | `docker compose version` |
| Git | 2.x+ | `git --version` |
| Node.js (opcional) | 20.x+ | `node --version` |
| Python (opcional) | 3.12+ | `python3 --version` |

> **Nota:** Node.js y Python son opcionales si ejecutas todo con Docker. Solo se necesitan para desarrollo sin Docker.

---

## Opción 1: Ejecución con Docker (Recomendada)

### Paso 1 - Clonar el repositorio
```bash
git clone <url-del-repo> Santoni-Bot
cd Santoni-Bot
```

### Paso 2 - Configurar variables de entorno
```bash
cp .env.example .env
```

Editar `.env` con estos valores mínimos para pruebas:
```env
# General
APP_NAME=SantoniBot
APP_ENV=development
DEBUG=true

# Backend
SECRET_KEY=mi-clave-secreta-de-prueba-32-chars-min
JWT_ALGORITHM=HS256
JWT_EXPIRATION_MINUTES=480

# Database interna (estos valores funcionan tal cual con Docker)
POSTGRES_HOST=db
POSTGRES_PORT=5432
POSTGRES_DB=santonibot
POSTGRES_USER=santonibot
POSTGRES_PASSWORD=santoni-dev-2026

# iDempiere - NO NECESARIO para pruebas locales
# Los agentes usan datos demo automáticamente
IDEMPIERE_DB_HOST=192.168.1.73
IDEMPIERE_DB_PORT=5432
IDEMPIERE_DB_NAME=idempiere_produccion
IDEMPIERE_DB_USER=ova
IDEMPIERE_DB_PASSWORD=

# AI - NECESARIO para que los agentes generen respuestas
GROQ_API_KEY=<tu-groq-api-key-aqui>
GROQ_MODEL=llama-3.1-70b-versatile

# Claude (opcional)
ANTHROPIC_API_KEY=
ANTHROPIC_MODEL=claude-sonnet-4-5-20250929

# ChromaDB
CHROMA_HOST=chromadb
CHROMA_PORT=8001

# Frontend
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_APP_NAME=SantoniBot

# Nginx
DOMAIN=localhost
```

### Paso 3 - Levantar servicios
```bash
docker compose up -d
```

Esto levanta 5 servicios:
| Servicio | Puerto | URL |
|----------|--------|-----|
| PostgreSQL 16 | 5433 (host) → 5432 (container) | - |
| ChromaDB | 8001 | http://localhost:8001 |
| Backend (FastAPI) | 8000 | http://localhost:8000 |
| Frontend (Next.js) | 3000 | http://localhost:3000 |
| Nginx | 80/443 | http://localhost |

### Paso 4 - Verificar que todo está corriendo
```bash
# Ver estado de contenedores
docker compose ps

# Ver logs (todos)
docker compose logs -f

# Ver logs de un servicio específico
docker compose logs -f backend
```

### Paso 5 - Verificar API
```bash
# Health check
curl http://localhost:8000/api/health

# Respuesta esperada:
# {"status":"ok","app":"SantoniBot","version":"1.0.0"}
```

### Paso 6 - Acceder a la aplicación
1. Abrir **http://localhost:3000** (o http://localhost vía Nginx)
2. Login con credenciales de admin:
   - **Usuario:** `admin`
   - **Contraseña:** `SantoniAdmin2026!`
3. Ya puedes chatear con los agentes

### Paso 7 - Probar los agentes
Mensajes de prueba por departamento:

| Agente | Mensaje de prueba |
|--------|-------------------|
| Ventas | "¿Cuáles son los top 10 clientes por facturación en 2025?" |
| Ventas | "Muéstrame las cobranzas del mes de enero 2025" |
| Finanzas | "¿Cuál es el flujo de caja actual?" |
| Contabilidad | "Dame el balance general del primer trimestre 2025" |
| RRHH | "¿Cuántos empleados activos hay y cuál es la nómina?" |
| Producción | "¿Cuál es la producción diaria de esta semana?" |
| Compras Insumos | "¿Cuáles son las órdenes de compra pendientes?" |
| Compras Productores | "¿Cuánto arroz hemos comprado en 2025?" |

### Paso 8 - Probar exportación
1. Haz una pregunta que genere una tabla (ej: "top 10 clientes")
2. En la respuesta del bot, verás botones de exportación: CSV, Excel, PDF
3. Haz clic en cualquiera para descargar

### Paso 9 - Probar panel de administración
1. Ir a http://localhost:3000/admin
2. Pestañas disponibles:
   - **Estadísticas**: métricas de uso, gráficos por agente
   - **Usuarios**: crear/editar/eliminar usuarios
   - **Auditoría**: logs de acciones

---

## Opción 2: Ejecución sin Docker (Desarrollo)

### Backend
```bash
cd backend

# Crear entorno virtual
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
# .\venv\Scripts\activate  # Windows

# Instalar dependencias
pip install -r requirements.txt

# Necesitas PostgreSQL corriendo localmente
# Actualizar POSTGRES_HOST=localhost en .env

# Ejecutar
uvicorn app.main:app --reload --port 8000
```

### Frontend
```bash
cd frontend

# Instalar dependencias
npm install

# Ejecutar en modo desarrollo
npm run dev
```

### Bases de datos locales
```bash
# PostgreSQL con Docker (sin levantar toda la stack)
docker run -d \
  --name santonibot-db \
  -e POSTGRES_DB=santonibot \
  -e POSTGRES_USER=santonibot \
  -e POSTGRES_PASSWORD=santoni-dev-2026 \
  -p 5432:5432 \
  postgres:16-alpine

# ChromaDB con Docker
docker run -d \
  --name santonibot-chroma \
  -e ANONYMIZED_TELEMETRY=false \
  -p 8001:8000 \
  chromadb/chroma:latest
```

---

## Opción 3: Deploy en Vercel (Solo Frontend)

> **Importante:** Vercel solo sirve para el frontend (Next.js). El backend necesita un servidor propio o un servicio como Railway/Render.

### Frontend en Vercel

1. **Instalar Vercel CLI** (opcional):
   ```bash
   npm i -g vercel
   ```

2. **Desde el dashboard de Vercel:**
   - Ir a https://vercel.com/new
   - Importar el repositorio de GitHub
   - **Root Directory:** `frontend`
   - **Framework Preset:** Next.js
   - **Environment Variables:**
     ```
     NEXT_PUBLIC_API_URL=https://tu-backend-url.com
     NEXT_PUBLIC_APP_NAME=SantoniBot
     ```
   - Click "Deploy"

3. **Desde CLI:**
   ```bash
   cd frontend
   vercel --prod
   ```

### Backend - Opciones complementarias

Si quieres el backend también en la nube para pruebas:

| Servicio | Gratis | Notas |
|----------|--------|-------|
| Railway | Sí (limitado) | Soporta Docker, PostgreSQL incluido |
| Render | Sí (limitado) | Free tier con cold starts |
| Fly.io | Sí (limitado) | Buen soporte Docker |
| VM Santoni | N/A | Producción final |

> **Recomendación para pruebas:** Usar Docker local (Opción 1). Para demos al cliente, puedes subir el frontend a Vercel apuntando al backend en tu máquina vía ngrok o similar.

---

## Troubleshooting

### El backend no arranca
```bash
# Ver logs detallados
docker compose logs backend

# Causa común: la DB aún no está lista
# Solución: reiniciar backend
docker compose restart backend
```

### Error de conexión a la base de datos
```bash
# Verificar que PostgreSQL está corriendo
docker compose exec db pg_isready -U santonibot

# Conectarse directamente
docker compose exec db psql -U santonibot
```

### El frontend no conecta con el backend
```bash
# Verificar que NEXT_PUBLIC_API_URL apunta correctamente
# En .env: NEXT_PUBLIC_API_URL=http://localhost:8000

# Si usas Nginx: NEXT_PUBLIC_API_URL=http://localhost
```

### Error de CORS
Si ves errores de CORS en la consola del navegador, verifica que el origen está en la lista de `allow_origins` en `backend/app/main.py`.

### Los agentes no responden / error de Groq
```bash
# Verificar que GROQ_API_KEY está configurada
docker compose exec backend env | grep GROQ

# Probar la API key directamente
curl https://api.groq.com/openai/v1/models \
  -H "Authorization: Bearer $GROQ_API_KEY"
```

### Rebuild completo
```bash
# Si algo se rompió, rebuild desde cero
docker compose down -v  # -v borra los volúmenes (¡borra datos!)
docker compose build --no-cache
docker compose up -d
```

---

## Datos Demo

El sistema viene con datos demo precargados que se crean automáticamente al iniciar:

| Tipo | Cantidad | Ejemplo |
|------|----------|---------|
| Clientes | 50 | Distribuidora Caracas, Abastos El Nacional... |
| Facturas de venta | 200 | Facturas 2024-2025 |
| Cobranzas | 150 | Pagos parciales y completos |
| Empleados | 45 | Nómina completa |
| Productores | 80 | 60 arroz + 20 maíz |
| Órdenes de producción | Varias | Arroz, harina de maíz |
| Proveedores de insumos | Varios | Empaques, químicos, repuestos |
| Cuentas bancarias | Varias | Banesco, Mercantil, Provincial |

Los datos son generados con `random.seed(42)` para reproducibilidad. Se recrean cada vez que el backend arranca si las tablas están vacías.

> **No necesitas conexión a iDempiere para probar.** Todo funciona con datos demo.
