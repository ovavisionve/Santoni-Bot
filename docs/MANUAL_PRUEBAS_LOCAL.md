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
GROQ_MODEL=llama-3.3-70b-versatile

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

### 3.1 Abrir Docker Desktop

**Windows:**
1. Clic en el botón de **Inicio** de Windows (abajo a la izquierda)
2. Escribir `Docker Desktop`
3. Clic en **"Docker Desktop"** cuando aparezca
4. Se abre la ventana de Docker. En la parte inferior izquierda verás un indicador:
   - Si dice **"Engine running"** con un punto verde → perfecto, sigue al paso 3.2
   - Si dice **"Starting..."** → esperar 1-2 minutos hasta que cambie a verde
   - Si no aparece nada, esperar

**macOS:**
1. Abrir **Finder** → **Aplicaciones** → doble clic en **Docker**
2. En la barra superior del Mac, aparece un ícono de ballena 🐳
3. Clic en la ballena → debe decir **"Docker Desktop is running"**
4. Si dice "Starting...", esperar 1-2 minutos

### 3.2 Abrir una Terminal DENTRO de la carpeta del proyecto

Esto es clave. La terminal debe estar **dentro de la carpeta Santoni-Bot** para que Docker encuentre los archivos.

**Windows - Forma más fácil:**
1. Abrir el **Explorador de Archivos** (la carpeta amarilla en la barra de tareas)
2. Navegar hasta la carpeta **Santoni-Bot** (donde hiciste el git clone, probablemente en Escritorio)
3. Entrar a la carpeta hasta que veas los archivos: `backend`, `frontend`, `docker-compose.yml`, `.env`, etc.
4. Clic en la **barra de direcciones** (arriba, donde dice la ruta)
5. Escribir `cmd` y presionar **Enter**
6. Se abre una ventana negra de terminal. Ya estás dentro de la carpeta correcta.

**macOS - Forma más fácil:**
1. Abrir **Finder**
2. Navegar hasta la carpeta **Santoni-Bot**
3. Clic derecho en la carpeta → **"Nuevo Terminal en la carpeta"**
   - Si no ves esa opción: abrir Terminal (Cmd+Espacio → "Terminal") y escribir: `cd ~/Desktop/Santoni-Bot` y presionar Enter

**Verificar que estás en el lugar correcto:**

Escribir en la terminal y presionar Enter:
```
dir
```
(En Mac usar `ls` en vez de `dir`)

Debes ver estos archivos en la lista:
```
backend
frontend
docker-compose.yml
.env
nginx
docs
scripts
```

Si NO ves `docker-compose.yml` en la lista, no estás en la carpeta correcta. Volver al punto 1 de esta sección.

### 3.3 Escribir el comando para levantar todo

Copiar este comando, pegarlo en la terminal y presionar **Enter**:

```
docker compose up -d --build
```

> **Cómo pegar en la terminal:**
> - **Windows (cmd):** Clic derecho → "Pegar"
> - **Windows (PowerShell/Terminal):** Ctrl + V
> - **macOS:** Cmd + V

### 3.4 Qué pasa ahora (esperar)

Después de presionar Enter, Docker empieza a trabajar:

1. **Primero** descarga las imágenes (PostgreSQL, Python, Node.js, etc.)
   - Verás líneas como `Pulling db...`, `Pulling backend...`, `Downloading...`
   - **Esto tarda 5-15 minutos la primera vez** (depende de tu internet)
   - Es normal ver muchas líneas de texto. No tocar nada, dejar que termine.

2. **Después** construye los contenedores
   - Verás líneas como `Building backend...`, `Step 1/8...`
   - Puede tardar 3-5 minutos más

3. **Al final** levanta todo. Debes ver algo como esto:
   ```
   ✔ Container santoni-bot-db-1        Started
   ✔ Container santoni-bot-chromadb-1   Started
   ✔ Container santoni-bot-backend-1    Started
   ✔ Container santoni-bot-frontend-1   Started
   ✔ Container santoni-bot-nginx-1      Started
   ```

4. Cuando vuelve a aparecer el cursor parpadeando, **terminó**.

> **Si ves errores en rojo**, no te preocupes todavía. Ve al Paso 3.5 para verificar el estado.

