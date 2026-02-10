# Manual de Pruebas Locales - SantoniBot

## Requisitos Previos

### 1. Instalar Docker Desktop

Si ya lo tienes instalado, salta al paso 2.

**Windows:**
1. Ir a https://www.docker.com/products/docker-desktop/
2. Clic en **"Download for Windows"**
3. Ejecutar el instalador `.exe` descargado
4. En el instalador: dejar marcada la opción **"Use WSL 2 instead of Hyper-V"**
5. Clic en **"Ok"** → esperar instalación → **"Close and restart"**
6. Después de reiniciar, Docker Desktop se abre automáticamente
7. Aceptar los términos de servicio
8. Esperar a que el ícono de la ballena en la barra de tareas diga **"Docker Desktop is running"**

**macOS:**
1. Ir a https://www.docker.com/products/docker-desktop/
2. Clic en **"Download for Mac"** (elegir Apple Chip o Intel según tu Mac)
3. Abrir el `.dmg` descargado
4. Arrastrar Docker al folder **Applications**
5. Abrir Docker desde Applications
6. Autorizar con tu contraseña del Mac cuando lo pida
7. Esperar a que el ícono de la ballena en la barra superior diga **"Docker Desktop is running"**

### 2. Verificar que Docker funciona

Abrir una terminal:
- **Windows:** Buscar "Terminal" o "PowerShell" en el menú Inicio
- **macOS:** Abrir "Terminal" desde Applications → Utilities

Escribir estos comandos uno por uno:
```
docker --version
```
Debe mostrar algo como: `Docker version 27.x.x`

```
docker compose version
```
Debe mostrar algo como: `Docker Compose version v2.x.x`

Si alguno da error, Docker Desktop no está corriendo. Abrirlo desde el menú Inicio (Windows) o Applications (Mac).

### 3. Instalar Git

**Windows:**
1. Ir a https://git-scm.com/download/win
2. Descargar e instalar con todas las opciones por defecto
3. Reiniciar la terminal

**macOS:**
```
xcode-select --install
```
Clic en "Instalar" cuando aparezca el popup.

### 4. Verificar Git
```
git --version
```
Debe mostrar: `git version 2.x.x`

---

## Paso 1: Clonar el Proyecto

### 1.1 Abrir la terminal

- **Windows:** Clic derecho en el Escritorio → "Abrir en Terminal" (o buscar "Terminal" en el menú Inicio)
- **macOS:** Cmd + Espacio → escribir "Terminal" → Enter

### 1.2 Ir a la carpeta donde quieres el proyecto

```
cd Desktop
```
(O cualquier carpeta donde quieras tenerlo)

### 1.3 Clonar el repositorio

```
git clone https://github.com/ovavisionve/Santoni-Bot.git
```

Esperar a que termine. Verás mensajes de progreso.

### 1.4 Entrar a la carpeta del proyecto

```
cd Santoni-Bot
```

### 1.5 Verificar que estás en la carpeta correcta

```
ls
```
Debes ver: `backend`, `frontend`, `docker-compose.yml`, `nginx`, `docs`, `scripts`, etc.

---

## Paso 2: Crear el Archivo de Configuración (.env)

El proyecto necesita un archivo llamado `.env` con la configuración. Vamos a crearlo.

### 2.1 Crear el archivo

1. Dentro de la carpeta `Santoni-Bot`, buscar el archivo llamado **`.env.example`**

   > **Nota Windows:** Si no ves el archivo, es porque Windows oculta archivos que empiezan con punto. En el Explorador de Archivos: clic en **"Ver"** (arriba) → marcar **"Elementos ocultos"**

2. **Copiar** ese archivo y **pegar** en la misma carpeta
3. Se crea un archivo llamado `.env.example - copia` (Windows) o `.env.example copy` (Mac)
4. **Renombrarlo** a `.env` (solo punto-env, sin nada más)
   - Windows: Clic derecho → Cambiar nombre → escribir `.env` → Enter → Si pregunta "¿Está seguro?", clic en **Sí**
   - Mac: Clic en el archivo → Enter → escribir `.env` → Enter → Clic en **"Usar ."**

