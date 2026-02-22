# Manual de Conexion Rutinaria - Servidor SantoniBot

Este documento explica paso a paso como conectarte al servidor donde esta
instalado SantoniBot, verificar que todo funcione y realizar tareas comunes
de mantenimiento.

---

## Datos del Servidor

| Dato | Valor |
|---|---|
| Sistema operativo | Ubuntu Server 25.10 LTS |
| IP del servidor (SantoniBot) | 192.168.1.26 |
| IP del ERP (iDempiere) | 192.168.1.73 |
| RAM | 16 GB |
| CPU | 8 nucleos |
| Disco | 512 GB SSD |
| Usuario SSH | accinproa |
| Contrasena SSH | pTTkL3gHLYmj5$BL1oFq |
| Ruta del proyecto | /opt/santonibot |

## Datos de la VPN (FortiClient)

| Dato | Valor |
|---|---|
| Usuario VPN | OVA |
| Contrasena VPN | Santoni2022$ |

---

## PASO 1: Conectar la VPN (solo si estas FUERA de Santoni)

Si estas en la oficina de Santoni conectado a su red WiFi o cable, puedes
saltar este paso. Si estas en tu casa o en otra oficina, necesitas la VPN.

1. Abre el programa **FortiClient** en tu computador
2. Si no lo tienes instalado, descargalo desde https://www.fortinet.com/support/product-downloads
3. Una vez abierto, ve a la seccion **VPN** (icono de candado a la izquierda)
4. Haz clic en el campo **Usuario** y escribe: `OVA`
5. En el campo **Contrasena** escribe: `Santoni2022$`
6. Haz clic en **Conectar**
7. Espera a que diga **"Conectado"** o muestre un icono verde
8. Si da error, verifica que tengas internet y que las credenciales esten correctas

**Como saber si la VPN esta funcionando:**
- Abre CMD (Paso 2) y escribe: `ping 192.168.1.26`
- Si ves respuestas como `Reply from 192.168.1.26: bytes=32 time=15ms`, la VPN funciona
- Si dice `Request timed out`, la VPN no esta conectada

---

## PASO 2: Abrir la terminal de Windows (CMD)

1. En tu teclado presiona las teclas **Windows + R** al mismo tiempo
   (la tecla Windows es la que tiene el logo de Windows, esta entre Ctrl y Alt)
2. Se abre una ventanita que dice **"Ejecutar"**
3. Escribe: `cmd`
4. Presiona **Enter** o haz clic en **Aceptar**
5. Se abre una ventana negra con letras blancas. Esa es la terminal (CMD)
6. Deberias ver algo como:

```
Microsoft Windows [Version 10.0.xxxxx]
(c) Microsoft Corporation. All rights reserved.

C:\Users\PCELL>
```

Ese `C:\Users\PCELL>` es el "prompt" - significa que esta listo para recibir
comandos. El cursor parpadea al final esperando que escribas.

---

## PASO 3: Conectarse al servidor por SSH

1. En la ventana negra del CMD, escribe exactamente esto:

```
ssh accinproa@192.168.1.26
```

2. Presiona **Enter**

3. La primera vez que te conectes, te preguntara algo asi:

```
The authenticity of host '192.168.1.26' can't be established.
Are you sure you want to continue connecting (yes/no/[fingerprint])?
```

Escribe `yes` y presiona **Enter**. Esto solo pasa la primera vez.

4. Te pedira la contrasena:

```
accinproa@192.168.1.26's password:
```

Escribe: `pTTkL3gHLYmj5$BL1oFq`

**IMPORTANTE**: Cuando escribes la contrasena NO se ven los caracteres en
pantalla. No aparecen asteriscos ni puntos. Parece que no escribes nada,
pero si se esta registrando. Escribe la contrasena completa y presiona **Enter**.

5. Si la contrasena es correcta, veras algo como:

```
Welcome to Ubuntu 25.10 (GNU/Linux ...)
...
accinproa@santonibot:~$
```