### 3.5 Verificar que todo levantó correctamente

Ahora vamos a **Docker Desktop** para ver si todo está bien:

1. Ir a la ventana de **Docker Desktop** (clic en el ícono de la ballena en la barra de tareas/menú)
2. En la barra lateral izquierda, clic en **"Containers"** (el primer ícono, parece una caja)
3. Verás una fila que dice **"santoni-bot"** con una flechita ▶ a la izquierda
4. **Clic en la flechita ▶** para expandir y ver los 5 contenedores

Debes ver esto:

| Nombre del contenedor | Color del punto | Significa |
|----------------------|-----------------|-----------|
| santoni-bot-db-1 | 🟢 Verde | Base de datos OK |
| santoni-bot-chromadb-1 | 🟢 Verde | Vector DB OK |
| santoni-bot-backend-1 | 🟢 Verde | API del backend OK |
| santoni-bot-frontend-1 | 🟢 Verde | Interfaz web OK |
| santoni-bot-nginx-1 | 🟢 Verde | Proxy web OK |

**Si todos tienen punto verde:** Perfecto. Ve al Paso 3.6.

**Si alguno tiene punto rojo o amarillo:**
1. Clic en el **nombre** del contenedor que tiene el problema (el texto azul)
2. Se abre una nueva vista. Arriba verás pestañas: **Logs**, Inspect, Bind mounts...
3. La pestaña **"Logs"** ya debería estar seleccionada
4. Lee el texto que aparece. Busca líneas en rojo o que digan "error"
5. Los errores más comunes:

| Lo que dice el error | Qué pasó | Cómo arreglarlo |
|---------------------|----------|-----------------|
| `password authentication failed` | El password de la base de datos no coincide | Ir a la sección "Reinicio limpio" al final del manual |
| `port is already allocated` | Otro programa ya usa ese puerto | Cerrar Skype, otro servidor local, o cualquier programa que use el puerto 80, 3000, 5432 u 8000 |
| `no such file or directory: .env` | No creaste el archivo .env | Volver al Paso 2 |
| `Cannot connect to the Docker daemon` | Docker Desktop no está corriendo | Volver al Paso 3.1 |

### 3.6 Buscar la contraseña del administrador

La contraseña del admin se genera automáticamente la primera vez. Necesitas encontrarla en los logs.

**En Docker Desktop:**
1. En la lista de contenedores, clic en **"santoni-bot-backend-1"** (el texto azul)
2. Se abren los **Logs** (registros del backend)
3. Buscar con los ojos una línea que diga algo como:
   ```
   Admin user created with generated password. Temporary password: AbCdEf123456
   ```
4. La parte después de `Temporary password:` es tu contraseña. **Selecciónala con el mouse y cópiala** (Ctrl+C / Cmd+C)
5. **Pegar la contraseña en un lugar seguro** (un archivo de texto, un post-it, etc.). La necesitas en el Paso 5.

> **Si no encuentras la línea:** Usar Ctrl+F (o Cmd+F) dentro de los logs y buscar `password`. Si aún no aparece, esperar 30 segundos (el backend puede estar aún iniciando) y refrescar los logs cerrando y abriendo el contenedor de nuevo.

---

## Paso 4: Verificar que el Sistema Funciona

### 4.1 Abrir el navegador web

1. Abrir **Google Chrome**, **Firefox**, o **Microsoft Edge** (el que uses)

### 4.2 Probar que el backend está funcionando

1. En la **barra de direcciones** del navegador (arriba, donde se escribe la URL)
2. Escribir: `localhost:8000/api/health`
3. Presionar **Enter**
4. Debes ver este texto en la pantalla:
   ```
   {"status":"ok","app":"SantoniBot","version":"1.0.0"}
   ```
5. Si ves eso: **el backend funciona**.

**Si ves "No se puede acceder a este sitio" o "Unable to connect":**
- Esperar 30 segundos más (el backend puede estar iniciando)
- Verificar que los contenedores están verdes en Docker Desktop (Paso 3.5)
- Refrescar la página (F5 o Ctrl+R)

### 4.3 Ver la documentación de la API (opcional, solo si tienes curiosidad)