**Alternativa por terminal** (si prefieres):
```
cp .env.example .env
```

### 2.2 Editar el archivo .env

1. **Abrir** el archivo `.env` que acabas de crear:
   - **Clic derecho** sobre el archivo `.env`
   - **"Abrir con"** → elegir **Visual Studio Code**, **Bloc de Notas** (Windows), o **TextEdit** (Mac)
   - Si no ves "Abrir con", clic derecho → **"Abrir con"** → **"Elegir otra aplicación"** → Bloc de Notas

2. **Borrar TODO** el contenido del archivo (Ctrl+A → Suprimir)

3. **Copiar TODO** el siguiente bloque y **pegarlo** en el archivo vacío:

```
APP_NAME=SantoniBot
APP_ENV=development
DEBUG=true
DOMAIN=localhost

SECRET_KEY=mi-clave-secreta-para-pruebas-locales-2026
JWT_ALGORITHM=HS256
JWT_EXPIRATION_MINUTES=480

POSTGRES_HOST=db
POSTGRES_PORT=5432
POSTGRES_DB=santonibot
POSTGRES_USER=santonibot
POSTGRES_PASSWORD=santoni-dev-2026

IDEMPIERE_DB_HOST=192.168.1.73
IDEMPIERE_DB_PORT=5432
IDEMPIERE_DB_NAME=idempiere_produccion
IDEMPIERE_DB_USER=ova
IDEMPIERE_DB_PASSWORD=

GROQ_API_KEY=PEGAR-TU-API-KEY-DE-GROQ-AQUI
GROQ_MODEL=llama-3.1-70b-versatile

ANTHROPIC_API_KEY=
ANTHROPIC_MODEL=claude-sonnet-4-5-20250929

CHROMA_HOST=chromadb
CHROMA_PORT=8001

NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_APP_NAME=SantoniBot
```

4. **Ahora, cambia UNA sola cosa:** buscar la línea que dice:
   ```
   GROQ_API_KEY=PEGAR-TU-API-KEY-DE-GROQ-AQUI
   ```
   Y reemplazar `PEGAR-TU-API-KEY-DE-GROQ-AQUI` con la API key real de Groq que tenemos del proyecto (empieza con `gsk_`). Debe quedar algo así:
   ```
   GROQ_API_KEY=gsk_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
   ```

5. **Guardar** el archivo:
   - **Windows:** Ctrl + S
   - **Mac:** Cmd + S

6. **Cerrar** el editor

> **Importante:** La GROQ_API_KEY es lo único que NECESITAS cambiar. Todo lo demás ya está listo para funcionar. Si no pones la key de Groq, la app levanta pero los agentes no pueden responder preguntas.

---

## Paso 3: Levantar el Proyecto con Docker

### 3.1 Asegurarse de que Docker Desktop está corriendo

**Windows:**
- Buscar "Docker Desktop" en el menú Inicio y abrirlo
- Esperar a que el ícono de la ballena (abajo a la derecha, en la barra de tareas) esté quieto (sin animación)
- Si dice "Docker Desktop is starting...", esperar

**macOS:**
- Abrir Docker desde Applications
- Esperar a que el ícono de la ballena en la barra superior esté quieto

### 3.2 Volver a la terminal donde estás en la carpeta del proyecto

Verificar que estás en la carpeta correcta:
```
ls docker-compose.yml
```
Si dice "No such file", volver a la carpeta:
```
cd Desktop/Santoni-Bot
```

### 3.3 Construir y levantar los contenedores

```
docker compose up -d --build
```