Ese `accinproa@santonibot:~$` significa que ya estas DENTRO del servidor.
Todo lo que escribas a partir de ahora se ejecuta en el servidor, no en tu PC.

**Si te da error "Connection refused" o "Connection timed out":**
- Verifica que la VPN este conectada (Paso 1)
- Verifica que escribiste bien la IP: 192.168.1.26
- El servidor podria estar apagado - contacta a IT en Santoni

---

## PASO 4: Ir a la carpeta del proyecto

Una vez dentro del servidor, escribe:

```bash
cd /opt/santonibot
```

Presiona **Enter**. El prompt cambiara a:

```
accinproa@santonibot:/opt/santonibot$
```

Eso confirma que estas en la carpeta correcta. **Todos los comandos de los
pasos siguientes se ejecutan desde esta carpeta.**

---

## PASO 5: Verificar que SantoniBot esta corriendo

Escribe:

```bash
docker compose ps
```

Presiona **Enter**. Deberias ver una tabla con 5 contenedores. Lo importante
es que todos digan **"Up"** o **"Running"** en la columna de estado:

| Contenedor | Puerto | Que hace | Estado correcto |
|---|---|---|---|
| santonibot-db-1 | 5433 | Base de datos interna | Up (healthy) |
| santonibot-chromadb-1 | 8001 | Base de datos vectorial | Up |
| santonibot-backend-1 | 8000 | API del bot (Python) | Up |
| santonibot-frontend-1 | 3000 | Interfaz web (lo que ves en el navegador) | Up |
| santonibot-nginx-1 | 80/443 | Proxy (redirige trafico) | Up |

**Si alguno dice "Exited" o no aparece**, ejecuta:

```bash
docker compose up -d
```

Eso levanta todos los contenedores. Espera unos 30 segundos y vuelve a ejecutar
`docker compose ps` para confirmar que ya estan todos en "Up".

**Si un contenedor sigue cayendo** (aparece y vuelve a decir Exited), hay un
error en el codigo o configuracion. Ve al Paso 8 para ver los logs del error.

---

## PASO 6: Abrir SantoniBot en el navegador

1. Abre tu navegador (Chrome, Firefox, Edge, etc.)
2. En la barra de direcciones escribe: `http://192.168.1.26`
3. Presiona **Enter**
4. Deberia cargarse la pagina de login de SantoniBot
5. Para el panel de administracion: `http://192.168.1.26/admin`

**Si no carga:**
- Verifica que la VPN este conectada (si estas fuera de Santoni)
- Verifica que los contenedores esten corriendo (Paso 5)
- Prueba limpiar cache: presiona **Ctrl + Shift + R** en el navegador

---

## PASO 7: Aplicar actualizaciones de codigo (deploy)

Cuando haya cambios nuevos en el repositorio de GitHub, necesitas bajarlos
al servidor y reconstruir los contenedores.

### 7.1 - Bajar los cambios de GitHub

```bash
cd /opt/santonibot
git pull origin main
```

Si te pide usuario y contrasena de GitHub, usa tus credenciales de GitHub
o el token de acceso personal configurado.

### 7.2 - Reconstruir y reiniciar

**Si los cambios son SOLO del backend (Python):**

```bash
docker compose build --no-cache backend && docker compose up -d backend
```

**Si los cambios son SOLO del frontend (la pagina web):**

```bash
docker compose build --no-cache frontend && docker compose up -d frontend
```

**Si hay cambios en ambos o no estas seguro:**

```bash
docker compose build --no-cache backend frontend && docker compose up -d
```

El proceso de build puede tardar entre 1 y 5 minutos. Cuando termine
veras algo como:

```
[+] Running 5/5
 ✔ Container santonibot-db-1        Running
 ✔ Container santonibot-chromadb-1   Running
 ✔ Container santonibot-backend-1    Started
 ✔ Container santonibot-frontend-1   Started
 ✔ Container santonibot-nginx-1      Running
```

### 7.3 - Verificar que funciona