1. En el navegador, ir a: `localhost:8000/api/docs`
2. Verás una página con todos los endpoints del API documentados (Swagger UI)
3. Esto es solo informativo, no necesitas hacer nada aquí

---

## Paso 5: Entrar a la Aplicación

### 5.1 Abrir SantoniBot

1. En el **navegador**, ir a la barra de direcciones
2. Escribir: `localhost:3000`
3. Presionar **Enter**
4. Debe aparecer la **pantalla de login** de SantoniBot:
   - Fondo con degradado naranja
   - Logo con la letra "S"
   - Campos para "Usuario" y "Contraseña"
   - Botón "Ingresar"

**Si ves una página en blanco o un error:**
- Esperar 1 minuto (el frontend tarda en compilar la primera vez)
- Refrescar la página (F5)
- Verificar que el contenedor `santoni-bot-frontend-1` está verde en Docker Desktop

### 5.2 Hacer login

1. Clic en el campo **"Usuario"**
2. Escribir: `admin`
3. Clic en el campo **"Contraseña"**
4. Pegar la contraseña que copiaste en el Paso 3.6 (Ctrl+V / Cmd+V)
5. Clic en el botón **"Ingresar"**

**Si dice "Credenciales inválidas":**
- La contraseña tiene que ser EXACTA. Verificar que no copiaste un espacio extra al inicio o final
- Volver a Docker Desktop → contenedor backend → Logs → buscar la línea con `Temporary password`
- Si de verdad no encuentras la contraseña, hacer un **Reinicio limpio** (al final del manual) y buscarla de nuevo

### 5.3 Lo que debes ver después del login

Después de hacer login exitoso, llegas a la pantalla principal del chat:

**Barra lateral izquierda:**
- Botón **"Nueva conversación"** (arriba)
- Lista de conversaciones (vacía por ahora)
- Tu nombre: "Administrador SantoniBot"
- Link **"Administración"** (solo visible para admin)
- Botón **"Cerrar sesión"** (abajo)

**Área central:**
- Texto de bienvenida: "Bienvenido a SantoniBot"
- Botones de sugerencias con preguntas de ejemplo
- Campo de texto abajo: "Escribe tu consulta..."

---

## Paso 6: Probar los Agentes de IA

### 6.1 Tu primera pregunta

1. Clic en el **campo de texto** abajo que dice "Escribe tu consulta..."
2. Escribir (o copiar y pegar) esta pregunta:
   ```
   ¿Cuáles son los top 10 clientes por facturación?
   ```
3. Presionar la tecla **Enter** en el teclado
4. Aparecen **tres puntos animados** (el bot está pensando)
5. Esperar **5 a 15 segundos**
6. Aparece la respuesta del bot

**Lo que debes ver en la respuesta:**
- Una etiqueta azul que dice **"Agente de Ventas"** (significa que el sistema detectó que es una pregunta de ventas)
- Una tabla o lista con los clientes principales
- Nombres de empresas venezolanas (son datos demo)
- Montos en bolívares

**Si el bot no responde después de 30 segundos:**
- Verificar que pusiste la GROQ_API_KEY en el archivo .env (Paso 2)
- Ver los logs del backend en Docker Desktop por si hay error

### 6.2 Probar los 7 departamentos

Ahora vamos a probar que cada agente funcione. Para cada pregunta:

1. Primero, clic en **"Nueva conversación"** en la barra lateral izquierda (para empezar limpio)
2. Luego, copiar la pregunta y pegarla en el campo de texto
3. Presionar **Enter**
4. Esperar la respuesta

**Pregunta 1 - Ventas:**
1. Clic en **"Nueva conversación"**
2. Copiar y pegar en el campo de texto:
   ```
   ¿Cuáles son los top 10 clientes por facturación en 2025?
   ```
3. Presionar Enter
4. Verificar que responde el **"Agente de Ventas"** con una tabla de clientes

**Pregunta 2 - Finanzas:**
1. Clic en **"Nueva conversación"**
2. Copiar y pegar:
   ```
   ¿Cuál es el flujo de caja actual?
   ```
3. Presionar Enter
4. Verificar que responde el **"Agente de Finanzas"** con datos bancarios