**Qué pasa ahora:**
- Docker descarga las imágenes necesarias (PostgreSQL, ChromaDB, Node, Python, Nginx)
- Esto puede tardar **5-15 minutos la primera vez** (depende de tu internet)
- Verás muchas líneas de texto en la terminal. Es normal.
- Al final debe decir algo como:
  ```
  ✔ Container santoni-bot-db-1        Started
  ✔ Container santoni-bot-chromadb-1   Started
  ✔ Container santoni-bot-backend-1    Started
  ✔ Container santoni-bot-frontend-1   Started
  ✔ Container santoni-bot-nginx-1      Started
  ```

### 3.4 Verificar en Docker Desktop

1. Abrir **Docker Desktop**
2. Clic en **"Containers"** en la barra lateral izquierda
3. Verás un grupo llamado **"santoni-bot"** (o similar)
4. Clic en la flechita para expandir
5. Debes ver **5 contenedores**, todos con un punto **verde** (Running):

   | Contenedor | Estado esperado |
   |-----------|----------------|
   | santoni-bot-db-1 | 🟢 Running |
   | santoni-bot-chromadb-1 | 🟢 Running |
   | santoni-bot-backend-1 | 🟢 Running |
   | santoni-bot-frontend-1 | 🟢 Running |
   | santoni-bot-nginx-1 | 🟢 Running |

**Si algún contenedor tiene punto rojo o amarillo:**
- Clic en el nombre del contenedor
- Clic en la pestaña **"Logs"** (arriba)
- Leer el error. Los más comunes:
  - `"password authentication failed"` → La POSTGRES_PASSWORD en .env no coincide. Solución: borrar volúmenes (Paso 8.1)
  - `"port is already allocated"` → Otro programa usa ese puerto. Cerrar ese programa o cambiar el puerto en docker-compose.yml
  - `"GROQ_API_KEY"` error → No pusiste la API key en .env

### 3.5 Ver los logs del backend (para ver la contraseña admin)

En la terminal:
```
docker compose logs backend | head -50
```

O en **Docker Desktop:**
1. Clic en el contenedor **"santoni-bot-backend-1"**
2. Se abre la pestaña **"Logs"** automáticamente
3. Buscar la línea que dice:
   ```
   Admin user created with generated password. Temporary password: XXXXXXXXX
   ```
4. **Copiar esa contraseña.** La vas a necesitar para hacer login.

> **Importante:** El password admin se genera automáticamente la primera vez. Aparece UNA SOLA VEZ en los logs. Si lo pierdes, necesitas borrar la base de datos y reiniciar (Paso 8.1).

---

## Paso 4: Verificar que el API funciona

### 4.1 En el navegador

Abrir esta URL en Chrome/Firefox/Edge:
```
http://localhost:8000/api/health
```

Debes ver:
```json
{"status":"ok","app":"SantoniBot","version":"1.0.0"}
```

Si ves eso, el backend está funcionando.

### 4.2 Ver la documentación del API (modo desarrollo)

Abrir en el navegador:
```
http://localhost:8000/api/docs
```

Verás la documentación Swagger con todos los endpoints. Esto solo funciona con `DEBUG=true`.

---

## Paso 5: Entrar a la Aplicación

### 5.1 Abrir el frontend

Abrir en el navegador:
```
http://localhost:3000
```

Verás la pantalla de login de SantoniBot con el logo naranja.

### 5.2 Hacer login

1. En el campo **"Usuario"**: escribir `admin`
2. En el campo **"Contraseña"**: pegar la contraseña que copiaste de los logs (Paso 3.5)
3. Clic en el botón **"Ingresar"**

Si todo está bien, te lleva a la pantalla de chat.

**Si dice "Credenciales inválidas":**
- Verificar que copiaste bien la contraseña de los logs
- Verificar que no hay espacios extras al inicio/final

### 5.3 Qué debes ver

La pantalla de chat tiene 3 áreas:
- **Izquierda:** Barra lateral con "Nueva conversación", tu nombre, "Administración"
- **Centro:** Área de chat con sugerencias de preguntas
- **Abajo:** Campo de texto para escribir tu pregunta

---