1. Ejecuta `docker compose ps` y verifica que todos digan "Up"
2. Abre el navegador y entra a `http://192.168.1.26`
3. Presiona **Ctrl + Shift + R** para forzar recarga sin cache
4. Prueba enviar un mensaje al bot para confirmar que responde

---

## PASO 8: Ver logs cuando algo falla

Los logs son los mensajes que genera el sistema. Sirven para ver errores.

### Ver las ultimas 50 lineas de log del backend:

```bash
docker compose logs backend --tail 50
```

### Ver las ultimas 50 lineas de log del frontend:

```bash
docker compose logs frontend --tail 50
```

### Ver logs en tiempo real (se actualizan solos):

```bash
docker compose logs -f backend
```

Los mensajes van apareciendo en pantalla conforme llegan. Para dejar de ver
los logs, presiona **Ctrl + C** (mantener Ctrl y presionar la tecla C).

### Ver logs de TODOS los contenedores:

```bash
docker compose logs --tail 30
```

---

## PASO 9: Cambiar API keys o variables de entorno

Las configuraciones sensibles (claves de API, contrasenas de bases de datos,
etc.) estan en un archivo llamado `.env`.

### 9.1 - Abrir el archivo para editar

```bash
nano /opt/santonibot/.env
```

Se abre un editor de texto dentro de la terminal. Veras las variables asi:

```
GROQ_API_KEY=gsk_xxxxx...
OPENROUTER_API_KEY=sk-or-v1-xxxxx...
POSTGRES_PASSWORD=xxxxx...
```

### 9.2 - Editar

- Usa las flechas del teclado para moverte arriba/abajo/izquierda/derecha
- Escribe normalmente para agregar texto
- Usa la tecla **Backspace** o **Delete** para borrar

### 9.3 - Guardar y salir

1. Presiona **Ctrl + O** (la letra O, no el cero) para guardar
2. Te pregunta el nombre del archivo. Solo presiona **Enter** para confirmar
3. Presiona **Ctrl + X** para salir del editor

### 9.4 - Reiniciar el backend para que tome los cambios

```bash
docker compose restart backend
```

Espera 10 segundos y prueba el bot en el navegador.

---

## PASO 10: Reiniciar contenedores

### Reiniciar un solo contenedor (no pierde datos):

```bash
docker compose restart backend
```

o

```bash
docker compose restart frontend
```

### Reiniciar TODO (apagar y prender):

```bash
docker compose down && docker compose up -d
```

`down` apaga todos los contenedores. `up -d` los vuelve a encender.
Los datos de la base de datos NO se pierden.

---

## PASO 11: Hacer backup de la base de datos

Para crear una copia de seguridad de la base de datos:

```bash
docker compose run --rm backup
```

Veras un mensaje como:

```
[20260222_143000] Iniciando backup...
[20260222_143000] Backup completado: santonibot_20260222_143000.sql.gz (45K)
Backups disponibles: 5
```

Los backups se guardan automaticamente. Los de mas de 30 dias se eliminan solos.

---

## PASO 12: Desconectarse del servidor

Cuando termines de trabajar:

1. Escribe `exit` y presiona **Enter**. Eso cierra la conexion SSH.
2. Veras que el prompt regresa a `C:\Users\PCELL>` (tu PC local).
3. Si usaste VPN, puedes desconectarla desde FortiClient.
4. Cierra la ventana del CMD.

---

## Resumen rapido (para cuando ya sepas los pasos)

```bash
# Conectarse
ssh accinproa@192.168.1.26

# Ir al proyecto
cd /opt/santonibot

# Ver estado
docker compose ps

# Ver logs si algo falla
docker compose logs backend --tail 50

# Aplicar actualizaciones
git pull origin main
docker compose build --no-cache backend frontend && docker compose up -d

# Reiniciar todo
docker compose down && docker compose up -d

# Salir
exit
```

---

## Contactos

| Quien | Para que |
|---|---|
| OVA Agency | Errores en el codigo, nuevas funcionalidades |
| IT Santoni | Servidor apagado, red, VPN, iDempiere |