**Pregunta 3 - Contabilidad:**
1. Clic en **"Nueva conversación"**
2. Copiar y pegar:
   ```
   Dame el balance general del primer trimestre 2025
   ```
3. Presionar Enter
4. Verificar que responde el **"Agente de Contabilidad"**

**Pregunta 4 - RRHH:**
1. Clic en **"Nueva conversación"**
2. Copiar y pegar:
   ```
   ¿Cuántos empleados activos hay y cuál es la nómina?
   ```
3. Presionar Enter
4. Verificar que responde el **"Agente de RRHH"**

**Pregunta 5 - Producción:**
1. Clic en **"Nueva conversación"**
2. Copiar y pegar:
   ```
   ¿Cuál es la producción diaria de esta semana?
   ```
3. Presionar Enter
4. Verificar que responde el **"Agente de Producción"**

**Pregunta 6 - Compras Insumos:**
1. Clic en **"Nueva conversación"**
2. Copiar y pegar:
   ```
   ¿Cuáles son las órdenes de compra pendientes?
   ```
3. Presionar Enter
4. Verificar que responde el **"Agente de Compras Insumos"**

**Pregunta 7 - Compras Productores:**
1. Clic en **"Nueva conversación"**
2. Copiar y pegar:
   ```
   ¿Cuánto arroz hemos comprado en 2025?
   ```
3. Presionar Enter
4. Verificar que responde el **"Agente de Compras Productores"**

### 6.3 Qué verificar en cada respuesta

Después de cada pregunta, verificar estos 4 puntos:
- Aparece una **etiqueta azul** con el nombre del agente correcto
- La respuesta tiene **datos con números** (tablas, listas, resúmenes)
- La respuesta está en **español**
- Los datos se ven realistas (nombres venezolanos, montos en Bs.)

---

## Paso 7: Probar Exportación (CSV, Excel, PDF)

### 7.1 Primero, generar una respuesta que tenga tabla

1. Si no tienes una respuesta con tabla de los pasos anteriores, escribir:
   ```
   Dame un ranking de los 10 principales clientes
   ```
2. Esperar la respuesta. Debe incluir una tabla con datos.

### 7.2 Encontrar los botones de exportación

1. Buscar la respuesta del bot que tiene tabla
2. **Debajo de la respuesta**, verás tres botones pequeños: **CSV**, **Excel**, **PDF**
3. Si no los ves, mover el mouse sobre la respuesta del bot (pueden aparecer al pasar el cursor)

### 7.3 Probar CSV

1. Clic en el botón **"CSV"**
2. El navegador descarga un archivo (aparece abajo en Chrome, o en la carpeta Descargas)
3. Buscar el archivo descargado (se llama algo como `export_123.csv`)
4. Abrirlo haciendo **doble clic** → se abre en Excel o Google Sheets
5. Verificar que la tabla tiene los mismos datos que la respuesta del bot

### 7.4 Probar Excel

1. Clic en el botón **"Excel"**
2. Se descarga un archivo `.xlsx`
3. Abrirlo haciendo **doble clic** → se abre en Excel
4. Verificar:
   - Arriba dice **"SantoniBot - Reporte"** en naranja
   - La tabla tiene encabezados naranjas
   - Los datos coinciden con la respuesta del bot

### 7.5 Probar PDF

1. Clic en el botón **"PDF"**
2. Se descarga un archivo `.pdf`
3. Abrirlo haciendo **doble clic** → se abre en el visor de PDF
4. Verificar:
   - Título **"SantoniBot - Reporte"** en naranja
   - Tabla formateada con colores
   - Nombre del agente y fecha

---

## Paso 8: Probar el Panel de Administración

### 8.1 Entrar al panel

1. Mirar la **barra lateral izquierda** del chat
2. Buscar el link que dice **"Administración"** (cerca del final, antes de "Cerrar sesión")
3. **Clic en "Administración"**
4. Se abre el panel de admin con tres pestañas arriba: **Estadísticas**, **Usuarios**, **Auditoría**

### 8.2 Pestaña "Estadísticas"

Ya debería estar seleccionada por defecto.

1. Verás **tarjetas** con números:
   - Total de usuarios (debería decir 1, porque solo existe el admin)
   - Total de conversaciones (las que hiciste en el paso 6)
   - Total de mensajes