## Paso 6: Probar los Agentes de IA

### 6.1 Hacer tu primera pregunta

1. Clic en el campo de texto que dice "Escribe tu consulta..."
2. Escribir: `¿Cuáles son los top 10 clientes por facturación?`
3. Presionar **Enter** (o clic en el botón de enviar)
4. Esperar la respuesta (verás puntos animados mientras procesa, 5-15 segundos)

**Resultado esperado:** Una tabla con los 10 clientes con más facturación, generada por el Agente de Ventas.

### 6.2 Probar cada departamento

Copia y pega estas preguntas una por una. Clic en **"Nueva conversación"** (barra lateral) entre cada una para mantener el contexto limpio:

**Ventas** (clic en "Nueva conversación" primero):
```
¿Cuáles son los top 10 clientes por facturación en 2025?
```

**Finanzas** (clic en "Nueva conversación" primero):
```
¿Cuál es el flujo de caja actual?
```

**Contabilidad** (clic en "Nueva conversación" primero):
```
Dame el balance general del primer trimestre 2025
```

**RRHH** (clic en "Nueva conversación" primero):
```
¿Cuántos empleados activos hay y cuál es la nómina?
```

**Producción** (clic en "Nueva conversación" primero):
```
¿Cuál es la producción diaria de esta semana?
```

**Compras Insumos** (clic en "Nueva conversación" primero):
```
¿Cuáles son las órdenes de compra pendientes?
```

**Compras Productores** (clic en "Nueva conversación" primero):
```
¿Cuánto arroz hemos comprado en 2025?
```

### 6.3 Qué verificar en cada respuesta

- Que aparece una etiqueta azul con el nombre del agente (ej: "Agente de Ventas")
- Que la respuesta tiene datos con números, tablas o resúmenes
- Que la respuesta está en español
- Que los datos demo se ven realistas (clientes venezolanos, montos en Bs., etc.)

---

## Paso 7: Probar Exportación

### 7.1 Generar una respuesta con tabla

1. Escribir: `Dame un ranking de los 10 principales clientes`
2. Esperar la respuesta

### 7.2 Exportar a CSV

1. En la respuesta del bot, buscar los botones debajo del mensaje
2. Clic en el botón **"CSV"**
3. Se descarga un archivo `.csv`
4. Abrirlo con Excel o Google Sheets
5. Verificar que los datos de la tabla están completos

### 7.3 Exportar a Excel

1. Clic en el botón **"Excel"**
2. Se descarga un archivo `.xlsx`
3. Abrirlo con Excel
4. Verificar: encabezado naranja "SantoniBot - Reporte", tabla con datos

### 7.4 Exportar a PDF

1. Clic en el botón **"PDF"**
2. Se descarga un archivo `.pdf`
3. Abrirlo con cualquier lector de PDF
4. Verificar: logo SantoniBot, tabla formateada, colores naranja

---

## Paso 8: Probar Panel de Administración

### 8.1 Acceder al panel

1. En la barra lateral izquierda, clic en **"Administración"**
2. Se abre el panel de admin con 3 pestañas

### 8.2 Pestaña "Estadísticas"

- Verás tarjetas con: Total usuarios, Conversaciones, Mensajes
- Un gráfico de uso por agente
- Verificar que los números reflejan las pruebas que hiciste

### 8.3 Pestaña "Usuarios" - Crear un usuario de prueba

1. Clic en la pestaña **"Usuarios"**
2. Clic en el botón **"Nuevo Usuario"**
3. Llenar el formulario:
   - **Usuario:** `vendedor1`
   - **Nombre completo:** `Carlos Prueba`
   - **Email:** `carlos@test.com`
   - **Contraseña:** `Test1234!`
   - **Rol:** `usuario`
   - **Departamento:** `ventas`
4. Clic en **"Crear"**
5. El usuario aparece en la tabla

### 8.4 Probar login con el usuario nuevo

1. Clic en **"Cerrar sesión"** (barra lateral, abajo)
2. En la pantalla de login:
   - Usuario: `vendedor1`
   - Contraseña: `Test1234!`
3. Clic en **"Ingresar"**
4. Verificar:
   - El chat funciona
   - Las sugerencias son de Ventas (porque el usuario es de ventas)
   - NO aparece el link "Administración" (porque no es admin)
   - Si preguntas algo de RRHH, debe decir que no tiene acceso

### 8.5 Pestaña "Auditoría"

1. Volver a loguearte como `admin`
2. Ir a Administración → pestaña **"Auditoría"**
3. Verificar que aparecen las acciones del usuario `vendedor1`

---

## Paso 9: Copiar respuestas

1. Pasar el cursor sobre cualquier respuesta del bot
2. Aparece un ícono de **copiar** en la esquina superior derecha del mensaje
3. Clic en el ícono
4. Se muestra un check verde confirmando que se copió
5. Pegar (Ctrl+V) en cualquier lugar para verificar

---

## Troubleshooting (Solución de Problemas)

### Problema: Docker Desktop dice "Docker Desktop is starting..." y no arranca

**Windows:**
1. Abrir "Servicios" (buscar "services.msc" en el menú Inicio)
2. Buscar "Docker Desktop Service"
3. Clic derecho → "Reiniciar"
4. Esperar 1 minuto
5. Si no funciona, reiniciar el PC

**macOS:**
1. Cerrar Docker Desktop (clic derecho en ícono de ballena → "Quit")
2. Abrirlo de nuevo desde Applications

### Problema: Un contenedor tiene punto rojo en Docker Desktop

1. Clic en el contenedor rojo
2. Ir a pestaña **"Logs"**
3. Leer el error
4. Errores comunes:

| Error en logs | Causa | Solución |
|--------------|-------|----------|
| `password authentication failed` | Password de DB no coincide | Ver "Reinicio limpio" abajo |
| `port is already allocated` | Puerto ocupado | Cerrar otro programa que use el puerto, o cambiar puerto en docker-compose.yml |
| `no such file .env` | Falta el archivo .env | Volver al Paso 2 |
| `GROQ_API_KEY` vacío | No configuraste la key | Editar .env, agregar la key de Groq |
| `Cannot connect to chromadb` | ChromaDB no arrancó | Normal al inicio. Esperar 30 seg y reiniciar backend |

### Problema: La página dice "Unable to connect" o no carga

1. Verificar que los contenedores están corriendo (Docker Desktop → Containers → todos verdes)
2. Esperar 30 segundos después de levantar (el frontend tarda en compilar)
3. Probar http://localhost:3000 (frontend directo) en vez de http://localhost (nginx)

### Problema: El bot no responde o da error

1. Verificar la GROQ_API_KEY en el .env
2. Ver los logs del backend:
   - Docker Desktop → clic en contenedor "backend" → Logs
   - O en terminal: `docker compose logs backend --tail 50`
3. Si dice "rate limit", esperar 1 minuto (Groq tiene límites en el free tier)

### Problema: "Credenciales inválidas" al hacer login

1. La contraseña admin se genera aleatoriamente la primera vez
2. Buscarla en los logs del backend (Paso 3.5)
3. Si ya no la ves en los logs, hacer reinicio limpio (siguiente sección)

### Reinicio limpio (borra todo y empieza de nuevo)

**Desde la terminal:**
```
docker compose down -v
docker compose up -d --build
```

**Desde Docker Desktop:**
1. Ir a **"Containers"**
2. Buscar el grupo **"santoni-bot"**
3. Clic en el ícono de **Stop** (cuadrado) del grupo completo
4. Clic en el ícono de **Delete** (basura) del grupo completo
5. Ir a **"Volumes"** en la barra lateral
6. Seleccionar todos los volúmenes que digan "santoni-bot"
7. Clic en **"Delete"** (esto borra la base de datos)
8. Volver a la terminal y ejecutar: `docker compose up -d --build`