2. Abajo hay un **gráfico** de uso por agente
3. Verificar que los números tienen sentido (si hiciste 7 preguntas, debería haber al menos 7 conversaciones)

### 8.3 Pestaña "Usuarios" - Crear un usuario de prueba

1. Clic en la pestaña **"Usuarios"** (arriba)
2. Verás una tabla con el usuario `admin`
3. Clic en el botón **"Nuevo Usuario"** (arriba a la derecha de la tabla)
4. Se abre un formulario. Llenar así:
   - **Usuario:** escribir `vendedor1`
   - **Nombre completo:** escribir `Carlos Prueba`
   - **Email:** escribir `carlos@test.com`
   - **Contraseña:** escribir `Test1234!`
   - **Rol:** seleccionar `usuario` del menú desplegable
   - **Departamento:** seleccionar `ventas` del menú desplegable
5. Clic en el botón **"Crear"** (o "Guardar")
6. El usuario nuevo **aparece en la tabla** debajo de admin

### 8.4 Probar el login con el usuario nuevo

1. En la barra lateral izquierda, clic en **"Cerrar sesión"** (abajo del todo)
2. Vuelves a la pantalla de login
3. En el campo **"Usuario"**: escribir `vendedor1`
4. En el campo **"Contraseña"**: escribir `Test1234!`
5. Clic en **"Ingresar"**
6. Entras al chat. Ahora verificar estas cosas:
   - Las **sugerencias** son de Ventas (porque el usuario es del departamento de ventas)
   - En la barra lateral izquierda **NO aparece** el link "Administración" (porque no es admin)
   - Hacer una pregunta de ventas: debe funcionar normal
   - Hacer una pregunta de otro departamento (ej: `¿Cuál es la nómina de RRHH?`): **debe decir que no tiene acceso**

### 8.5 Pestaña "Auditoría"

1. Cerrar sesión del usuario `vendedor1`
2. Login de nuevo como `admin` (con la contraseña del Paso 3.6)
3. Ir a **"Administración"**
4. Clic en la pestaña **"Auditoría"**
5. Verás una tabla con todas las acciones: quién hizo qué y cuándo
6. Debe aparecer el login y las consultas del usuario `vendedor1`

---

## Paso 9: Probar copiar respuestas

1. Ir al chat (clic en cualquier conversación en la barra lateral)
2. Buscar una respuesta del bot
3. **Pasar el mouse** por encima de la respuesta del bot (no hacer clic, solo pasar)
4. Aparece un **ícono de copiar** (dos cuadraditos) en la esquina superior derecha del mensaje
5. **Clic en el ícono de copiar**
6. El ícono cambia a un **check verde** por 2 segundos (confirmando que se copió)
7. Abrir cualquier programa (Word, Bloc de Notas, un email) y pegar con **Ctrl+V** (o Cmd+V)
8. Verificar que se pegó el texto de la respuesta

---

## Troubleshooting (Solución de Problemas)

### Problema: Docker Desktop dice "Docker Desktop is starting..." y no arranca

**Windows:**
1. Clic en el botón de Inicio → escribir `services.msc` → Enter
2. En la ventana de Servicios, buscar **"Docker Desktop Service"**
3. Clic derecho sobre él → **"Reiniciar"**
4. Esperar 1 minuto
5. Si no funciona: reiniciar el PC

**macOS:**
1. Clic derecho en el ícono de ballena en la barra superior → **"Quit Docker Desktop"**
2. Esperar 10 segundos
3. Abrir Docker de nuevo desde Aplicaciones

### Problema: Un contenedor tiene punto rojo en Docker Desktop

1. En Docker Desktop → **Containers** → clic en el contenedor rojo
2. Leer los **Logs** que aparecen
3. Buscar la línea con el error. Soluciones comunes:

| Lo que dice | Qué hacer |
|-------------|-----------|
| `password authentication failed` | Hacer "Reinicio limpio" (más abajo) |
| `port is already allocated` | Otro programa usa ese puerto. Cerrar Skype, Zoom, o cualquier servidor local que tengas abierto. O reiniciar el PC. |
| `no such file .env` | No creaste el archivo .env. Volver al Paso 2. |
| `GROQ_API_KEY` / `groq` error | Abrir el .env y verificar que la GROQ_API_KEY tiene un valor real (empieza con gsk_) |
| `Cannot connect to chromadb` | Normal al inicio. Esperar 30 segundos. En Docker Desktop: clic en el contenedor backend → ícono de Restart (flechita circular) |

### Problema: "localhost:3000" dice "No se puede acceder a este sitio"

1. Verificar que Docker Desktop muestra los 5 contenedores en verde
2. Esperar 1 minuto completo (el frontend tarda en compilar la primera vez)
3. Presionar **F5** para refrescar la página
4. Si sigue sin funcionar, probar: `localhost` (sin el :3000)

### Problema: El bot no responde o da error después de escribir una pregunta

1. Abrir Docker Desktop → clic en el contenedor **"backend"** → leer los **Logs**
2. Si dice algo sobre `groq` o `API key`: abrir .env y verificar la GROQ_API_KEY
3. Si dice `rate limit exceeded`: esperar 1 minuto y reintentar (Groq tiene límites de uso)

### Problema: "Credenciales inválidas" al hacer login

1. La contraseña admin se genera automáticamente la primera vez
2. En Docker Desktop → clic en contenedor **"backend"** → Logs → buscar `Temporary password`
3. Si no la encuentras: hacer **Reinicio limpio** (siguiente sección) y buscarla de nuevo

### Reinicio limpio (borra todo y empieza de nuevo)

Usar cuando algo se rompió y quieres empezar desde cero:

**En Docker Desktop:**
1. Ir a **"Containers"** en la barra lateral
2. En la fila **"santoni-bot"**, clic en el botón **Stop** (ícono de cuadrado ⬛)
3. Esperar a que todos los puntos se pongan grises
4. Clic en el botón **Delete** (ícono de basura 🗑️) en la misma fila
5. Confirmar con **"Delete"** en el popup
6. Ahora ir a **"Volumes"** en la barra lateral izquierda (ícono de cilindro)
7. Verás volúmenes que dicen `santoni-bot_postgres_data`, `santoni-bot_chroma_data`, etc.
8. Marcar **todos** los que digan "santoni-bot" (checkbox a la izquierda)
9. Clic en **"Delete"** (arriba)
10. Confirmar

**Ahora volver a levantar:**
1. Ir a la terminal (la misma que usaste en el Paso 3.2, dentro de la carpeta Santoni-Bot)
2. Escribir y presionar Enter:
   ```
   docker compose up -d --build
   ```
3. Esperar a que termine (3-10 minutos)
4. Ir a Docker Desktop → Containers → verificar 5 contenedores verdes
5. Buscar la **nueva contraseña** de admin en los logs del backend (Paso 3.6)

> **Advertencia:** El reinicio limpio borra TODOS los datos: usuarios creados, conversaciones, todo. Empiezas de cero.

---

## Detener el Proyecto (cuando termines de probar)

### Opción A - Desde Docker Desktop:
1. Abrir Docker Desktop
2. Ir a **"Containers"**
3. En la fila **"santoni-bot"**, clic en el botón **Stop** (ícono de cuadrado ⬛)
4. Todos los puntos se ponen grises. El proyecto está detenido.

### Opción B - Desde la terminal:
1. Abrir la terminal dentro de la carpeta Santoni-Bot
2. Escribir:
   ```
   docker compose down
   ```
3. Presionar Enter

### Para volver a levantar otro día:

**Desde Docker Desktop:**
1. Abrir Docker Desktop
2. Ir a **"Containers"**
3. En la fila **"santoni-bot"**, clic en el botón **Start** (ícono de play ▶)
4. Esperar 30 segundos
5. Ir a `localhost:3000` en el navegador

**Desde la terminal:**
1. Abrir la terminal dentro de la carpeta Santoni-Bot
2. Escribir:
   ```
   docker compose up -d
   ```
3. Esperar 30 segundos
4. Ir a `localhost:3000` en el navegador

> **Nota:** No necesitas hacer `--build` cuando vuelves a levantar. Solo usas `--build` la primera vez o después de un reinicio limpio.

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