> **Advertencia:** Esto borra TODOS los datos (usuarios, conversaciones, etc.) y empieza de cero.

---

## Detener el Proyecto

### Desde la terminal:
```
docker compose down
```

### Desde Docker Desktop:
1. Ir a **"Containers"**
2. Buscar el grupo **"santoni-bot"**
3. Clic en el botón **Stop** (ícono de cuadrado)

### Para volver a levantarlo después:

**Desde la terminal:**
```
cd Desktop/Santoni-Bot
docker compose up -d
```

**Desde Docker Desktop:**
1. Ir a **"Containers"**
2. Buscar el grupo **"santoni-bot"**
3. Clic en el botón **Start** (ícono de play ▶)

---

## Datos Demo

El sistema viene con datos demo que se crean automáticamente al iniciar. No necesitas cargar nada manualmente.

| Tipo | Cantidad | Ejemplos |
|------|----------|----------|
| Clientes | 50 | Distribuidora Caracas, Abastos El Nacional, Supermercado Miranda... |
| Facturas de venta | 200 | Facturas 2024-2025 con montos en Bs. |
| Cobranzas | 150 | Pagos parciales y completos |
| Empleados | 45 | Nómina completa con cargos |
| Productores | 80 | 60 de arroz + 20 de maíz (estados Portuguesa, Guárico, Barinas) |
| Órdenes de producción | Varias | Arroz blanco, harina de maíz |
| Proveedores de insumos | Varios | Empaques, químicos, repuestos |
| Cuentas bancarias | Varias | Banesco, Mercantil, Provincial |

Los datos se recrean cada vez que el backend arranca **si las tablas están vacías**. Si quieres datos frescos, haz un reinicio limpio (Troubleshooting).

> **No necesitas conexión a iDempiere ni a Santoni para probar.** Todo funciona 100% local con datos demo.

---

## Resumen de URLs

| Qué | URL | Cuándo usar |
|-----|-----|-------------|
| Frontend (app principal) | http://localhost:3000 | Siempre |
| Frontend vía Nginx | http://localhost | Alternativa |
| API Backend | http://localhost:8000 | Para verificar API |
| API Docs (Swagger) | http://localhost:8000/api/docs | Para explorar endpoints |
| Health Check | http://localhost:8000/api/health | Para verificar que funciona |

---

## Checklist de Pruebas

Marca cada ítem cuando lo hayas probado:

- [ ] Docker Desktop corriendo (ballena verde)
- [ ] `docker compose up -d --build` completado sin errores
- [ ] Los 5 contenedores están verdes en Docker Desktop
- [ ] http://localhost:8000/api/health devuelve `{"status":"ok"}`
- [ ] http://localhost:3000 muestra pantalla de login
- [ ] Login con usuario admin funciona
- [ ] Chat: pregunta de Ventas responde con datos
- [ ] Chat: pregunta de Finanzas responde con datos
- [ ] Chat: pregunta de Contabilidad responde con datos
- [ ] Chat: pregunta de RRHH responde con datos
- [ ] Chat: pregunta de Producción responde con datos
- [ ] Chat: pregunta de Compras Insumos responde con datos
- [ ] Chat: pregunta de Compras Productores responde con datos
- [ ] Exportar a CSV funciona
- [ ] Exportar a Excel funciona
- [ ] Exportar a PDF funciona
- [ ] Copiar respuesta al portapapeles funciona
- [ ] Panel de Administración → Estadísticas carga
- [ ] Panel de Administración → Crear usuario nuevo funciona
- [ ] Login con usuario nuevo funciona
- [ ] Usuario nuevo NO ve "Administración"
- [ ] Usuario nuevo NO puede consultar otros departamentos
- [ ] Panel de Administración → Auditoría muestra acciones
- [ ] Nueva conversación funciona
- [ ] Eliminar conversación funciona
- [ ] Buscar conversación en sidebar funciona
- [ ] Cerrar sesión funciona
